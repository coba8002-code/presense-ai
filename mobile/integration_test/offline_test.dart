import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';
import 'package:petsense_mobile/app.dart';
import 'package:petsense_mobile/audio_capture.dart';
import 'package:petsense_mobile/repository.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'Android native storage: offline create, reload, delete and English',
    (tester) async {
      // A unique app-cache directory keeps real user notes separate from test fixtures.
      final temporary = await getTemporaryDirectory();
      final directory = await Directory(temporary.path)
          .createTemp('petsense-integration-');
      addTearDown(() => directory.delete(recursive: true));
      final storage = FileStateStorage(directory);
      final repo = LocalRepository(storage);
      await repo.load();
      await tester.pumpWidget(PetSenseApp(repository: repo));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('settingsTab')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('dogName')), 'Bori-test');
      await tester.ensureVisible(find.byKey(const Key('addPet')));
      await tester.tap(find.byKey(const Key('addPet')));
      await tester.pumpAndSettle();
      expect(repo.state.pets.single.name, 'Bori-test');
      await tester.tap(find.byKey(const Key('journalTab')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('observation')));
      await tester.enterText(
        find.byKey(const Key('observation')),
        'Synthetic test: looked at the door.',
      );
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('storeConsent')));
      await tester.tap(find.byKey(const Key('storeConsent')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('saveNote')));
      await tester.tap(find.byKey(const Key('saveNote')));
      await tester.pumpAndSettle();
      expect(repo.state.entries.length, 1);
      final reopened = LocalRepository(storage);
      await reopened.load();
      expect(
        reopened.state.entries.single.observation,
        'Synthetic test: looked at the door.',
      );
      await tester.pumpWidget(
        PetSenseApp(key: UniqueKey(), repository: reopened),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('settingsTab')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('English'));
      await tester.pumpAndSettle();
      expect(find.text('Your dogs'), findsOneWidget);
      await reopened.removePet(reopened.state.pets.single.id);
      final deleted = LocalRepository(storage);
      await deleted.load();
      expect(deleted.state.entries, isEmpty);
      expect(deleted.state.pets, isEmpty);
      expect(deleted.state.language, 'en');
    },
  );
  testWidgets('Android native microphone: bounded memory stream and discard', (
    tester,
  ) async {
    // Run on an emulator with host audio disabled and RECORD_AUDIO granted via adb.
    final capture = CaptureController(DeviceRecorder());
    addTearDown(capture.dispose);
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: Text('Native microphone check'))));
    await tester.pumpAndSettle();
    await tester.runAsync(() async {
      await capture.start().timeout(const Duration(seconds: 15));
      expect(capture.phase, CapturePhase.recording, reason: capture.error);
      await Future<void>.delayed(const Duration(seconds: 1));
      await capture.stop().timeout(const Duration(seconds: 15));
      expect(capture.phase, CapturePhase.ready, reason: capture.error);
      expect(capture.pcm!.length, inInclusiveRange(3200, CaptureController.maxBytes));
      expect(pcmToWav(capture.pcm!).length, capture.pcm!.length + 44);
      await capture.cancel();
      expect(capture.pcm, isNull);
    });
  });
}
