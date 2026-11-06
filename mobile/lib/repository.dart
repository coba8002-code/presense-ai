import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import 'models.dart';

abstract interface class StateStorage {
  Future<String?> read();
  Future<void> write(String data);
  Future<void> clear();
}

class FileStateStorage implements StateStorage {
  FileStateStorage(this.directory);
  final Directory directory;
  File get _file => File('${directory.path}/state.json');
  File get _temporary => File('${directory.path}/state.tmp');
  @override
  Future<String?> read() async {
    if (await _temporary.exists()) await _temporary.delete();
    if (!await _file.exists()) return null;
    if (await _file.length() > 1000000) throw const AppFailure('corrupt');
    return _file.readAsString();
  }

  @override
  Future<void> write(String data) async {
    await directory.create(recursive: true);
    await _temporary.writeAsString(data, flush: true);
    // Keep the old state intact until the complete new file has been flushed.
    await _temporary.rename(_file.path);
  }

  @override
  Future<void> clear() async {
    for (final file in [_file, _temporary]) {
      if (await file.exists()) await file.delete();
    }
  }
}

class LocalRepository extends ChangeNotifier {
  LocalRepository(this.storage, {DateTime Function()? now})
    : _now = now ?? DateTime.now;
  final StateStorage storage;
  final DateTime Function() _now;
  LocalState _state = LocalState();
  LocalState get state => _state;
  bool _writing = false;
  bool _loaded = false;
  LocalState _prune(LocalState state) => state.copyWith(
    entries: state.entries
        .where((entry) => entry.expiresAt.isAfter(_now().toUtc()))
        .toList(),
  );

  Future<void> load() async {
    if (_writing) return;
    _writing = true;
    try {
      final raw = await storage.read();
      final parsed = raw == null
          ? LocalState()
          : LocalState.fromJson(jsonDecode(raw) as Map<String, dynamic>);
      final cleaned = _prune(parsed);
      if (cleaned.entries.length != parsed.entries.length) {
        await storage.write(jsonEncode(cleaned.toJson()));
      }
      _state = cleaned;
      _loaded = true;
      notifyListeners();
    } catch (_) {
      _loaded = false;
      throw const AppFailure('corrupt');
    } finally {
      _writing = false;
    }
  }

  Future<void> _commit(LocalState next) async {
    if (!_loaded) throw const AppFailure('corrupt');
    if (_writing) throw const AppFailure('busy');
    _writing = true;
    try {
      final cleaned = _prune(next);
      await storage.write(jsonEncode(cleaned.toJson()));
      _state = cleaned;
      notifyListeners();
    } catch (_) {
      throw const AppFailure('storage');
    } finally {
      _writing = false;
    }
  }

  Future<DogProfile> addPet(String name) async {
    final valid = checkedText(name, 40, required: true);
    if (state.pets.length >= 20) throw const AppFailure('limit');
    final pet = DogProfile(id: newId(), name: valid, createdAt: _now().toUtc());
    await _commit(state.copyWith(pets: [...state.pets, pet]));
    return pet;
  }

  Future<void> addEntry({
    required String petId,
    required String observation,
    String hypothesis = '',
    String followUp = '',
    required bool consent,
    DateTime? observedAt,
  }) async {
    if (!consent) throw const AppFailure('consent');
    final clean = _prune(state);
    if (!clean.pets.any((pet) => pet.id == petId)) {
      throw const AppFailure('needPet');
    }
    if (clean.entries.length >= 100) throw const AppFailure('limit');
    final time = (observedAt ?? _now()).toUtc();
    if (time.isAfter(_now().toUtc().add(const Duration(minutes: 5)))) {
      throw const AppFailure('invalid');
    }
    final entry = GuardianEntry(
      id: newId(),
      petId: petId,
      observation: checkedText(observation, 500, required: true),
      hypothesis: checkedText(hypothesis, 500),
      followUp: checkedText(followUp, 500),
      observedAt: time,
      savedAt: _now().toUtc(),
    );
    await _commit(clean.copyWith(entries: [entry, ...clean.entries]));
  }

  Future<void> removePet(String id) => _commit(
    state.copyWith(
      pets: state.pets.where((p) => p.id != id).toList(),
      entries: state.entries.where((e) => e.petId != id).toList(),
    ),
  );
  Future<void> removeEntry(String id) => _commit(
    state.copyWith(entries: state.entries.where((e) => e.id != id).toList()),
  );
  Future<void> settings({String? language, String? server}) async {
    if (language != null && !['ko', 'en'].contains(language)) {
      throw const AppFailure('invalid');
    }
    await _commit(
      state.copyWith(
        language: language,
        server: server == null ? null : serverOrigin(server)?.toString() ?? '',
      ),
    );
  }

  Future<void> clearAll() async {
    if (_writing) throw const AppFailure('busy');
    _writing = true;
    try {
      await storage.clear();
      _state = LocalState();
      _loaded = true;
      notifyListeners();
    } catch (_) {
      throw const AppFailure('storage');
    } finally {
      _writing = false;
    }
  }
}
