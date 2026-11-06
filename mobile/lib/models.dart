import 'dart:math';

class AppFailure implements Exception {
  const AppFailure(this.code);
  final String code;
}

String newId() {
  final random = Random.secure();
  return List.generate(
    16,
    (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
  ).join();
}

String checkedText(String value, int limit, {bool required = false}) {
  final trimmed = value.trim();
  if (trimmed.length > limit || (required && trimmed.isEmpty)) {
    throw const AppFailure('invalid');
  }
  return trimmed;
}

Uri? serverOrigin(String value) {
  if (value.trim().isEmpty) return null;
  final uri = Uri.tryParse(value.trim());
  if (uri == null ||
      uri.scheme != 'https' ||
      uri.host.isEmpty ||
      uri.userInfo.isNotEmpty ||
      uri.hasQuery ||
      uri.hasFragment ||
      (uri.path.isNotEmpty && uri.path != '/') ||
      value.length > 300) {
    throw const AppFailure('serverInvalid');
  }
  return uri.replace(path: '');
}

String _id(dynamic value) {
  if (value is! String || !RegExp(r'^[a-f0-9]{32}$').hasMatch(value)) {
    throw const FormatException('Invalid id');
  }
  return value;
}

String _text(dynamic value, int max, {bool required = false}) {
  if (value is! String) throw const FormatException('Invalid text');
  return checkedText(value, max, required: required);
}

DateTime _date(dynamic value) {
  if (value is! String || !value.endsWith('Z')) {
    throw const FormatException('Invalid date');
  }
  return DateTime.parse(value).toUtc();
}

class DogProfile {
  DogProfile({required this.id, required this.name, required this.createdAt});
  final String id;
  final String name;
  final DateTime createdAt;
  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'created_at': createdAt.toUtc().toIso8601String(),
    'species': 'dog',
  };
  factory DogProfile.fromJson(Map<String, dynamic> json) {
    if (json['species'] != 'dog') throw const FormatException('Dog only');
    return DogProfile(
      id: _id(json['id']),
      name: _text(json['name'], 40, required: true),
      createdAt: _date(json['created_at']),
    );
  }
}

class GuardianEntry {
  GuardianEntry({
    required this.id,
    required this.petId,
    required this.observation,
    required this.hypothesis,
    required this.followUp,
    required this.observedAt,
    required this.savedAt,
  });
  final String id, petId, observation, hypothesis, followUp;
  final DateTime observedAt, savedAt;
  String get source => 'guardian_report';
  DateTime get expiresAt => savedAt.add(const Duration(days: 30));
  Map<String, dynamic> toJson() => {
    'id': id,
    'pet_id': petId,
    'observation': observation,
    'hypothesis': hypothesis,
    'follow_up': followUp,
    'source': source,
    'observed_at': observedAt.toUtc().toIso8601String(),
    'saved_at': savedAt.toUtc().toIso8601String(),
  };
  factory GuardianEntry.fromJson(Map<String, dynamic> json) {
    if (json['source'] != 'guardian_report') {
      throw const FormatException('Unknown source');
    }
    return GuardianEntry(
      id: _id(json['id']),
      petId: _id(json['pet_id']),
      observation: _text(json['observation'], 500, required: true),
      hypothesis: _text(json['hypothesis'], 500),
      followUp: _text(json['follow_up'], 500),
      observedAt: _date(json['observed_at']),
      savedAt: _date(json['saved_at']),
    );
  }
}

class LocalState {
  LocalState({
    this.language = 'ko',
    this.server = '',
    List<DogProfile> pets = const [],
    List<GuardianEntry> entries = const [],
  }) : pets = List.unmodifiable(pets),
       entries = List.unmodifiable(entries);
  final String language, server;
  final List<DogProfile> pets;
  final List<GuardianEntry> entries;
  LocalState copyWith({
    String? language,
    String? server,
    List<DogProfile>? pets,
    List<GuardianEntry>? entries,
  }) => LocalState(
    language: language ?? this.language,
    server: server ?? this.server,
    pets: pets ?? this.pets,
    entries: entries ?? this.entries,
  );
  Map<String, dynamic> toJson() => {
    'schema_version': 1,
    'language': language,
    'server_url': server,
    'pets': pets.map((p) => p.toJson()).toList(),
    'entries': entries.map((e) => e.toJson()).toList(),
  };
  factory LocalState.fromJson(Map<String, dynamic> json) {
    if (json['schema_version'] != 1 ||
        !['ko', 'en'].contains(json['language']) ||
        json['pets'] is! List ||
        json['entries'] is! List ||
        json['server_url'] is! String) {
      throw const FormatException('Unsupported state');
    }
    final pets = (json['pets'] as List)
        .map((p) => DogProfile.fromJson(Map<String, dynamic>.from(p as Map)))
        .toList();
    final entries = (json['entries'] as List)
        .map((e) => GuardianEntry.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
    final ids = pets.map((p) => p.id).toSet();
    if (pets.length > 20 ||
        entries.length > 100 ||
        ids.length != pets.length ||
        entries.map((e) => e.id).toSet().length != entries.length ||
        entries.any((e) => !ids.contains(e.petId))) {
      throw const FormatException('Invalid collection');
    }
    final server = serverOrigin(json['server_url'] as String)?.toString() ?? '';
    return LocalState(
      language: json['language'] as String,
      server: server,
      pets: pets,
      entries: entries,
    );
  }
}
