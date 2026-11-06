import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:petsense_mobile/audio_api.dart';
import 'package:petsense_mobile/audio_capture.dart';
import 'package:petsense_mobile/models.dart';

class FakeTransport implements SoundTransport {
  int calls = 0;
  bool cancelled = false;
  Map<String, String>? headers;
  TransportResponse response = TransportResponse(
    200,
    utf8.encode(
      jsonEncode({
        'decision': 'abstain',
        'production_ready': false,
        'dog_event_scores': [
          {'label': 'Bark', 'score': 0.2},
        ],
      }),
    ),
  );
  Completer<TransportResponse>? pending;
  @override
  Future<TransportResponse> post(
    Uri uri,
    Map<String, String> headers,
    Uint8List body,
  ) async {
    calls++;
    this.headers = headers;
    expect(uri.path, '/v1/audio/events');
    return pending?.future ?? Future.value(response);
  }

  @override
  void cancel() {
    cancelled = true;
  }
}

void main() {
  final wav = pcmToWav(Uint8List(3200));
  test(
    'no request without both confirmations, HTTPS origin and memory token',
    () async {
      final wire = FakeTransport();
      final client = SoundAnalyzer(() => wire);
      for (final input in [
        (false, true, 'https://example.com', 'test'),
        (true, false, 'https://example.com', 'test'),
        (true, true, 'http://example.com', 'test'),
        (true, true, 'https://a:b@example.com', 'test'),
        (true, true, 'https://example.com/path', 'test'),
        (true, true, 'https://example.com', ''),
      ]) {
        await expectLater(
          client.analyze(
            server: input.$3,
            token: input.$4,
            wav: wav,
            consent: input.$1,
            dogConfirmed: input.$2,
          ),
          throwsA(isA<AppFailure>()),
        );
      }
      expect(wire.calls, 0);
    },
  );
  test(
    'single request uses existing consent contract and keeps abstention',
    () async {
      final wire = FakeTransport();
      final result = await SoundAnalyzer(() => wire).analyze(
        server: 'https://example.com',
        token: 'test',
        wav: wav,
        consent: true,
        dogConfirmed: true,
      );
      expect(wire.calls, 1);
      expect(wire.headers!['X-Audio-Species'], 'dog');
      expect(wire.headers!['X-Audio-Consent'], 'true');
      expect(wire.headers!['Authorization'], 'Bearer test');
      expect(result.scores.single.label, 'Bark');
      expect(result.scores.single.score, 0.2);
    },
  );
  test(
    'disabled, redirects, large and unsafe responses are rejected',
    () async {
      for (final response in [
        TransportResponse(503, []),
        TransportResponse(302, []),
        TransportResponse(200, List.filled(65537, 32)),
        TransportResponse(
          200,
          utf8.encode('{"decision":"translate","production_ready":true}'),
        ),
      ]) {
        final wire = FakeTransport()..response = response;
        await expectLater(
          SoundAnalyzer(() => wire).analyze(
            server: 'https://example.com',
            token: 'test',
            wav: wav,
            consent: true,
            dogConfirmed: true,
          ),
          throwsA(isA<AppFailure>()),
        );
        expect(wire.calls, 1);
      }
    },
  );
  test(
    'late response after cancel is discarded and connection is closed',
    () async {
      final wire = FakeTransport()..pending = Completer<TransportResponse>();
      final client = SoundAnalyzer(() => wire);
      final request = client.analyze(
        server: 'https://example.com',
        token: 'test',
        wav: wav,
        consent: true,
        dogConfirmed: true,
      );
      final assertion = expectLater(request, throwsA(isA<AppFailure>()));
      client.cancel();
      wire.pending!.complete(wire.response);
      await assertion;
      expect(wire.cancelled, isTrue);
    },
  );
}
