// AudioWorklet: fixed 1-second mono PCM16 chunks, no recording retained.
class PCMChunker extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = new Float32Array(16000);
    this.offset = 0;
    this.sequence = 0;
  }
  process(inputs, outputs) {
    // Silent sink keeps the graph alive without microphone feedback.
    for (const output of outputs) for (const channel of output) channel.fill(0);
    const channel = inputs[0]?.[0];
    if (!channel) return true;
    for (const sample of channel) {
      this.samples[this.offset++] = sample;
      if (this.offset === 16000) {
        const pcm = new ArrayBuffer(32000);
        const view = new DataView(pcm);
        let energy = 0;
        for (let i = 0; i < this.samples.length; i++) {
          const clipped = Math.max(-1, Math.min(1, this.samples[i]));
          const quantized = Math.round(clipped * (clipped < 0 ? 32768 : 32767));
          view.setInt16(i * 2, quantized, true);
          energy += (quantized / 32768) ** 2;
        }
        this.port.postMessage({pcm, rms: Math.sqrt(energy / 16000), sequence: this.sequence++}, [pcm]);
        this.offset = 0;
      }
    }
    return true;
  }
}
registerProcessor('pcm-chunker', PCMChunker);
