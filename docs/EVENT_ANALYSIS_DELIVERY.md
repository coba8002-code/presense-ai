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

No probabilities means Brier is null. Provided sigmoid values are not automatically calibrated; Brier here concerns event presence, never emotion. Latency is supplied, not timed by evaluator. Cluster confidence intervals, keypoint localization/ID tracking metrics, explanation reviewer rubric and independent causal validation remain future evaluation work. Pose scores must still use video_predictions. Missing predictions and empty event lists have different meanings (abstain versus an accepted negative).

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
