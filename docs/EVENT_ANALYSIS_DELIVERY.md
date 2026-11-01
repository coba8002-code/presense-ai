# Event-aligned PetSense analysis: delivery contract

2026-11-01 KST. Builds on PR24 (3c994bc). All claims below separate measured implementation behavior from model accuracy.

## Completion matrix

| Work | Acceptance | State |
|---|---|---|
| Independent references | Reuse existing dog/household/session/source/hash split isolation, locked windows and rights registry | Implemented metadata validation; real independent evidence missing |
| Event benchmark | Bound event annotations to parent reference hash, exact evaluation clip set, source hash, finite bounded video-clock events | Implemented CLI and synthetic fixtures |
| Three-mode comparison | One each audio/video/fused run on identical reference windows, missing predictions count as abstention | Implemented; no actual mode inference run |
| Sound event metrics | Class F1, FP/hour on known windows, fixed tIoU .5 maximum-cardinality matching, onset/offset MAE and p95 supplied latency | Implemented; synthetic plumbing only |
| Identity/calibration | Matched-event reference speaker agreement/error; event-presence Brier for supplied seven-class probabilities | Implemented; unknown identity stays unknown, no calibrated model claim |
| Existing posture metrics | Existing video_predictions fixed four-class confusion/F1, known coverage and unknown abstention | Reused; real pose/ID tracker missing |
| Sound timeline adapter | Injected AST-compatible scorer over 1 s windows, .5 s hop plus final tail, explicit shared-clock offset, signal quality | Implemented offline; scores remain abstentions, no learned onset detector |
| Product timeline | Caregiver marks sound intervals in parent-video seconds; repeat count/gaps; first 3 events choose up to12 surrounding frames | Implemented browser flow; no automatic sound detection |
| Evidence UI | Show source, supporting times, inconsistent times, alternatives, missing evidence/questions, abstain on conflict | Implemented; no causal/intent/emotion claim |
| Personal baseline | Same-dog/same-model measured history, >=5 observed days, median rate and difference; feedback excluded from learning | Implemented offline descriptive adapter; not persistent product history |
| Research candidates | Verify model supply/license metadata and runtime before comparison | Dog2vec metadata checked; runtime/weight execution not done |
| Release evidence | Focused boundaries, full regressions, browser checks, exact HEAD CI | CI status recorded in PR |

## Execute the benchmark

```
python -m evaluation.event_evaluation \
  --parent docs/examples/video-evaluation/reference.synthetic.json \
  --registry docs/examples/video-evaluation/registry.synthetic.json \
  --reference docs/examples/video-evaluation/events.synthetic.json \
  --runs docs/examples/video-evaluation/event-runs.synthetic.json \
  --output /tmp/petsense-event-evaluation.json
```

Output is exclusive-create. Inputs <=8MB; models/events/windows bounded. Synthetic scores demonstrate plumbing, never animal performance. Event references must be known/unknown separately; known-empty windows allow false-positive measurement. Duplicate predicted events count as FP. Events cannot escape parent window. Threshold .5 tIoU is fixed evaluation policy, not a dog decision threshold. Event labels are the existing seven AudioSet labels and are not collapsed as synonyms. Parent reviewers/rights/identities and event reviewer names are metadata assertions, not independent verification of expertise, blind annotation or copyright rights. Actual recordings and review evidence must be audited before real evaluation.

No probabilities means Brier is null. Provided sigmoid values are not automatically calibrated; Brier here concerns event presence, never emotion. Latency is supplied, not timed by evaluator. Household-cluster intervals and a hash-bound explanation review rubric were subsequently implemented below; actual keypoint localization/ID tracking metrics and independent causal validation still require further evaluation work. Pose scores must still use video_predictions. Missing predictions and empty event lists have different meanings (abstain versus an accepted negative).

## Product flow

Run source locally, open `/app` → 영상 장면 살펴보기 (`/video-review`). Local consent + same-dog confirmation → bounded video → optionally mark sound start/end/type → event count/gaps and unconfirmed speaker → event-adjacent frames → direct posture annotations → supporting/inconsistent timestamps, alternatives/questions or abstention.

Video time is browser currentTime, not verified PTS or sensor sync. Marked sound source is always guardian_report; multiple dogs/offscreen speakers never become the target dog automatically. Inputting an event invalidates previous frames/results. Cancellation, file replacement, consent/identity withdrawal and departure discard all events, video, frames and results. Extraction interruption discards partial results. CSP connect-src none blocks uploads/model calls. No audio playback/analysis is performed (video stays muted); manual event marks may come from prior observation. Up to20 intervals are allowed, but only the first3 are used for frame sampling, explicitly disclosed. Automatic tracking, pose estimation, VLM extraction and real audiovisual synchronization are absent.

The initial UI heuristic is intentionally narrow; a back-facing ear/tucked-tail/crouched pose combination is merely an unvalidated avoidance possibility. A lack of opposite sampled cues does not prove their absence. No automatic action, health/intent label or probability is produced.

## Model and baseline adapters

`training.audio_timeline.analyze_windows(signal, scorer, offset=..., video_duration=...)` accepts <=30s mono16kHz signal. A trusted injected scorer uses the existing AST result contract. It performs no model loading, downloads, network, threshold learning or persistence. Scores do not become confirmed events. Offset is supplied and bounded; identity/synchronization remain unverified. Actual multi-window workload must later run under bounded worker deadline/cancel/GPU admission before API/UI integration.

`pet_baseline` requires explicit dog/model identity, bounded measured history and five observed day buckets. It returns descriptive rate delta with no diagnosis. Measurements are caller supplied and must later have immutable source IDs, verified timestamps, device/context stratification and retention consent before product persistence. Feedback and different-dog/model entries are excluded. It never exports learning labels or automatically trains. No durable baseline API/UI is claimed.

## Candidate evidence checked

- Dog2vec primary paper: https://kenzhu2000.github.io/papers/interspeech25-dog2vec.pdf (HTTP200, read). Paper links https://github.com/fispresent/dog2vec . README requires fairseq and links Zenodo. Repository API license field is null; files at root are README, data, extract_feature.py.
- Zenodo https://zenodo.org/api/records/15494042 returned open access and cc-by-4.0 metadata, with dog2vec_130k_9.pt (1,135,553,458 bytes). This is weight-record metadata, not approval of every training source or repository code. No weights downloaded/executed. Fairseq dependency compatibility, checkpoint safety, dataset rights and a frozen revision must be audited before adopting. AST remains the baseline. The paper's reported gains are not PetSense gains.
- Temporal animal pose reference https://link.springer.com/article/10.1007/s11263-023-01946-z and VLM limitation reference https://pmc.ncbi.nlm.nih.gov/articles/PMC12638295/ both returned HTTP200. They remain research references, not implemented models or accuracy evidence.

## Required external inputs and remaining development

Need rights-checked AI-Hub/raw data integrity and schema, independent dog/source/household identities, blind event/posture reviews and unknown windows; company permitted image-capable API/model/safe auth; domestic PC/device operational access. AX is unrelated. No real/customer media transmission, paid calls/training, new keys/access, network changes, deployment or merging occurred.

Remaining engineering beyond these initial contracts: independent review rubrics/adjudication for sound; reliable event detector and independent timestamp/PTS verification; actual tracking/pose/VLM adapters; verified speaker association; calibrated thresholds and cluster CIs; context-stratified persistent baselines and account consent/UI; real devices and operational performance/recovery. These are not marked complete by synthetic examples.

## Subsequent completion: real file-clock alignment and account reporting pattern

The original blockers were integration gaps, not company-model requirements. Added `training.av_alignment` to decode a consented local MP4/WebM without upload/model access. ffprobe returns decoded video/audio frame PTS and audio sample counts; ffmpeg produces bounded mono16kHz PCM. Continuous audio-frame timing and decoded length are checked; RMS windows use the first decoded video PTS as shared zero. Discontinuous clocks are rejected instead of silently repaired. VFR frame times are kept, not replaced with a constant frame-rate assumption. Silent-video reports explicitly have no audio. This verifies a container/file clock, not capture-sensor sync, sound identity or behavior.

```
python -m training.av_alignment --video /local/path/clip.webm \
  --consent-local --output /local/path/clip-alignment.json
```

Requires installed ffmpeg/ffprobe and existing Python/numpy, performs no automatic installation/download. Input <=25MB/30s/1920x1080. Local media is snapshotted in a private temporary directory; demuxers/protocols are allowlisted, subprocess output/deadline limited (45s overall), process groups killed on interrupt/cancel and temporary copies/PCM/metadata removed on every exit. Original video is never deleted. Cancellation flag supports embedding; Ctrl-C cancels CLI. Report is exclusively created. It contains hash/timestamps/energy, not extracted original audio/images or account details. The source hash is checked again to reject file changes during processing.

`/video-review`: choose the original consented file, then optionally choose the local JSON report (<=200KB). Browser SHA256 must match source, report duration/ordered finite PTS/audio intervals must validate. Hash binding is not a signature proving report origin; UI explicitly says report producer/capture sync are unverified. A different file, malformed clock or wrong hash is rejected. Display audio energy on the shared video axis and use reported video PTS near event-driven frame targets. This path never uploads the file/report or invokes a model; audio is not played by the muted player. Source/report replacement invalidates old frames/results. Consent/identity withdrawal/cancel also remove reports/energy from memory.

Existing journal summary now includes `record_pattern`, derived only from that owner's selected dog's unexpired, non-future guardian entries within the chosen existing 7/30-day window. It reports prior UTC recorded-day count and, after five such days, median entries per recorded day. Today without entries is null, never proof of no behavior. Historical days exclude today. Source is guardian_report, model_revision null, measurement condition self-selected reporting days; training_approved and measured_behavior_baseline remain false. Existing read permissions, deletion/TTL and stale-response/profile-change guards apply. English/Korean UI names this a reporting-pattern reference, not event frequency, model-personalization or evidence of improvement. No schema migration, new consent purpose, feedback learning or extra data retention.

Actual measured sound/movement baseline still needs independently sourced measurements and consented account persistence; it is not fabricated from self-selected diaries. Technical alignment does not implement automatic speaker/ID tracking or VLM interpretation.

Validation added: real generated AV fixture with known ~0.3s delayed audio, variable-frame-rate fixture, absent audio, damaged file, pre/mid-process cancellation and private temp cleanup; browser same-source report import, wrong-hash rejection, energy and reported-frame path; account reporting-pattern enough/insufficient history; existing English/Korean account/journal browser flow. All inputs synthetic, no dog behavior accuracy evidence.

## Independent audit completion: cluster intervals, failure review and explanation rubric

`evaluation.analysis_audit` reuses all event-evaluation binding and rights/split gates. It aggregates known-window TP/FP/FN/duration per household and computes deterministic household-cluster percentile bootstrap intervals for micro event F1 and FP/hour. Fewer than5 independent households returns insufficient status and null intervals. 100–2000 draws, fixed seed, valid F1 draw count, known-only scope and limitations are explicit. No BCa, representativeness or causal claim. The supplied reference registry/identities remain assertions requiring independent audit.

Failure queues preserve source hash/window and whether prediction is missing/abstained or mismatched. They are unreviewed and training_eligible=false. They support collecting failures for later adjudication/re-evaluation, never generate new ground truth or authorize use of media.

An optional human explanation rubric is bound to the exact normalized model-run digest AND the UTF-8 hash of each reviewed explanation text. Reviewer IDs must be distinct per clip; two reviews expose disagreements requiring adjudication. Dimensions: grounding, causal overclaim, emotion/intent overclaim, useful next question. Explicit identity-blind=true attestation is required. It does not prove reviewer identity/qualifications, consensus truth or automatic training approval. No explanations/reviewer names are copied into summary output; no network, storage API or training is invoked.

```
python -m evaluation.analysis_audit \
  --parent docs/examples/video-evaluation/reference.synthetic.json \
  --registry docs/examples/video-evaluation/registry.synthetic.json \
  --reference docs/examples/video-evaluation/events.synthetic.json \
  --run docs/examples/video-evaluation/analysis-run.synthetic.json \
  --reviews docs/examples/video-evaluation/explanation-review.synthetic.json \
  --output /tmp/petsense-analysis-audit.json
```

Input files <=8MB, exclusive output, bounded windows/reviews, offline only. Synthetic fixture has one validation household: null CI is the correct result, not an error. Six-household synthetic unit test verifies bootstrap reproducibility only. Real intervals and expert review require real independent groups and reviewers. This closes the evaluation software gap, not the evidence gap. Product integration remains the existing evidence UI; no automated expert validation is shown to users.

## Actual local model execution completion (AST + SmolVLM)

Company AX/API credentials are NOT required for this experimental local path. `training.av_ast` now runs fixed public pretrained AST and optionally SmolVLM2-256M in a private Linux/WSL child process against the same local consented source snapshot. The warm cache is required; model workers force HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE and strip key/token/password/secret/application environment variables. No network or model provider is used for media. Public weight cache setup is distinct from inference and must use the pinned revisions documented in PRETRAINED_AUDIO/SMALL_VLM_TUNING. It does not create a hosted service or new persistent access.

```
# In an isolated environment with requirements-vlm, torch/torchvision CPU and ffmpeg:
python -m training.av_ast --video /local/path/clip.webm --consent-local \
  --with-vision --output /local/path/local-model-report.json
```

Without --with-vision the same command only runs cached AST. File validation and explicit consent precede worker creation. The outer worker has a <=120s default deadline (configurable API bound <=300s), output <=200KB and no media in logs/stdout except the bounded metadata report. Model-assisted alignment uses a115s internal processing budget; plain alignment retains45s. Its nested ffmpeg/ffprobe processes share the isolated worker process group, so cancellation kills the group; all private media snapshots/results live under the parent's private temp root and are discarded. This isolated runner requires Linux/WSL; native Windows process-tree semantics are not claimed. Original input is preserved.

AST processes overlapping 1s windows with .5s hop plus the final tail. Trim/pad boundaries are reconciled with decoded source clock; output retains all7 uncalibrated independent sigmoid scores. Scores are NOT event onset/offset or calibrated dog probabilities. SmolVLM reads at most6 actually decoded PNG frames selected by index from ffprobe frame timestamps, using only safetensors, fixed revisions and trust_remote_code=false. It emits standing/sitting/lying/unknown posture candidates, never validated observations, tracking or motion. Both models retain decision=abstain and species_verified=false; non-dog rejection is not independently reliable. No fine-tuning, labels, emotion/intent, action recommendation or model promotion occurs.

Import the same-source model report into `/video-review`. Separate display shows pinned model/revision, raw audio-window top scores and frame posture candidates, labelled uncalibrated/unverified and not filled into guardian annotations. The report's source hash and schema/model/revision/window/score/candidate bounds are checked; generator authenticity is still not cryptographically verified. Existing CSP connect-src none and local consent/clear/cancel guards remain. No model is run inside the browser, and importing a report does not authorize training or server upload.

Local verification used an actual generated test-pattern video plus synthetic sine audio (no animal/customer data). The cached AST and SmolVLM forward passes completed, and the actual report was imported/rendered in Chromium at mobile viewport with no outbound requests. Six posture candidates were unknown for the generated test pattern. This is integration evidence only, not dog accuracy. New worker tests cover consent-before-spawn, timeout/cancellation, malformed output, stripped credentials and temp-root cleanup; frame hooks validate actual decoded PNGs. Existing CI pipelines now exercise actual cached AST-only and AST+SmolVLM AV/browser paths. The small VLM CI's pre-existing optimizer smoke remains synthetic and is not real dog training.

Remaining model work: automatic dog/speaker identity/pose/tracking, calibrated sound event thresholds, actual independent dog evaluation, trained/validated behavior interpretation and measured personalized baselines. Actual deployment and physical-device checks still require the domestic PC/device target. No model credentials need be posted in chat to use this local prototype path.
