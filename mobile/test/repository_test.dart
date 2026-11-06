import 'dart:io';
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:petsense_mobile/models.dart';
import 'package:petsense_mobile/repository.dart';

class MemoryStorage implements StateStorage {
  String? value;
  bool fail = false;
  @override
  Future<String?> read() async => value;
  @override
  Future<void> write(String data) async {
    if (fail) throw const FileSystemException('test');
    value = data;
  }

  @override
  Future<void> clear() async => value = null;
}

class BlockingStorage extends MemoryStorage {
  Completer<void>? gate;
  @override
  Future<void> write(String data) async {
    await gate?.future;
    await super.write(data);
  }
}

void main() {
  late MemoryStorage storage;
  late LocalRepository repo;
  var now = DateTime.utc(2026, 11, 6);
  setUp(() async {
    storage = MemoryStorage();
    now = DateTime.utc(2026, 11, 6);
    repo = LocalRepository(storage, now: () => now);
    await repo.load();
  });
  test('save needs consent and separates guardian observation, hypothesis, follow-up', () async {
    final pet = await repo.addPet(' 보리 ');
    await expectLater(
      repo.addEntry(petId: pet.id, observation: '현관을 봄', consent: false),
      throwsA(isA<AppFailure>()),
    );
    expect(repo.state.entries, isEmpty);
    await repo.addEntry(
      petId: pet.id,
      observation: '현관을 봄',
      hypothesis: '산책을 기다릴 수 있음',
      followUp: '이후 누웠음',
      consent: true,
    );
    final reopened = LocalRepository(storage, now: () => now);
    await reopened.load();
    expect(reopened.state.pets.single.name, '보리');
    final entry = reopened.state.entries.single;
    expect(entry.observation, '현관을 봄');
    expect(entry.hypothesis, '산책을 기다릴 수 있음');
    expect(entry.followUp, '이후 누웠음');
    expect(entry.source, 'guardian_report');
  });
  test(
    'profile deletion cascades and expired records are removed on reopening',
    () async {
      final first = await repo.addPet('보리');
      final second = await repo.addPet('콩이');
      await repo.addEntry(petId: first.id, observation: '누웠음', consent: true);
      await repo.addEntry(petId: second.id, observation: '걸었음', consent: true);
      await repo.removePet(first.id);
      expect(repo.state.entries.single.petId, second.id);
      now = now.add(const Duration(days: 30));
      final reopened = LocalRepository(storage, now: () => now);
      await reopened.load();
      expect(reopened.state.entries, isEmpty);
      expect(storage.value, isNot(contains('걸었음')));
    },
  );
  test(
    'write failure preserves previous state and damaged file is not replaced',
    () async {
      await repo.addPet('보리');
      final before = storage.value;
      storage.fail = true;
      await expectLater(repo.addPet('콩이'), throwsA(isA<AppFailure>()));
      expect(repo.state.pets.length, 1);
      expect(storage.value, before);
      storage.fail = false;
      storage.value = '{broken';
      await expectLater(
        LocalRepository(storage).load(),
        throwsA(isA<AppFailure>()),
      );
      expect(storage.value, '{broken');
    },
  );
  test('enforces input and profile limits; individual and complete removal persist', () async {
    await expectLater(repo.addPet('  '), throwsA(isA<AppFailure>()));
    for (var i = 0; i < 20; i++) {
      await repo.addPet('dog $i');
    }
    await expectLater(repo.addPet('extra'), throwsA(isA<AppFailure>()));
    await expectLater(
      repo.addEntry(petId: 'missing', observation: 'x', consent: true),
      throwsA(isA<AppFailure>()),
    );
    await repo.addEntry(
      petId: repo.state.pets.first.id,
      observation: 'x',
      consent: true,
    );
    await repo.removeEntry(repo.state.entries.single.id);
    expect(repo.state.entries, isEmpty);
    await repo.clearAll();
    final reopened = LocalRepository(storage);
    await reopened.load();
    expect(reopened.state.pets, isEmpty);
  });
  test(
    'file storage atomically replaces state without leftover copies',
    () async {
      final directory = await Directory.systemTemp.createTemp('petsense-unit-');
      addTearDown(() => directory.delete(recursive: true));
      final file = FileStateStorage(directory);
      await file.write('first');
      await file.write('second');
      expect(await file.read(), 'second');
      expect(await directory.list().length, 1);
      await file.clear();
      expect(await file.read(), isNull);
    },
  );
  test('pending write blocks other writes and reset without losing the first update', () async {
    final blocked = BlockingStorage();
    final store = LocalRepository(blocked);
    await store.load();
    blocked.gate = Completer<void>();
    final first = store.addPet('first');
    await expectLater(store.addPet('second'), throwsA(isA<AppFailure>()));
    await expectLater(store.clearAll(), throwsA(isA<AppFailure>()));
    await store.load();
    blocked.gate!.complete();
    await first;
    expect(store.state.pets.single.name, 'first');
  });
  test('100 note limit and future time are checked; failed load cannot overwrite damaged data', () async {
    final pet = await repo.addPet('보리');
    await expectLater(
      repo.addEntry(
        petId: pet.id,
        observation: 'future',
        consent: true,
        observedAt: now.add(const Duration(hours: 1)),
      ),
      throwsA(isA<AppFailure>()),
    );
    for (var i = 0; i < 100; i++) {
      await repo.addEntry(petId: pet.id, observation: 'note $i', consent: true);
    }
    await expectLater(
      repo.addEntry(petId: pet.id, observation: 'extra', consent: true),
      throwsA(isA<AppFailure>()),
    );
    storage.value = '{broken';
    final damaged = LocalRepository(storage);
    await expectLater(damaged.load(), throwsA(isA<AppFailure>()));
    await expectLater(
      damaged.addPet('must not overwrite'),
      throwsA(isA<AppFailure>()),
    );
    expect(storage.value, '{broken');
  });
}
