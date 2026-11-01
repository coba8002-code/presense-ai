# 실제 음원 학습 실행 · 2026-11-01

이번 작업은 합성 데이터 실행이나 사전학습 모델 추론 재생이 아니다. 기존 확보된 ESC-10 실제 음원 400개에서 34차원 로그 주파수대/음량/영교차율 특징을 추출하고 softmax 회귀 가중치를 새로 학습했다. 개 소리 40개와 환경/배경음 360개를 구분하는 작은 연구용 기준 모델이다. AST·VLM 파인튜닝, 유튜브 학습, 행동 원인·감정·의도 학습은 아니다.

## 출처와 분할

[공식 ESC-50 저장소의 ESC-10 부분집합](https://github.com/karolpiczak/ESC-50/tree/33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6)을 사용했다. 공식 README는 ESC-10으로 표시된 400개를 CC BY로 구분한다. ESC-50 전체의 비상업용 나머지는 사용하지 않았다. 원본/전처리 음원의 SHA256, 원본 녹음 그룹, 카테고리와 공식 fold를 검사하고 원래 LICENSE의 개별 출처 표시를 산출물에 보존했다.

fold1–3: 학습240개(개24), fold4: 검증80개(개8), fold5: 보류 평가80개(개8). 같은 원본 녹음 그룹/동일 내용 해시가 분할 사이에 겹치면 중단한다. 정규화는 학습 데이터에서만 계산하고, 학습 데이터만 균형 재표집한다. 고정 penalty0.001/0.01/0.1 중 검증 macroF1로 선택한 값은0.1. 평가 데이터로 가중치·정규화·penalty를 선택하지 않는다. 결과를 확인한 fold5는 이후 반복 튜닝의 최종 독립 검증 자료로 주장할 수 없다.

개체·가정 식별자는 제공되지 않았다. 이를 원본 녹음 ID로 대체하거나 가상의 animal_id를 만들지 않았다. 동물 개체 독립 평가/서비스 승격 요건은 충족하지 못하므로 기존 생산용 preflight나 registry의 training_approved를 변경하지 않는다. 별도의 연구 전용 형식으로만 가중치를 저장하며 자동 배포·서비스 모델 교체는 하지 않는다.

## 실제 결과

| 보류 평가80개 | 결과 |
|---|---:|
| 정확도 |82.5%|
| macroF1 |0.6785|
| 개 소리 F1 |0.4615|
| 개 소리 정밀도 |33.33%|
| 개 소리 재현율 |75.0%|
| 배경음 오분류율(클립 기준) |16.67%|
| 모두 배경음이라고 예측하는 기준의 정확도 |90.0%|

혼동행렬은 실제 배경72개 중 배경60/개12, 실제 개8개 중 배경2/개6이다. 정확도82.5%만으로 우수한 모델이라고 평가하면 안 된다. 다수 클래스 기준보다 정확도가 낮고 오탐이 많아 **운영 적용 불가**다. macroF1은 다수 클래스 기준0.4737보다 높지만 평가 양성은8개뿐이며 실제 개체/가정 독립 성능이 아니다. 0.7 확신 점수의 보류율도 실측 교정 확률이나 감정 확률이 아니다. 시간당 오탐·실제 발성 구간 정확도는 측정하지 않았다.

실행 증거/산출물 SHA는 [ESC10_RESEARCH_20261101.json](evidence/ESC10_RESEARCH_20261101.json)에 기록했다. 로컬 artifacts/esc10-trained-research-20261101-v2에 report.json, research-model.json, attribution.txt를 생성했다. 최초 결과 보존 후 두 번째 실행은 다수 클래스 기준과 정밀도/재현율 보고 추가에 대한 재현이며 다른 학습 설정을 탐색하지 않았다.

## 재현

기존 Python 환경의 requirements.lock을 사용한다. 이미 원본·전처리가 있으면 마지막 명령만 실행한다. 출력 경로는 새 디렉터리여야 한다.

```sh
python -m scripts.acquire_esc10 --output data/esc10-source
python -m local_pc.pc prepare-esc10 --input data/esc10-source --output data/esc10-prepared
python -m training.esc10_experiment --source data/esc10-source --prepared data/esc10-prepared --output artifacts/esc10-research
```

## 국내외 확대 조사와 다음 실험

범위는 국내외 모두다. [Barkopedia](https://github.com/UTA-ACL2/Barkopedia), [DogSpeak](https://huggingface.co/datasets/ArlingtonCL2/DogSpeak_Dataset), [Canine Age Transition](https://huggingface.co/datasets/ArlingtonCL2/Canine-Age-Transition-Vocalization-Dataset), [BEANS](https://github.com/earthspecies/beans), [CC0 표기 테스트 음원](https://huggingface.co/datasets/petdecoder/pet-decoder-audio-fixtures)을 추가 검색했다. 이번에는 이 후보들을 다운로드·학습한 것이 아니다. DogSpeak/연령 데이터 카드의 NC-SA 표기, Barkopedia의 원천 영상 이용 조건, 테스트 효과음의 편집/개체 정보 등을 따로 확인해야 한다. 카드의 감정/나이/크기 명칭을 행동 원인 정답으로 바꾸지 않는다.

후속 우선순위는 오탐 유발 실제 생활 잡음과 여러 개체의 원본·보호자 동의 수집 → 개체/가정/원본 분리 잠금 평가셋 → 학습/검증에서 전이학습·교정 → 새 잠금 평가셋에서 AST/신규 모델 비교다. 유튜브 4후보는 기존 SOURCE_AUTOMATION_DELIVERY의 분석/검수 대기 상태다. 실제 영상 접근·API 인증이 없어 영상 학습을 수행하지 않았으며, 새 음원 연구 실험으로 유튜브 학습 완료라고 표시하지 않는다.
