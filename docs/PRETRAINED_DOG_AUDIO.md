# 개 소리 사전학습 모델 추론

2026-10-19 KST. 이번 변경은 **학습이 아니라 사전학습 가중치 추론**이다.

## 선택과 보류

- [Dog2vec 코드](https://github.com/fispresent/dog2vec), [가중치](https://zenodo.org/records/15494042):
  공개 1.1 GB 체크포인트와 배포 MD5는 확인했다. 읽을 수 있는 모델 배포 페이지의
  License 항목에 조건 본문이 없어 상업 이용 조건을 확정하지 못했다. 다운로드 가능과
  상업 이용 승인을 구분한다. 이번에는 설치·적용하지 않았다.
- [AVES](https://github.com/earthspecies/aves): 코드 MIT와 GCS 모델 배포 경로, 16 kHz
  embedding 출력은 확인했다. 가중치에 적용되는 조건을 별도로 확정하지 못해 보류했다.
  embedding은 짖음·하울링 라벨 자체가 아니므로 검수 자료로 분류 head를 학습해야 한다.
- [AST HF 배포](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593): 모델 카드
  BSD-3-Clause 표기와 safetensors 배포 확인. 기존 조사 후보 중 실제 소리 사건 라벨이
  있는 비교 기준선으로 선택했다. 원 연구 [GitHub](https://github.com/YuanGongND/ast).
  HF 카드가 HF 팀에 의해 작성된 점을 포함해 기록한다. 배포 조건 표기는 모델의 개 소리
  정확도, 원래 학습 데이터 전체의 권리 감사 또는 제품 출시 승인을 뜻하지 않는다.

Dog2vec/AVES 연결 완료로 표시하지 않는다. 이번 실행 대상은 AST이며 범용 AudioSet
모델에서 개 관련 라벨만 추출한다. 346 MB safetensors를 CPU에 불러오는 서버 실험으로,
경량 모바일 모델 또는 스트리밍 실시간 모델로 검증한 것이 아니다.

고정 revision: `f826b80d28226b62986cc218e5cec390b1096902`.
`trust_remote_code=False`, `use_safetensors=True`. 설치하는 라이브러리 직접 버전을
고정했으며 전이 의존성 전체 해시 잠금·취약점 감사는 후속 과제다.

## 실행

기존 서버와 별도의 Python 3.12 가상환경을 사용한다.

```sh
python -m venv /tmp/presense-audio-env
. /tmp/presense-audio-env/bin/activate
python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-audio-model.txt
python -m training.pretrained_audio --audio data/my-dog.wav --output artifacts/my-dog-ast.json
```

첫 실행에 공개 모델을 다운로드한다. 유료 API나 API 키는 필요 없다. 입력 음성은
외부 추론 서비스에 전송하지 않는다. 로컬 PCM16 WAV, 16 kHz, mono/stereo,
0.1~10초, 2 MB 이하만 받는다. 잘못된 파일은 모델 다운로드 전 거절한다.
스테레오는 평균을 취하며 서로 역위상인 소리는 상쇄될 수 있다. 임의 리샘플링·긴
영상 다운로드·자동 분할은 수행하지 않는다. 기존 출력 파일은 덮어쓰지 않는다.

출력은 원본 라벨 이름을 확인한 `Dog`, `Bark`, `Yip`, `Howl`, `Bow-wow`, `Growling`,
`Whimper (dog)` 점수다. 사람 `Whimper`를 개 낑낑거림으로 혼동하지 않는다.
AudioSet의 다중 라벨 성격에 맞춰 sigmoid를 사용한다. 개 라벨끼리 softmax로 재정규화해
잡음에서도 반드시 개 소리 하나를 고르는 방식은 사용하지 않는다.

점수는 보정된 확률이 아니며, 실제 개 평가로 임계값을 정하기 전까지 `decision=abstain`,
`species_verified=false`, `production_ready=false`다. cat 지원 또는 개체 확인 기능을
추가한 것이 아니다. 감정·의도·질병 라벨은 생성하지 않는다. 파일 전체 구간 점수이며
소리의 정확한 발생 시점은 제공하지 않는다.

기존 `/v1/audio/chunks`와 NumPy 모델 설정은 변경하지 않았다. 서로 다른 모델 형식과
입력 시간 창을 섞지 않기 위해 별도 CLI로 연결했다. 실시간 서비스 연결은 sequence gap,
시간 창·부하·임계값 평가 후 별도 작업으로 진행한다.

## 검증

로컬 unittest 112개 통과. 추가된 검사는 잘못된 PCM 형식·샘플레이트·절단 파일,
스테레오 평균, 라벨 순서 독립 매핑, 사람/개 Whimper 구분, 다중 라벨 점수 보존,
누락 라벨·비정상 수치 거절을 포함한다. pinned skills 및 Python 컴파일 확인.

`pretrained-audio-smoke` CI는 실제 AST 가중치로 자체 생성한 무음과 440 Hz 음을 추론한다.
각 파일의 반복 추론 일치, 유한 점수, 판정 보류를 검사하고 별도 CLI도 실행한다.
합성 소리를 개 소리로 표시하지 않으며 `dog_accuracy=null`로 기록한다. 결과 JSON은
Actions artifact로 7일 보관한다. 새 개 녹음을 학습하거나 정확도를 검증하는 테스트는 아니다.

## 남은 작업

1. Dog2vec/AVES 가중치 조건 확정 후 embedding 추론 어댑터와 분류 head 실험.
2. 사용 권한이 있는 개 녹음·사람 말·TV 재생음·생활 잡음·다른 동물 녹음으로 독립 평가.
3. 개체/가정/세션 분리, 클래스별 recall·오탐·calibration·coverage 및 지연 측정.
4. validation에서 임계값을 고정한 뒤 test 평가. 통과 후에만 앱/서버의 사용자 판정에 연결.

실행 결과: [실제 AST 추론 및 CLI CI](https://github.com/coba8002-code/presense-ai/actions/runs/39213061875) 성공. [백엔드·브라우저 CI](https://github.com/coba8002-code/presense-ai/actions/runs/39213065678)도 성공했다.
