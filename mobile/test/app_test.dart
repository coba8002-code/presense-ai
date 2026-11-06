import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:petsense_mobile/app.dart';
import 'package:petsense_mobile/l10n.dart';
import 'package:petsense_mobile/repository.dart';
import 'package:petsense_mobile/screens/sound_screen.dart';

import 'repository_test.dart' show MemoryStorage;
import 'audio_test.dart' show FakeRecorder;

void main() {
  Future<LocalRepository> repository() async {
    final repo = LocalRepository(MemoryStorage());
    await repo.load();
    return repo;
  }

  testWidgets(
    'offline add dog, explicit note consent, persisted note and language',
    (tester) async {
      tester.view.physicalSize = const Size(440, 950);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final repo = await repository();
      await tester.pumpWidget(PetSenseApp(repository: repo));
      await tester.tap(find.byKey(const Key('settingsTab')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('dogName')), '보리');
      await tester.tap(find.byKey(const Key('addPet')));
      await tester.pumpAndSettle();
      expect(repo.state.pets.single.name, '보리');
      await tester.tap(find.byKey(const Key('journalTab')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('observation')));
      await tester.enterText(
        find.byKey(const Key('observation')),
        '현관을 바라봤어요.',
      );
      await tester.ensureVisible(find.byKey(const Key('saveNote')));
      await tester.tap(find.byKey(const Key('saveNote')));
      await tester.pumpAndSettle();
      expect(repo.state.entries, isEmpty);
      await tester.ensureVisible(find.byKey(const Key('storeConsent')));
      await tester.tap(find.byKey(const Key('storeConsent')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('saveNote')));
      await tester.tap(find.byKey(const Key('saveNote')));
      await tester.pumpAndSettle();
      expect(repo.state.entries.single.observation, '현관을 바라봤어요.');
      await tester.tap(find.byKey(const Key('settingsTab')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('English'));
      await tester.pumpAndSettle();
      expect(find.text('Your dogs'), findsOneWidget);
      expect(repo.state.language, 'en');
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets('small screen and large text do not overflow', (tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.platformDispatcher.textScaleFactorTestValue = 1.4;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    final repo = await repository();
    await tester.pumpWidget(PetSenseApp(repository: repo));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settingsTab')));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
  testWidgets('backgrounding cancels a pending microphone permission', (
    tester,
  ) async {
    final repo = await repository();
    final recorder = FakeRecorder();
    final permission = Completer<bool>();
    recorder.permission = permission.future;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SoundScreen(
            repository: repo,
            copy: Copy('ko'),
            recorder: recorder,
          ),
        ),
      ),
    );
    await tester.tap(find.byKey(const Key('record')));
    await tester.pump();
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump();
    permission.complete(true);
    await tester.pumpAndSettle();
    expect(recorder.starts, 0);
    await tester.pumpWidget(const SizedBox.shrink());
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  });
  testWidgets('brief app switch clears a ready recording on inactive', (
    tester,
  ) async {
    final repo = await repository();
    final recorder = FakeRecorder();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SoundScreen(
            repository: repo,
            copy: Copy('ko'),
            recorder: recorder,
          ),
        ),
      ),
    );
    await tester.tap(find.byKey(const Key('record')));
    await tester.pumpAndSettle();
    recorder.stream.add(Uint8List(6400));
    await tester.pump();
    await tester.ensureVisible(find.text('녹음 마치기'));
    await tester.tap(find.text('녹음 마치기'));
    await tester.pumpAndSettle();
    expect(find.text('0.2 / 10.0 s'), findsOneWidget);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    addTearDown(
      () => tester.binding.handleAppLifecycleStateChanged(
        AppLifecycleState.resumed,
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('0.0 / 10.0 s'), findsOneWidget);
  });
}
