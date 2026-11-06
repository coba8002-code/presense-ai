import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'models.dart';

class TransportResponse {
  TransportResponse(this.status, List<int> data)
    : data = Uint8List.fromList(data);
  final int status;
  final Uint8List data;
}

abstract interface class SoundTransport {
  Future<TransportResponse> post(
    Uri uri,
    Map<String, String> headers,
    Uint8List body,
  );
  void cancel();
}

class HttpsSoundTransport implements SoundTransport {
  final HttpClient _client = HttpClient()
    ..connectionTimeout = const Duration(seconds: 10);
  @override
  Future<TransportResponse> post(
    Uri uri,
    Map<String, String> headers,
    Uint8List body,
  ) async {
    try {
      final request = await _client.postUrl(uri);
      request.followRedirects = false;
      headers.forEach(request.headers.set);
      request.contentLength = body.length;
      request.add(body);
      final response = await request.close();
      final bytes = BytesBuilder();
      await for (final chunk in response) {
        if (bytes.length + chunk.length > 65536) {
          throw const AppFailure('badResponse');
        }
        bytes.add(chunk);
      }
      return TransportResponse(response.statusCode, bytes.takeBytes());
    } finally {
      _client.close(force: true);
    }
  }

  @override
  void cancel() => _client.close(force: true);
}

const dogLabels = {
  'Dog',
  'Bark',
  'Yip',
  'Howl',
  'Bow-wow',
  'Growling',
  'Whimper (dog)',
};

class EventScore {
  EventScore(this.label, this.score);
  final String label;
  final double score;
}

class SoundResult {
  SoundResult(this.scores);
  final List<EventScore> scores;
  factory SoundResult.parse(Uint8List bytes) {
    try {
      if (bytes.length > 65536) throw const FormatException();
      final json = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
      if (json['decision'] != 'abstain' ||
          json['production_ready'] != false ||
          json['dog_event_scores'] is! List) {
        throw const FormatException();
      }
      final values = json['dog_event_scores'] as List;
      if (values.isEmpty || values.length > dogLabels.length) {
        throw const FormatException();
      }
      final seen = <String>{};
      final scores = values.map((value) {
        final row = value as Map<String, dynamic>;
        final label = row['label'];
        final score = row['score'];
        if (label is! String ||
            !dogLabels.contains(label) ||
            !seen.add(label) ||
            score is! num ||
            !score.isFinite ||
            score < 0 ||
            score > 1) {
          throw const FormatException();
        }
        return EventScore(label, score.toDouble());
      }).toList();
      return SoundResult(List.unmodifiable(scores));
    } catch (_) {
      throw const AppFailure('badResponse');
    }
  }
}

class SoundAnalyzer {
  SoundAnalyzer([SoundTransport Function()? create])
    : _create = create ?? HttpsSoundTransport.new;
  final SoundTransport Function() _create;
  SoundTransport? _active;
  var _generation = 0;
  void cancel() {
    _generation++;
    _active?.cancel();
    _active = null;
  }

  Future<SoundResult> analyze({
    required String server,
    required String token,
    required Uint8List wav,
    required bool consent,
    required bool dogConfirmed,
  }) async {
    if (!consent || !dogConfirmed) throw const AppFailure('consent');
    final origin = serverOrigin(server);
    if (origin == null) throw const AppFailure('serverInvalid');
    if (!RegExp(r'^[\x21-\x7e]{1,4096}$').hasMatch(token)) {
      throw const AppFailure('auth');
    }
    if (wav.length < 3244 ||
        wav.length > 320044 ||
        String.fromCharCodes(wav.sublist(0, 4)) != 'RIFF') {
      throw const AppFailure('tooShort');
    }
    if (_active != null) throw const AppFailure('busy');
    final generation = ++_generation;
    final wire = _create();
    _active = wire;
    try {
      final response = await wire
          .post(origin.replace(path: '/v1/audio/events'), {
            'Authorization': 'Bearer $token',
            'Content-Type': 'audio/wav',
            'X-Audio-Consent': 'true',
            'X-Audio-Species': 'dog',
          }, wav)
          .timeout(
            const Duration(seconds: 70),
            onTimeout: () {
              wire.cancel();
              throw const AppFailure('timeout');
            },
          );
      if (generation != _generation) throw const AppFailure('cancelled');
      if ([401, 403].contains(response.status)) throw const AppFailure('auth');
      if (response.status == 429) throw const AppFailure('busy');
      if (response.status == 503) throw const AppFailure('unavailable');
      if (response.status != 200) throw const AppFailure('connection');
      return SoundResult.parse(response.data);
    } on AppFailure {
      rethrow;
    } catch (_) {
      throw AppFailure(generation != _generation ? 'cancelled' : 'connection');
    } finally {
      wire.cancel();
      if (generation == _generation) _active = null;
    }
  }
}
