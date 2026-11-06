import 'package:flutter/material.dart';

import 'l10n.dart';
import 'models.dart';

class SectionCard extends StatelessWidget {
  const SectionCard({super.key, required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: children,
      ),
    ),
  );
}

class PageBody extends StatelessWidget {
  const PageBody({super.key, required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Center(
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 720),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: children,
      ),
    ),
  );
}

void showFailure(BuildContext context, Copy copy, Object error) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(copy(error is AppFailure ? error.code : 'storage'))),
  );
}

Future<bool> confirmDelete(
  BuildContext context,
  Copy copy,
  String explanation,
) async =>
    await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(copy('confirm')),
        content: Text(copy(explanation)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(copy('cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(copy('delete')),
          ),
        ],
      ),
    ) ??
    false;
String localTime(DateTime time) {
  final date = time.toLocal();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${date.year}-${two(date.month)}-${two(date.day)} ${two(date.hour)}:${two(date.minute)}';
}
