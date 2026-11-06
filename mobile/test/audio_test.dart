import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:petsense_mobile/audio_capture.dart';

class FakeRecorder implements RecorderPort {
  final stream = StreamController<Uint8List>();
  Future<bool> permission = Future.value(true);
  var starts = 0, cancels = 0;
  @override
  Future<bool> hasPermission() => permission;
  @override
  Future<Stream<Uint8List>> start() async {
    starts++;
    return stream.stream;
  }

  @override
  Future<void> stop() async {}
  @override
  Future<void> cancel() async {
    cancels++;
  }

  @override
  Future<void> dispose() async {
    await stream.close();
  }
}

void main() {
  test(
    'late permission after cancellation never starts the microphone',
    () async {
      final recorder = FakeRecorder();
      final permission = Completer<bool>();
      recorder.permission = permission.future;
      final capture = CaptureController(recorder);
      final starting = capture.start();
      await capture.cancel();
      permission.complete(true);
      await starting;
      expect(recorder.starts, 0);
      expect(capture.pcm, isNull);
      capture.dispose();
    },
  );
  test('bounds PCM at ten seconds and makes mono 16kHz PCM16 WAV', () async {
    final recorder = FakeRecorder();
    final capture = CaptureController(recorder);
    await capture.start();
    recorder.stream.add(Uint8List(400000));
    await Future<void>.delayed(Duration.zero);
    await capture.stop();
    expect(capture.pcm!.length, 320000);
    final wav = pcmToWav(capture.pcm!);
    expect(String.fromCharCodes(wav.sublist(0, 4)), 'RIFF');
    expect(ByteData.sublistView(wav).getUint32(24, Endian.little), 16000);
    expect(ByteData.sublistView(wav).getUint16(22, Endian.little), 1);
    expect(wav.length, 320044);
    await capture.cancel();
    expect(capture.pcm, isNull);
    capture.dispose();
  });
  test(
    'denied permission and tiny clips fail clearly without retaining audio',
    () async {
      final recorder = FakeRecorder()..permission = Future.value(false);
      final capture = CaptureController(recorder);
      await capture.start();
      expect(capture.error, 'permission');
      expect(recorder.starts, 0);
      expect(() => pcmToWav(Uint8List(100)), throwsA(anything));
      capture.dispose();
    },
  );
}
