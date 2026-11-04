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

## Continued completion: candidate events, consented model history and reviewed feedback

### Event postprocessing

`training.event_candidates.candidates` applies bounded experimental hysteresis (enter .6 / exit .4 / maximum gap .2s) to validated, ordered window scores. It yields candidate envelopes, first/last window boundary ranges, peak raw scores and clipping/near-silence flags. Same-label repetition is represented by distinct candidate spans; parent/child AudioSet labels may overlap. Thresholds are NOT fitted or validated. Ranges are score-window envelopes, not confidence intervals or verified onset/offset. No noise SNR, speaker, emotion, intent or definitive event label is inferred. Final decision remains abstain. The actual AV AST worker now generates these candidates and the report UI displays them separately; it does not turn them into caregiver annotations or training data.

### Persisted model observations (schema8)

API `/v1/me/observations` snapshots only completed owner jobs with recognized server execution provenance, pinned AST/model revision, input-hash/job-fingerprint agreement and verified PCM duration (measured from actual job input in JobStore.finish, not accepted from client/model claims). Synthetic fixtures are a separate source_kind from actual pretrained computation; neither proves real dog content. Raw media, client-supplied model scores, source claims, timestamps or approval fields cannot be uploaded through this metadata API.

Source is computational provenance, not a proof of species/real animal/recording truth. Same dog, device ID and condition are guardian attestations. Observations retain species_verified=false, training_approved=false and server-submission time explicitly labelled not capture time. UUID and source-job/context/model/input snapshot are immutable through the API. A replay returns the same ID without extending retention; different context for an existing source is rejected. Delete and explicitly re-save creates a new snapshot, not an edited old record.

`/app` → model observation history: enter nonpersonal device ID/condition, confirm same dog and separate metadata+feedback storage consent, then select “모델 관찰로 별도 보관” on a completed job. No automatic storage on completion. History lists stored contexts, uncalibrated scores/source/version and insufficient history. Comparison uses only one dog/model/revision/source/device/condition and the latest record's100ms duration bucket, with >=5 prior UTC recorded days; unknown condition is insufficient. Display daily-mean score medians and latest-minus-median deltas, not event frequency, emotional state or improvement. Self-selected sample/device/context limitations remain. All guardian-only journals, synthetic computation and actual model computation stay separate.

Maximum200 metadata snapshots per owner, up to30days capped by profile expiry. Normal24h job-result expiry does not erase separately consented metadata; explicit job cancellation/result deletion DOES erase linked observations/feedback. Profile/account deletion, observation deletion and independent TTL maintenance cascade. Original audio retains existing15min/complete/cancel deletion policy and is never copied into model history. Shared journal viewers do not gain model-history access. Source hashes/IDs/scores are private owner data. Browser holds no new local/sessionStorage and clears results on identity/profile/context changes; pending requests are aborted and stale responses rejected.

Separate consent is `X-Observation-Consent: model-metadata-v1`; same-dog confirmation must be boolean true. Unchecking stops future storage and aborts pending UI updates; it does NOT guarantee rollback of an already received POST. UI says to query/delete any existing record. Cookie/CSRF/current-origin checks and no-store headers reuse existing account safeguards. No new production account role, provider credentials or network settings.

### Feedback and local review

Owner feedback is a fixed reason enum, immutable until withdrawn, initially unreviewed and never training-approved. Client approval/status/model fields are rejected. Owner can withdraw feedback independently or delete the observation. No feedback value changes model output, becomes a truth label, or trains automatically.

`python -m evaluation.feedback_review --db <existing-private-db> --card <local-review-card.json>` defaults read-only. Card binds observation UUID/payload hash and a feedback digest, requires two distinct reviewer IDs, qualification-evidence assertions and explicit identity-blind attestation. Disagreement yields disputed; missing evidence yields needs_more_evidence; agreement can record reviewed_not_training_approved. Qualification evidence is NOT independently verified and agreement is NOT fact/licensing approval. Original audio may already be deleted; lack of source evidence must not be hidden by reviewer consensus.

`--write-review` is an explicit local operator action using already-held filesystem access; no web endpoint or elevated role exists. Only current-schema unexpired observations/feedback/profile are accepted. Read source under transaction; stale hashes, withdrawn feedback or different existing immutable review are rejected. Store only card hash/time and nonapproval status, not reviewer evidence text or new labels. Identical-card replay is idempotent. Real review cards are not generated by the system and were not applied to real customer records in this work.

Card schema: observation_id, observation_payload_sha256, feedback_sha256 (canonical hash of immutable feedback id/owner/observation_id/created/reason), reviews[2] each containing reviewer, qualification_evidence, verdict (supports/contradicts/needs_more_evidence), model_identity_hidden=true. Actual reviewers and lawful source evidence remain external requirements.

### Detector/keypoint and Dog2vec comparison adapters

`python -m training.track_pose --input supplied-detections.json --output adapter-result.json` validates bounded common-clock, source hash, boxes and17 named keypoints. Mutual IoU association with ambiguity margin/gap guards creates clip-local geometry candidate IDs; occlusion/missing/ambiguous crossings do not preserve identity. Neck/tail-root confidence gates optional torso angle. No detector is run, no global pet ID or speaker is verified, no posture/motion/emotion label is inferred. Source detections/model/revision remain caller assertions. Synthetic unique/crossing/gap/occlusion/invalid geometry tests prove adapter logic only. An independently reviewed detector/keypoint model is still needed.

`training.dog2vec_adapter` records actual upstream source/Zenodo file/checksum/cc-by-4.0 weight metadata. Supplies a bounded injected feature contract (layer9 HuBERT-base768-dimensional features), mean/unit pooling with no task labels. It imports no fairseq/checkpoint, downloads nothing and requires explicit code-use evidence before non-synthetic extraction. It does not make an unlicensed-code assumption from weight license metadata. Runtime readiness exposes unresolved fairseq/code/data rights and unsafe legacy .pt deserialization; official helper defaults CUDA and generic Fairseq checkpoint loader, so no blind execution was performed. Actual trained task-head comparison against AST still requires licensed runtime, hashed weights and the same locked independent dog labels. Metadata checksums are not cryptographic proof of authorship.

### Migration and regression evidence

Schema7→8 adds model_observations/observation_feedback transactionally and preserves members, sessions, pets, jobs, journals/shares/plans. Metadata source remains immutable; no production DB was modified here. Run current source initialization/migration with workers stopped before current-schema privacy maintenance; older code cannot open higher schema. Physical encrypted backup/restore and real device operations are separate release gates.

Tests cover duration bound to raw input rather than model claim, owner/CSRF/consent/extra-field denial, source/context isolation,5-day threshold, migration preservation, metadata expiry, job cancellation, pet/account erasure, feedback withdrawal/review binding/disagreement/stale review rejection, candidate hysteresis/uncertainty/quality, supplied tracking/pose, Dog2vec contract gates. Existing HTTPS account browser now exercises separate consent→save→source-labelled lookup→feedback→withdraw→stored-context discovery→account cascade, with actual AST and mocked-source variants. All source media/identities used for these tests are synthetic.

## Actual detector and animal-keypoint runtime completion

Further model research found a lightweight animal-specific candidate, not just a supplied-output interface. Public Hub metadata identifies `PekingU/rtdetr_r50vd` revision `df939e661d8c52e80608d1ec566561aabd25a4e7` and `litert-community/RTMPose-Animal-AP10K-LiteRT` revision `1daee634c9db6889268124735374e6a9c1c2fc7b`, both with Apache-2.0 model-card metadata. The latter is a community OpenMMLab AP10K conversion, not an endorsement or independently validated accuracy result. Its17 AP10K animal joints are distinct from human COCO joints. A ViTPose candidate exposed human keypoint labels despite multiple backbone experts, so no human-head outputs were relabelled as animal anatomy.

The actual cached RT-DETR safetensors dog-class detector and animal RTMPose LiteRT interpreter now execute in the existing isolated AV worker with `--with-pose`. Only detections with the fixed experimental .7 dog-score threshold are passed to the animal pose model; keep at most4 candidates across at most6 frames. Empty detection means no accepted candidate, not proof no dog exists. TFLite model input is float32 NCHW1x3x256x256, outputs17x512 SimCC x/y each. Crops are1.2x square bounding-box extents, RGB mean/std as the publisher card; decoded bin argmax/2 maps back to the scaled decoded-frame plane. Padded/out-of-frame points are clipped with zero visibility score. Point confidence is a clipped raw SimCC peak, NOT a probability or validated visibility classifier. Imported results retain species_verified=false, identity_verified=false and abstention.

Before native model construction, check full artifact SHA256 against public Hub LFS metadata: detector `5263d5521eff3e356f6cd8a371fd5dfb891725beda5f713674f79669115cdc64` (172,175,856bytes); pose `7fbfc03239cebc1f657efab722849bc9b30d36d3d4371118aed2aaf4041e742f` (27,526,176bytes). Loads are fixed-revision, local-files-only, safetensors for the detector, native LiteRT2.3.0 for keypoints. No remote Python or arbitrary pickle is loaded. CPU threads are bounded. Weight-license metadata does not automatically approve every original training/photo source for new training.

```
# Separate setup, no customer media: add optional requirements-pose-model.txt
python -c "from training.dog_pose import prepare_public_cache; prepare_public_cache()"
# Actual local analysis (Linux/WSL, cached weights, explicit local consent)
python -m training.av_ast --video /local/path/clip.webm --consent-local \
  --with-vision --with-pose --output /local/path/model-report.json
```

The shared worker attaches pinned dog/pose metadata, source-frame times and scaled coordinate sizes. Supplied-box geometry association then creates clip-local candidate IDs, image-plane displacement and torso-angle deltas only for unambiguous short-gap matches. These are image geometry; no camera compensation, physical speed, global dog identity, speaker association, walking/emotion/intent or medical inference. Sparse gaps reset associations. This is a real detector/keypoint execution path with an unvalidated geometric association policy, not validated multi-dog tracking.

Existing report import checks model/revision/dimensions/frame/detection/keypoint bounds, displays candidate count/17-joint and clip-local association information separately from human notes, and always says that0 detections do not establish absence. No pose results are silently inserted into AST-score personal history or treated as human annotations/training labels. Report generator authenticity and real dog correctness remain unverified despite same-file hash binding.

Local generated color/sine AV test completed actual AST, SmolVLM, dog detector and browser report path. The detector found0 dogs, so no artificial dog box was fabricated. A separate explicitly synthetic full-frame native pose diagnostic produced17 finite decoded points to verify interpreter/decoder execution only; this diagnostic is not a detected dog observation and is not copied into the user report. Existing small-model CI warms fixed public cache, runs that native pose diagnostic, then exercises the combined AV/browser route. Runtime/operator approval is not required from AX; independent animal performance, original photograph rights, target-device performance and real tracking validation are still required before product promotion.

AP10K local annotation metadata lists MIT license and the17 animal joint names; original photograph provenance is still a separate issue. It was inspected for schema only. No actual AP10K photo was trained/evaluated or sent to a provider in this work. No paid training, real customer material, new account privileges, public deployment or merge occurred.
