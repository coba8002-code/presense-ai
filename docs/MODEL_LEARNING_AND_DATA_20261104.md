# 실제 음향 학습과 추가 확보 — 2026-11-04

## 실행한 모델 학습

확보·이용 범위가 검증된 기존 ESC-10 실제 음원400개를 사용해 NumPy softmax 분류 가중치를 새로 학습했다. 기존 원본/전처리 해시·CC BY 출처를 `training.esc10_experiment.load`로 재검사했다. 입력34차원, 600 gradient steps씩 후보3개를 비교하고 검증 fold4에서 penalty를 선택했다. 학습에는 fold1–3의 원본240개와 각 원본에 음량/훈련용 배경음을 조합한 강화 사본240개를 썼다. 검증80·시험80개는 강화하거나 학습 통계에 포함하지 않았다. 원본 수400개가480개나640개로 늘었다고 집계하지 않는다. 클래스 재표집은 훈련 자료 안에서만 한다.

배경 조합·음량 변화는 `augmentation_lineage`에 부모와 배경 원본 해시를 기록한다. 노이즈는 해당 학습 음원 RMS의0.1배로 맞추고 [-1,1]로 제한한다. 배경 반복은 실생활 소음 분포를 재현했다고 주장하지 않는다.

| 기존과 같은 시험80개 | 새 강화학습 결과 |
|---|---:|
| 정확도 |82.5%|
| 개 소리 F1 |0.461538|
| macro F1 |0.678530|
| 혼동행렬, 실제 배경/개 순서 |[[60,12],[2,6]]|
| 선택 penalty |0.001|
| 동물·가정 독립성 |미확인|
| 배포 |차단|

개 소리 F1은 기존 기준 모델과 동일해 개선이 확인되지 않았다. 시험 fold5는 이전 작업에서 이미 확인했기 때문에 이번 수치를 새로운 잠금 독립 평가 결과로 표시하지 않는다. 모델은 소리 종류의 좁은 연구 실험이며 감정·의도·원인·발성 시간 경계를 학습한 것이 아니다. 새로 확보한 효과음과 권리/라벨 미검수 자료는 이 학습에 넣지 않았다. 기존 서비스 모델을 교체하지 않는다.

실제 결과물: `artifacts/esc10-augmented-20261104/report.json`, `research-model.json`, `attribution.txt`. 공개 [증거](evidence/RESEARCH_TRAINING_20261104.json)에 결과·출처·해시를 기록했다. 연구용 format/class_names 형식이며 운영 모델 승격 조건을 완화하지 않는다.

```sh
python -m training.augmented_research \
 --source data/acquisition-20261028/esc10 \
 --prepared data/acquisition-20261028/esc10-16k \
 --output artifacts/new-research-run
```

## 추가 원본 수집과 적용

[Red Library: Animals Dogs](https://archive.org/details/Red_Library_Animals_Dogs)의 공식 metadata에서 CC0를 확인하고 MP3 전부31개, 총13333173바이트를 확보했다. 파일별 게시자 MD5/SHA1을 대조하고 SHA256·원래 WAV명·출처를 보존했다. `data/red-dogs-20261104/` 원본은 유지하고, `data/red-dogs-prepared-20261104/`에 각각 앞10초 이내의16kHz 모노 PCM16 사본31개를 만들어 기존34차원 음향 입력기의 유한값 검사를 통과했다. 이는 입력 파이프라인 적용이며 행동 정확도 검증이 아니다. 원본별 처리 이력은 receipt.json에 있다.

[HF 테스트 효과음5개](https://huggingface.co/datasets/petdecoder/pet-decoder-audio-fixtures/tree/1f16896a1692e65f0e2ef5a79e351ed12bff5857)는 모두 위31개 안의 파일과 SHA256가 같다. 신규 고유 효과음은31개이며5개를 다시 더하지 않는다. 특히 dog_growl_play.mp3는 원출처 R01-16-Low Bark and Whine.mp3와 동일하다. 이런 효과음 명칭을 놀이·공격성·연령·견종의 학습 정답으로 쓰지 않는다. 개인 개체/가정은 미상이고 원본 편집·다른 데이터와의 근접 중복 검토가 남아 있다.

```sh
# 공식 metadata를 먼저 로컬 보관하고 크기·라이선스가 맞는 고정 원출처만 받는다.
python -m scripts.acquire_red_dogs \
 --metadata data/research-training-20261104/red-library-metadata.json \
 --output data/red-library-new
```

## 새 전문가 자료와 사용조건 충돌

[Dog play pant](https://zenodo.org/records/18972388)는 개체17마리·놀이30세션, 전문가가 검토한2차 구간 라벨을 제공하는 유력 후보다. README·annotation ZIP·metadata CSV를 실제 확보하고 게시자 MD5를 검증했다. 그러나 API의 CC BY4.0 선언과 내려받은 README의 CC BY-NC4.0 문구가 충돌한다. 이 상태에서 본 상업 프로젝트의 학습에 넣거나 명확히 허용됐다고 표시하지 않는다. 실제 metadata는30세션·17개체이고, 2차 Table파일30개의 구간2636개를 확인했다. 여기에는 Human581개와 Other264개도 있어 전부 개 발성 정답으로 합산하지 않는다. 원본 오디오/영상은 받지 않았다. 공급자 조건 확인을 별도 의존성으로 남긴다. 연구용이라는 이름만으로 상업 개발의 이용 조건이 바뀌지 않는다.

[Biodenoising validation](https://zenodo.org/records/13736465)은 공식 설명에 교육·비상업 제한이 있어 메타데이터만 보관했다. [EmotionalCanines](https://github.com/tmdang1101/EmotionalCanines/tree/6b73c5fce55fc132e97db6a76899f8594a955f59)는 고정 README만 확보했으며 원본 배포/이용 조건을 확인하지 못했다. 소스 설명에 기재된 감정명을 검증된 전문가 정답으로 바꾸지 않는다.

## 국내 연결

기존 AI-Hub59·71878 승인 보고와 도구는 [직전 적용 보고서](DATA_EXPANSION_20261104.md)를 유지한다. 국내 PC 원본은 현재 실행환경에 연결되지 않아 실제 추가 학습에 사용하지 않았다. 신규 [71879 성장·질병 말뭉치](https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71879)는 한국어 보호자 질의의 검색 기반 설명 후보로 등록했다. 데이터 원본/별도 승인/의학적 답변 검토가 필요하며 영상·음향 감정 정답으로 사용하지 않는다. 무관한 등록현황/행정통계나 다른 동물 자료로 행동 학습량을 늘리지 않는다.

## 검증 및 남은 작업

새 학습 테스트는 시험 feature만 바꿔도 fitted weights가 바뀌지 않는지, 추가 feature가 학습 수를 넘어가면 거부하는지, 알려진 원본 겹침이 차단되는지를 검사한다. 수집 테스트는 고정 CC0 원출처·경로/크기/중복 제한을 검사한다. 전체388개 Python 검사와 compile·스킬 무결성 검사를 수행한다. 합성 회귀검사와 실제400음원 학습/31효과음 수집을 구분한다.

다음 순서는 국내 원본 및 식별자 연결, 전문가 데이터의 조건 충돌 해소, 미검수 새 음원의 청취·근접 중복/출처 검토, 추가 가정·기기·잡음 대조군, 이전 시험과 분리된 새 평가셋 잠금이다. 기존 모델 의존성 보안 공지도 별도 미해결이다. 새 학습 가중치의 제품 자동 적용·운영 배포는 수행하지 않았다.
