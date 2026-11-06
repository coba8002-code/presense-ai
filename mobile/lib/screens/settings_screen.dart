import 'package:flutter/material.dart';

import '../l10n.dart';
import '../repository.dart';
import '../ui.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({
    super.key,
    required this.repository,
    required this.copy,
  });
  final LocalRepository repository;
  final Copy copy;
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _name = TextEditingController();
  bool _busy = false;
  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _action(Future<void> Function() action) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
    } catch (error) {
      if (mounted) showFailure(context, widget.copy, error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.copy, state = widget.repository.state;
    return PageBody(
      children: [
        SectionCard(
          children: [
            Text(t('language'), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'ko', label: Text('한국어')),
                ButtonSegment(value: 'en', label: Text('English')),
              ],
              selected: {state.language},
              onSelectionChanged: _busy
                  ? null
                  : (values) => _action(
                      () => widget.repository.settings(language: values.single),
                    ),
            ),
          ],
        ),
        SectionCard(
          children: [
            Text(t('dogs'), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(t('countLimit')),
            const SizedBox(height: 16),
            TextField(
              key: const Key('dogName'),
              controller: _name,
              maxLength: 40,
              decoration: InputDecoration(labelText: t('name')),
              enabled: !_busy,
            ),
            FilledButton.icon(
              key: const Key('addPet'),
              onPressed: _busy
                  ? null
                  : () => _action(() async {
                      await widget.repository.addPet(_name.text);
                      _name.clear();
                    }),
              icon: const Icon(Icons.add),
              label: Text(t('addPet')),
            ),
            for (final pet in state.pets)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.pets_outlined),
                title: Text(pet.name),
                trailing: IconButton(
                  tooltip: t('delete'),
                  onPressed: _busy
                      ? null
                      : () async {
                          if (await confirmDelete(context, t, 'deletePet')) {
                            await _action(
                              () => widget.repository.removePet(pet.id),
                            );
                          }
                        },
                  icon: const Icon(Icons.delete_outline),
                ),
              ),
          ],
        ),
        SectionCard(
          children: [
            Text(t('privacy'), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            Text(t('privacyBody')),
            const SizedBox(height: 12),
            Text(t('notice')),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: _busy
                  ? null
                  : () async {
                      if (await confirmDelete(context, t, 'deleteAllBody')) {
                        await _action(widget.repository.clearAll);
                      }
                    },
              icon: const Icon(Icons.delete_forever_outlined),
              label: Text(t('deleteAll')),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Center(child: Text('PetSense 0.1.0 · ${t('beta')}')),
      ],
    );
  }
}
