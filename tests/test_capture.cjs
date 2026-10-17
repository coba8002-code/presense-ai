const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function processor() {
  let Processor;
  const messages = [];
  class AudioWorkletProcessor { constructor() { this.port = {postMessage: x => messages.push(x)}; } }
  vm.runInNewContext(fs.readFileSync('backend/static/capture.js', 'utf8'), {
    AudioWorkletProcessor, registerProcessor: (name, type) => { Processor = type; }
  });
  return {node: new Processor(), messages};
}

test('captures exactly one second, signed little-endian PCM16, and resets', () => {
  const {node, messages} = processor();
  for (let i = 0; i < 124; i++) node.process([[new Float32Array(128).fill(-1)]], []);
  assert.equal(messages.length, 0);
  node.process([[new Float32Array(128).fill(-1)]], []);
  assert.equal(messages.length, 1);
  assert.equal(messages[0].pcm.byteLength, 32000);
  assert.equal(new DataView(messages[0].pcm).getInt16(0, true), -32768);
  assert.equal(messages[0].rms, 1);
  assert.equal(messages[0].sequence, 0);
  for (let i = 0; i < 125; i++) node.process([[new Float32Array(128).fill(1)]], []);
  assert.equal(messages.length, 2);
  assert.equal(messages[1].sequence, 1);
  assert.equal(new DataView(messages[1].pcm).getInt16(0, true), 32767);
});

test('silences output to avoid microphone feedback and ignores absent input', () => {
  const {node, messages} = processor();
  const output = new Float32Array(128).fill(1);
  node.process([], [[output]]);
  assert.ok(output.every(x => x === 0));
  assert.equal(messages.length, 0);
});
