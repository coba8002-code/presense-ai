import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:record/record.dart';

import 'models.dart';

abstract interface class RecorderPort {
  Future<bool> hasPermission();
  Future<Stream<Uint8List>> start();
  Future<void> stop();
  Future<void> cancel();
  Future<void> dispose();
}

class DeviceRecorder implements RecorderPort {
  AudioRecorder? _recorder;
  AudioRecorder get _device => _recorder ??= AudioRecorder();
  @override
  Future<bool> hasPermission() => _device.hasPermission();
  @override
  Future<Stream<Uint8List>> start() => _device.startStream(
    const RecordConfig(
      encoder: AudioEncoder.pcm16bits,
      sampleRate: 16000,
      numChannels: 1,
      audioInterruption: AudioInterruptionMode.pause,
    ),
  );
  @override
  Future<void> stop() async {
    await _recorder?.stop();
  }

  @override
  Future<void> cancel() async {
    await _recorder?.cancel();
  }

  @override
  Future<void> dispose() async {
    await _recorder?.dispose();
  }
}

enum CapturePhase { idle, requesting, recording, stopping, ready }

class CaptureController extends ChangeNotifier {
  CaptureController(this.recorder);
  final RecorderPort recorder;
  static const maxBytes = 320000;
  final BytesBuilder _buffer = BytesBuilder();
  StreamSubscription<Uint8List>? _subscription;
  Timer? _deadline;
  var _generation = 0;
  var _disposed = false;
  CapturePhase phase = CapturePhase.idle;
  String? error;
  Uint8List? _pcm;
  Uint8List? get pcm => _pcm == null ? null : Uint8List.fromList(_pcm!);
  double get seconds => (_pcm?.length ?? _buffer.length) / 32000;
  bool _current(int generation) => !_disposed && _generation == generation;
  void _changed() {
    if (!_disposed) notifyListeners();
  }

  Future<void> start() async {
    if (_disposed || ![CapturePhase.idle, CapturePhase.ready].contains(phase)) {
      return;
    }
    final generation = ++_generation;
    _pcm = null;
    _buffer.clear();
    error = null;
    phase = CapturePhase.requesting;
    _changed();
    try {
      final allowed = await recorder.hasPermission();
      if (!_current(generation)) return;
      if (!allowed) throw const AppFailure('permission');
      final stream = await recorder.start();
      if (!_current(generation)) {
        await recorder.cancel();
        return;
      }
      phase = CapturePhase.recording;
      _subscription = stream.listen(
        (data) {
          if (!_current(generation) ||
              ![
                CapturePhase.recording,
                CapturePhase.stopping,
              ].contains(phase)) {
            return;
          }
          final remaining = maxBytes - _buffer.length;
          if (remaining > 0) {
            _buffer.add(
              data.length <= remaining ? data : data.sublist(0, remaining),
            );
          }
          _changed();
          if (_buffer.length >= maxBytes) unawaited(stop());
        },
        onError: (Object _) {
          if (_current(generation)) unawaited(_fail('recordError'));
        },
        onDone: () {
          if (_current(generation) && phase == CapturePhase.recording) {
            unawaited(stop());
          }
        },
      );
      _deadline = Timer(const Duration(seconds: 10), () => unawaited(stop()));
      _changed();
    } catch (failure) {
      if (_current(generation)) {
        await _fail(failure is AppFailure ? failure.code : 'recordError');
      }
    }
  }

  Future<void> _fail(String code) async {
    await cancel();
    if (!_disposed) {
      error = code;
      _changed();
    }
  }

  Future<void> stop() async {
    if (_disposed || phase != CapturePhase.recording) return;
    final generation = _generation;
    phase = CapturePhase.stopping;
    _deadline?.cancel();
    _changed();
    try {
      await recorder.stop();
      if (!_current(generation)) return;
      await _subscription?.cancel();
      _subscription = null;
      if (!_current(generation)) return;
      final bytes = _buffer.takeBytes();
      final length = bytes.length - bytes.length % 2;
      if (length < 3200) throw const AppFailure('tooShort');
      _pcm = Uint8List.fromList(bytes.sublist(0, length));
      phase = CapturePhase.ready;
      _changed();
    } catch (failure) {
      if (_current(generation)) {
        await _fail(failure is AppFailure ? failure.code : 'recordError');
      }
    }
  }

  Future<void> cancel() async {
    if (_disposed) return;
    final generation = ++_generation;
    _deadline?.cancel();
    _pcm = null;
    _buffer.clear();
    error = null;
    phase = CapturePhase.stopping;
    _changed();
    await _subscription?.cancel();
    _subscription = null;
    try {
      await recorder.cancel();
    } catch (_) {
      /* Nothing is retained on failure. */
    }
    if (_current(generation)) {
      phase = CapturePhase.idle;
      _changed();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    _deadline?.cancel();
    _buffer.clear();
    _pcm = null;
    unawaited(_subscription?.cancel());
    unawaited(recorder.dispose().catchError((Object _) {}));
    super.dispose();
  }
}

Uint8List pcmToWav(Uint8List pcm) {
  if (pcm.length < 3200 ||
      pcm.length > CaptureController.maxBytes ||
      pcm.length.isOdd) {
    throw const AppFailure('tooShort');
  }
  final wav = Uint8List(44 + pcm.length);
  final header = ByteData.sublistView(wav);
  void word(int offset, String value) =>
      wav.setRange(offset, offset + value.length, value.codeUnits);
  word(0, 'RIFF');
  header.setUint32(4, 36 + pcm.length, Endian.little);
  word(8, 'WAVE');
  word(12, 'fmt ');
  header.setUint32(16, 16, Endian.little);
  header.setUint16(20, 1, Endian.little);
  header.setUint16(22, 1, Endian.little);
  header.setUint32(24, 16000, Endian.little);
  header.setUint32(28, 32000, Endian.little);
  header.setUint16(32, 2, Endian.little);
  header.setUint16(34, 16, Endian.little);
  word(36, 'data');
  header.setUint32(40, pcm.length, Endian.little);
  wav.setRange(44, wav.length, pcm);
  return wav;
}
