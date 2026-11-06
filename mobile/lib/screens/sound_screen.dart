import 'dart:async';

import 'package:flutter/material.dart';

import '../audio_api.dart';
import '../audio_capture.dart';
import '../l10n.dart';
import '../models.dart';
import '../repository.dart';
import '../ui.dart';

class SoundScreen extends StatefulWidget {
  const SoundScreen({
    super.key,
    required this.repository,
    required this.copy,
    this.recorder,
    this.analyzer,
  });
  final LocalRepository repository;
  final Copy copy;
  final RecorderPort? recorder;
  final SoundAnalyzer? analyzer;
  @override
  State<SoundScreen> createState() => _SoundScreenState();
}

class _SoundScreenState extends State<SoundScreen> with WidgetsBindingObserver {
  late final CaptureController _capture;
  late final SoundAnalyzer _analyzer;
  late final TextEditingController _server;
  final _token = TextEditingController();
  bool _dog = false, _consent = false, _sending = false, _saving = false;
  int _generation = 0;
  SoundResult? _result;
  String? _message;
  @override
  void initState() {
    super.initState();
    _server = TextEditingController(text: widget.repository.state.server);
    _capture = CaptureController(widget.recorder ?? DeviceRecorder())
      ..addListener(_changed);
    _analyzer = widget.analyzer ?? SoundAnalyzer();
    WidgetsBinding.instance.addObserver(this);
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  void _cancelRequest() {
    _generation++;
    _analyzer.cancel();
    _sending = false;
    _result = null;
    _consent = false;
  }

  void _clear() {
    _cancelRequest();
    _token.clear();
    _dog = false;
    _message = null;
    unawaited(_capture.cancel());
    if (mounted) setState(() {});
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Keep only the pending permission dialog alive; app-switch previews clear existing audio.
    if ([
          AppLifecycleState.paused,
          AppLifecycleState.hidden,
          AppLifecycleState.detached,
        ].contains(state) ||
        (state == AppLifecycleState.inactive &&
            _capture.phase != CapturePhase.requesting)) {
      _clear();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _generation++;
    _analyzer.cancel();
    _capture.removeListener(_changed);
    _capture.dispose();
    _token.clear();
    _token.dispose();
    _server.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    if (_sending) return;
    final pcm = _capture.pcm;
    if (pcm == null) return;
    final generation = ++_generation;
    setState(() {
      _sending = true;
      _message = null;
      _result = null;
    });
    try {
      final result = await _analyzer.analyze(
        server: _server.text.trim(),
        token: _token.text,
        wav: pcmToWav(pcm),
        consent: _consent,
        dogConfirmed: _dog,
      );
      if (mounted && generation == _generation) {
        setState(() => _result = result);
      }
    } catch (error) {
      if (mounted && generation == _generation) {
        setState(
          () => _message = error is AppFailure ? error.code : 'connection',
        );
      }
    } finally {
      if (mounted && generation == _generation) {
        setState(() {
          _sending = false;
          _consent = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.copy;
    final idle = [
      CapturePhase.idle,
      CapturePhase.ready,
    ].contains(_capture.phase);
    final phaseText = switch (_capture.phase) {
      CapturePhase.idle => 'idle',
      CapturePhase.requesting => 'requesting',
      CapturePhase.recording => 'recording',
      CapturePhase.stopping => 'stopping',
      CapturePhase.ready => 'ready',
    };
    return PageBody(
      children: [
        SectionCard(
          children: [
            const Icon(
              Icons.graphic_eq_rounded,
              size: 48,
              color: Color(0xff386957),
            ),
            const SizedBox(height: 16),
            Text(
              t('soundTitle'),
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            Text(t('soundBody')),
            const SizedBox(height: 24),
            Text(
              '${_capture.seconds.toStringAsFixed(1)} / 10.0 s',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: _capture.seconds / 10,
              minHeight: 8,
              borderRadius: BorderRadius.circular(8),
            ),
            const SizedBox(height: 12),
            Text(t(phaseText), textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton.icon(
              key: const Key('record'),
              onPressed: !idle || _sending
                  ? null
                  : () {
                      _cancelRequest();
                      _dog = false;
                      _message = null;
                      unawaited(_capture.start());
                    },
              icon: const Icon(Icons.mic_none_rounded),
              label: Text(t('record')),
            ),
            if (_capture.phase == CapturePhase.recording)
              OutlinedButton(onPressed: _capture.stop, child: Text(t('stop'))),
            TextButton(
              key: const Key('discard'),
              onPressed: _clear,
              child: Text(t('discard')),
            ),
            if (_capture.error != null)
              Text(
                t(_capture.error!),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
        SectionCard(
          children: [
            Text(
              t('connectionTitle'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            Text(t('connectionBody')),
            const SizedBox(height: 20),
            TextField(
              key: const Key('server'),
              controller: _server,
              maxLength: 300,
              enabled: !_sending && !_saving,
              keyboardType: TextInputType.url,
              autocorrect: false,
              enableSuggestions: false,
              decoration: InputDecoration(
                labelText: t('server'),
                hintText: 'https://your-server.example',
              ),
              onChanged: (_) => setState(() {
                _cancelRequest();
                _token.clear();
                _message = null;
              }),
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: _sending || _saving
                    ? null
                    : () async {
                        setState(() => _saving = true);
                        try {
                          await widget.repository.settings(
                            server: _server.text,
                          );
                          if (mounted) setState(() => _message = 'serverSaved');
                        } catch (error) {
                          if (context.mounted) showFailure(context, t, error);
                        } finally {
                          if (mounted) setState(() => _saving = false);
                        }
                      },
                child: Text(t('saveServer')),
              ),
            ),
            TextField(
              key: const Key('token'),
              controller: _token,
              obscureText: true,
              maxLength: 4096,
              enabled: !_sending,
              autocorrect: false,
              enableSuggestions: false,
              decoration: InputDecoration(
                labelText: t('token'),
                helperText: t('tokenHint'),
                counterText: '',
              ),
              onChanged: (_) => setState(() {
                _consent = false;
                _result = null;
              }),
            ),
            const SizedBox(height: 12),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _dog,
              onChanged: (value) => setState(() {
                if (_sending) _cancelRequest();
                _dog = value ?? false;
                _consent = false;
              }),
              title: Text(t('dogConfirm')),
            ),
            CheckboxListTile(
              key: const Key('sendConsent'),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _consent,
              onChanged: (value) => setState(() {
                if (_sending) _cancelRequest();
                _consent = value ?? false;
                _result = null;
              }),
              title: Text(t('sendConsent')),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              key: const Key('sendAudio'),
              onPressed:
                  !_sending &&
                      _capture.phase == CapturePhase.ready &&
                      _dog &&
                      _consent
                  ? _send
                  : null,
              icon: const Icon(Icons.send_outlined),
              label: Text(t(_sending ? 'sending' : 'send')),
            ),
            if (_sending) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
              TextButton(
                onPressed: () => setState(() {
                  _cancelRequest();
                  _message = 'cancelled';
                }),
                child: Text(t('cancelSend')),
              ),
            ],
            if (_message != null)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Text(t(_message!)),
              ),
          ],
        ),
        if (_result != null)
          SectionCard(
            children: [
              Text(t('result'), style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                t('abstain'),
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              for (final score in _result!.scores)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${t(score.label)}   ${score.score.toStringAsFixed(3)}',
                      ),
                      const SizedBox(height: 4),
                      LinearProgressIndicator(value: score.score),
                    ],
                  ),
                ),
              const SizedBox(height: 12),
              Text(t('scoreNotice')),
            ],
          ),
      ],
    );
  }
}
