# 경량 VLM 선택과 LoRA 튜닝

검토일: 2026-10-18. 개 전용 MVP의 기존 하이브리드 설계에 추가하는 실험이다.

## 공식 GitHub 조사와 선택

| 후보 | 공식 소스 | 이번 결정 |
|---|---|---|
| SmolVLM2 256M | [Hugging Face smollm](https://github.com/huggingface/smollm/blob/main/vision/smolvlm2/README.md), [모델 카드](https://huggingface.co/HuggingFaceTB/SmolVLM2-256M-Video-Instruct) | 첫 구현. 작은 크기, 공식 LoRA 경로, Apache-2.0 모델 라이선스 확인 |
| SmolVLM2 500M | [모델 카드](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct) | 256M 정확도가 부족할 때 동일 평가셋으로 비교할 다음 후보 |
| InternVL 계열 | [OpenGVLab/InternVL](https://github.com/OpenGVLab/InternVL) | 소형 계열 대안. 개 데이터 평가·가중치별 라이선스 확인 후 선택 |
| Qwen3-VL 2B | [QwenLM/Qwen3-VL](https://github.com/QwenLM/Qwen3-VL) | 더 큰 서버용 비교 후보. 이번 실행 대상 아님 |

256M을 선택한 이유는 검증 비용이다. 개 행동 정확도가 가장 높다는 의미가 아니다.
공식 카드의 비디오 추론 GPU 메모리 1.38 GB는 제공자 수치이며 우리 측 측정값이나
학습 메모리 요구량이 아니다. 모델 이름은 Video지만 이번 경로는 정지 프레임만 받는다.
범용 벤치마크 점수를 반려견 교정 정확도로 환산하지 않는다.

고정 모델: `HuggingFaceTB/SmolVLM2-256M-Video-Instruct`.
고정 revision: `067788b187b95ebe7b2e040b3e4299e342e5b8fd`.
원격 Python 코드 실행을 끄고 safetensors 가중치를 읽는다. 모델 라이선스와 학습 영상의
사용 권리는 별개다. 권한 없는 방송/YouTube 영상을 자동 수집하여 학습하지 않는다.

## 구현 범위

`training.small_vlm`은 언어 attention q/v projection에만 rank 8, alpha 16 LoRA를
붙이고 기본 모델·시각 인코더를 고정한다. AdamW, 학습률 1e-4, seed 42, 배치 1,
FP32 CPU로 재현 가능한 첫 실험을 구성했다. 이는 최적화된 최종 하이퍼파라미터가 아니다.
프롬프트와 이미지 토큰에는 loss를 주지 않고 답변 토큰만 학습한다.

출력은 `standing`, `sitting`, `lying`, `unknown`이다. 규격 밖 응답은 unknown으로
처리하지만, 모델이 고양이를 보고 sitting이라고 틀리게 답하는 것을 코드가 완전히
차단하는 것은 아니다. 별도의 비개체·가림·다중 개 평가셋이 필요하다. 감정·질병·교정
판단, walking 같은 시간적 행동은 이번 단일 프레임 학습의 범위 밖이다.

기존 `/v1/vision/observe` 서비스에 자동 연결하거나 모델을 운영 배포하지 않는다.
LoRA는 학습할 파라미터를 줄이는 방법이며, 기본 모델의 추론 메모리를 자동으로
줄여주지는 않는다. 모바일 배포·INT4/INT8·ONNX/Core ML 변환은 정확도 확인 후 진행한다.

## 실행

기존 서버와 분리된 Python 3.12 환경을 사용한다. 아래 설치는 네트워크가 필요하며,
공개 사전학습 가중치 약 1 GB를 처음에 내려받는다. 모델 API 키는 필요 없다.

```sh
python -m venv /tmp/presense-vlm-env
. /tmp/presense-vlm-env/bin/activate
python -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-vlm.txt
python -m training.small_vlm --smoke --steps 2 --output artifacts/smolvlm-smoke
```

Smoke는 자체 생성한 단색 이미지에 unknown을 학습한다. 실제 사전학습 가중치를 불러
optimizer를 실행하지만 **개 데이터 미세조정이나 정확도 검증은 아니다**. 유한 loss,
LoRA 파라미터 변화, safetensors 저장 후 재로딩 일치, 생성 실행을 검증한다.
GitHub Actions `pretrained-small-vlm-smoke`에서 실행하며 어댑터와 report를 7일간 보관한다.
ML 직접 의존성은 버전을 고정했지만 전이 의존성 전체 해시 잠금·취약점 감사는 후속이다.

실제 데이터 실행:

```sh
python -m training.small_vlm --manifest data/dog-frames/frames.json --registry data/dog-frames/registry.json --steps 100 --output artifacts/dog-posture-run1
python -m training.small_vlm_infer --run artifacts/dog-posture-run1 --image data/dog-frames/example.png
```

100 steps는 실행 예시다. 데이터 규모·validation 결과에 따라 조정하고 test를 반복해서
보며 파라미터를 고르지 않는다. smoke 어댑터 추론에는 `--allow-synthetic`을 명시해야 한다.
기존 출력 디렉터리는 덮어쓰지 않는다.

## 데이터 계약과 평가

frames.json은 아래 형태의 배열이다. 예시는 형식 설명용이며 실제 파일·권한 증빙이 아니다.

```json
[{
  "path": "frames/dog01-sitting.png",
  "sha256": "실제 파일의 SHA256 64자리",
  "species": "dog",
  "label": "sitting",
  "animal_id": "dog01",
  "recording_group": "session01",
  "source_id": "owned-video01",
  "dataset": "owned-dogs-v1",
  "reviewer": "expert01",
  "review_evidence": "검토 기록 위치",
  "reviewed_at": "2026-10-18",
  "split": "train"
}]
```

registry.json은 기존 `training.data.approve_dataset` 계약을 사용한다. status approved,
training_allowed/commercial_allowed true 및 source/version/license/rights_evidence/
consent/reviewer/reviewed_at이 필요하다. 이 값은 운영자의 검토 선언이며 법적 증빙의
진위를 자동 확인하지 않는다. 기존 비디오 리뷰 결과가 이 manifest로 자동 변환되지는
않는다. 권한 있는 원본에서 프레임 추출·시점·자세 재검토가 먼저 필요하다.

최소 5마리, 2개 이상 라벨, train/validation/test의 모든 라벨 포함을 요구한다.
개체·녹화 세션·원본 source가 partition을 넘으면 거절한다. 동일 SHA256 중복, 경로
탈출, 파일 변조, 고양이, 미검토 필드는 거절한다. 프레임은 PNG/JPEG 8 MB 이하,
400만 화소 이하. 바이트 hash는 근접 중복을 찾지 못하므로 전역 개체 ID 관리와
가구 단위 분리·근접 중복 감사가 추가로 필요하다.

실제 실행 report에는 baseline/tuned validation, baseline/tuned test의 accuracy,
지원되는 정답 클래스 기준 macro F1, confusion matrix, abstention coverage와 selective
accuracy가 포함된다. 확률 보정은 미구현으로 null을 기록한다. production_ready는
항상 false다. 데이터 fingerprint, 권리 선언, seed·모델 revision·loss도 저장한다.
전체 split별 표본 수·불확실성 구간, calibration, 실제 기기 지연·메모리 측정 및 외부
검수자의 평가를 완료하기 전에는 제품 정확도나 배포 준비 완료를 주장하지 않는다.

## 후속 순서

1. 권한 확보한 실제 개 프레임과 독립 검수 라벨 확보, 미검토 학습 차단 유지.
2. baseline 대 LoRA 평가, 품종·크기·조명·가림별 실패 분석 및 unknown 검증.
3. validation으로 학습률/rank/steps 선택 후 고정 test 1회 평가.
4. 필요할 때 500M 또는 2B와 품질·메모리·지연 비교.
5. 짧은 프레임 시퀀스로 시간적 행동 학습을 별도 구현.
6. 양자화 전후 동일 평가 후 서버 배치, 이후 모바일 후보 기기 평가.

## 실행 증거

[CPU pretrained smoke CI](https://github.com/coba8002-code/presense-ai/actions/runs/39128020164)
성공: 실제 모델을 불러 2 steps 실행, trainable parameters 460,800,
loss 3.321520 → 3.191215, optimizer 구간 약 5.18초. adapter_changed=true,
adapter_reload_equal=true, synthetic=true, production_ready=false.
이 시간은 모델 설치·다운로드·로딩을 제외하므로 서비스 응답 지연으로 사용하지 않는다.
[합성 smoke 어댑터 다운로드](https://github.com/coba8002-code/presense-ai/actions/runs/39128020164/artifacts/12136917167)
(7일 보관). 로컬 unittest 108개 통과. 실제 개 학습 데이터는 아직 제공되지 않아
실제 자세 미세조정 및 정확도 비교 결과는 없다.


2026-11-01 후속: 학습 어댑터가 아닌 공개 고정 base 모델의 로컬 AV 프레임 추론/보고서 UI를 구현했다. 실행/한계/검증은 [EVENT_ANALYSIS_DELIVERY](EVENT_ANALYSIS_DELIVERY.md)의 Actual local model execution 절을 따른다. 실제 개 정답/비개체 유보 정확도는 미검증이며 프로덕션 API 자동 배포가 아니다.
