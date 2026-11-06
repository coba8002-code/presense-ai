import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import 'app.dart';
import 'repository.dart';

Future<LocalRepository> createRepository() async {
  final support = await getApplicationSupportDirectory();
  final directory = Directory('${support.path}/PetSensePrivate');
  await directory.create(recursive: true);
  if (Platform.isIOS) {
    await const MethodChannel('com.petsense/privacy')
        .invokeMethod<void>('protectDirectory', directory.path);
  }
  final repository = LocalRepository(FileStateStorage(directory));
  await repository.load();
  return repository;
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    runApp(PetSenseApp(repository: await createRepository()));
  } catch (_) {
    runApp(const StartupErrorApp());
  }
}

class StartupErrorApp extends StatelessWidget {
  const StartupErrorApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    home: Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.lock_outline, size: 48),
                const SizedBox(height: 24),
                const Text(
                  '기록을 읽지 못했어요. 기존 파일은 보존했습니다.\nCould not read your journal. Existing files were preserved.',
                ),
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: main,
                  child: const Text('다시 읽기 · Try again'),
                ),
                TextButton(
                  onPressed: () async {
                    final confirmed = await showDialog<bool>(
                      context: context,
                      builder: (context) => AlertDialog(
                        title: const Text('모든 기록을 지울까요? · Erase all notes?'),
                        content: const Text(
                          '반려견과 모든 일지를 지웁니다. 되돌릴 수 없어요.\nRemove all dog profiles and notes. This cannot be undone.',
                        ),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(context, false),
                            child: const Text('취소 · Cancel'),
                          ),
                          FilledButton(
                            onPressed: () => Navigator.pop(context, true),
                            child: const Text('전체 삭제 · Erase all'),
                          ),
                        ],
                      ),
                    );
                    if (confirmed != true) return;
                    try {
                      final support = await getApplicationSupportDirectory();
                      await FileStateStorage(
                        Directory('${support.path}/PetSensePrivate'),
                      ).clear();
                      await main();
                    } catch (_) {
                      /* Keep the error screen and existing files if deletion fails. */
                    }
                  },
                  child: const Text('전체 초기화 · Reset all data'),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
