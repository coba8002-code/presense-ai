import 'package:flutter/material.dart';

import '../l10n.dart';
import '../repository.dart';
import '../ui.dart';

class JournalScreen extends StatefulWidget {
  const JournalScreen({
    super.key,
    required this.repository,
    required this.copy,
  });
  final LocalRepository repository;
  final Copy copy;
  @override
  State<JournalScreen> createState() => _JournalScreenState();
}

class _JournalScreenState extends State<JournalScreen> {
  final _observation = TextEditingController(),
      _hypothesis = TextEditingController(),
      _followUp = TextEditingController();
  String? _petId;
  var _consent = false, _saving = false;
  DateTime _observedAt = DateTime.now();
  @override
  void dispose() {
    _observation.dispose();
    _hypothesis.dispose();
    _followUp.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      await widget.repository.addEntry(
        petId: _petId ?? '',
        observation: _observation.text,
        hypothesis: _hypothesis.text,
        followUp: _followUp.text,
        consent: _consent,
        observedAt: _observedAt,
      );
      _observation.clear();
      _hypothesis.clear();
      _followUp.clear();
      if (!mounted) return;
      setState(() {
        _consent = false;
        _observedAt = DateTime.now();
      });
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(widget.copy('saved'))));
    } catch (error) {
      if (mounted) showFailure(context, widget.copy, error);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _time() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _observedAt,
      firstDate: DateTime(2000),
      lastDate: DateTime.now(),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_observedAt),
    );
    if (time != null && mounted) {
      setState(
        () => _observedAt = DateTime(
          date.year,
          date.month,
          date.day,
          time.hour,
          time.minute,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.copy, state = widget.repository.state;
    if (!state.pets.any((pet) => pet.id == _petId)) {
      _petId = state.pets.firstOrNull?.id;
    }
    final pets = {for (final pet in state.pets) pet.id: pet.name};
    return PageBody(
      children: [
        Container(
          padding: const EdgeInsets.all(24),
          margin: const EdgeInsets.only(bottom: 12),
          decoration: BoxDecoration(
            color: const Color(0xff244c41),
            borderRadius: BorderRadius.circular(28),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.pets_rounded,
                color: Color(0xffd4e8b8),
                size: 34,
              ),
              const SizedBox(height: 18),
              Text(
                t('hero'),
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                t('heroBody'),
                style: const TextStyle(color: Color(0xffe0ece5), height: 1.6),
              ),
              const SizedBox(height: 18),
              Text(
                '● ${t('local')}',
                style: const TextStyle(color: Color(0xffd4e8b8)),
              ),
            ],
          ),
        ),
        SectionCard(
          children: [
            Text(t('newNote'), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            if (state.pets.isEmpty)
              Text(t('noPet'))
            else
              DropdownButtonFormField<String>(
                key: ValueKey('pet-${_petId ?? ''}'),
                initialValue: _petId,
                isExpanded: true,
                decoration: InputDecoration(labelText: t('pet')),
                items: state.pets
                    .map(
                      (pet) => DropdownMenuItem(
                        value: pet.id,
                        child: Text(pet.name),
                      ),
                    )
                    .toList(),
                onChanged: _saving
                    ? null
                    : (id) => setState(() {
                        _petId = id;
                        _consent = false;
                      }),
              ),
            const SizedBox(height: 16),
            TextField(
              key: const Key('observation'),
              controller: _observation,
              minLines: 2,
              maxLines: 5,
              maxLength: 500,
              enabled: !_saving,
              decoration: InputDecoration(
                labelText: t('observation'),
                hintText: t('observationHint'),
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('hypothesis'),
              controller: _hypothesis,
              minLines: 1,
              maxLines: 4,
              maxLength: 500,
              enabled: !_saving,
              decoration: InputDecoration(
                labelText: t('hypothesis'),
                hintText: t('hypothesisHint'),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('followUp'),
              controller: _followUp,
              minLines: 1,
              maxLines: 4,
              maxLength: 500,
              enabled: !_saving,
              decoration: InputDecoration(
                labelText: t('followUp'),
                hintText: t('followUpHint'),
              ),
            ),
            Text('${t('observedAt')}  ${localTime(_observedAt)}'),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: _saving ? null : _time,
                child: Text(t('changeTime')),
              ),
            ),
            CheckboxListTile(
              key: const Key('storeConsent'),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _consent,
              onChanged: _saving
                  ? null
                  : (value) => setState(() => _consent = value ?? false),
              title: Text(t('storeConsent')),
            ),
            Text(t('retention'), style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 16),
            FilledButton.icon(
              key: const Key('saveNote'),
              onPressed: _saving || state.pets.isEmpty ? null : _save,
              icon: const Icon(Icons.check_rounded),
              label: Text(t('save')),
            ),
          ],
        ),
        const SizedBox(height: 20),
        Text(
          '${t('history')} · ${state.entries.length}',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 10),
        if (state.entries.isEmpty)
          SectionCard(
            children: [
              const Icon(Icons.auto_stories_outlined, size: 42),
              const SizedBox(height: 12),
              Text(t('empty')),
            ],
          ),
        for (final entry in state.entries)
          SectionCard(
            children: [
              Text(
                pets[entry.petId] ?? '',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Text(
                localTime(entry.observedAt),
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              Text(
                t('observation'),
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              Text(entry.observation),
              if (entry.hypothesis.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  t('hypothesis'),
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Text(entry.hypothesis),
              ],
              if (entry.followUp.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  t('followUp'),
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Text(entry.followUp),
              ],
              const SizedBox(height: 12),
              Text(t('guardian'), style: Theme.of(context).textTheme.bodySmall),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: _saving
                      ? null
                      : () async {
                          if (await confirmDelete(context, t, 'deleteEntry')) {
                            try {
                              await widget.repository.removeEntry(entry.id);
                            } catch (error) {
                              if (context.mounted) {
                                showFailure(context, t, error);
                              }
                            }
                          }
                        },
                  icon: const Icon(Icons.delete_outline),
                  label: Text(t('delete')),
                ),
              ),
            ],
          ),
        const SizedBox(height: 16),
        Text(t('notice'), style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
