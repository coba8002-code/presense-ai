import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'l10n.dart';
import 'repository.dart';
import 'screens/journal_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/sound_screen.dart';

class PetSenseApp extends StatefulWidget {
  const PetSenseApp({super.key, required this.repository});
  final LocalRepository repository;
  @override
  State<PetSenseApp> createState() => _PetSenseAppState();
}

class _PetSenseAppState extends State<PetSenseApp> with WidgetsBindingObserver {
  int _index = 0;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      // Expiration is enforced again when returning from the background.
      widget.repository.load().catchError((Object _) {});
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.repository,
    builder: (context, _) {
      final t = Copy(widget.repository.state.language);
      return MaterialApp(
        title: 'PetSense',
        debugShowCheckedModeBanner: false,
        locale: Locale(widget.repository.state.language),
        supportedLocales: const [Locale('ko'), Locale('en')],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff386957)),
          scaffoldBackgroundColor: const Color(0xfff6f5ef),
          cardTheme: CardThemeData(
            color: Colors.white,
            elevation: 0,
            margin: const EdgeInsets.symmetric(vertical: 6),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(24),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: const Color(0xfff5f7f3),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide.none,
            ),
          ),
          filledButtonTheme: FilledButtonThemeData(
            style: FilledButton.styleFrom(padding: const EdgeInsets.all(16)),
          ),
        ),
        home: Scaffold(
          appBar: AppBar(
            backgroundColor: const Color(0xfff6f5ef),
            surfaceTintColor: Colors.transparent,
            title: const Row(
              children: [
                Icon(Icons.pets_rounded, color: Color(0xff386957)),
                SizedBox(width: 10),
                Text(
                  'PetSense',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.5,
                  ),
                ),
              ],
            ),
            bottom: PreferredSize(
              preferredSize: const Size.fromHeight(30),
              child: Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(t('tagline')),
              ),
            ),
          ),
          body: switch (_index) {
            0 => JournalScreen(repository: widget.repository, copy: t),
            1 => SoundScreen(repository: widget.repository, copy: t),
            _ => SettingsScreen(repository: widget.repository, copy: t),
          },
          bottomNavigationBar: NavigationBar(
            selectedIndex: _index,
            onDestinationSelected: (index) {
              FocusManager.instance.primaryFocus?.unfocus();
              setState(() => _index = index);
            },
            destinations: [
              NavigationDestination(
                key: const Key('journalTab'),
                icon: const Icon(Icons.auto_stories_outlined),
                selectedIcon: const Icon(Icons.auto_stories),
                label: t('journal'),
              ),
              NavigationDestination(
                key: const Key('soundTab'),
                icon: const Icon(Icons.graphic_eq_outlined),
                label: t('sound'),
              ),
              NavigationDestination(
                key: const Key('settingsTab'),
                icon: const Icon(Icons.tune_rounded),
                label: t('settings'),
              ),
            ],
          ),
        ),
      );
    },
  );
}
