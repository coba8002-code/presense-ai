# 개 전문 데이터 확보와 다음 평가 · 2026-11-01

## 이번 실행 결과

후속 [음원 중복 감사](AUDIO_DUPLICATE_AUDIT.md)에서 새로 확보한 BarkMeow46개 중40개와 ESC 사이에41개의 유사 구간 후보가 발견됐다. 파일 확보량을 독립 신규 학습자료 수로 계산하지 않는다. 라벨 충돌·원출처 검토가 남아 있으며 모든 학습 승인 상태는 그대로 미승인이다.

검색 결과의 규모와 내려받은 파일 수는 다르다. 원본 수집·권리 확인·라벨 검토·학습·독립 평가를 따로 기록한다. 실제 증거는 [해시/파일 목록](evidence/DATA_EXPANSION_20261101.json), 후속 작업은 [정본 TODO](../tasks/todo.md)에 있다.

| 실제 확보 | 검사 결과 | 적용 범위 |
|---|---|---|
| BarkMeowDB v0.2 공식 원본 31,661,044 bytes | 게시자 MD5 및 고정 SHA256 확인. 개 WAV 46개, 서로 다른 파일 해시 46개, 총292.811초. 모두16kHz float32 | 개 음원만 추출. 발성 종류/경계 검토 큐46개. 원본 archive에는 고양이도 있으나 학습·추출 대상에서 제외 |
| Dog Pain Database v2 XLSX 251,320 bytes | 게시자 MD5 및 SHA256 확인. 첫 시트662행(헤더 포함), 비어있지 않은 서로 다른 Dog ID184개, 관찰번호가 있는 행594개 | 개체·관찰·설문을 구분하는 평가 설계 자료. 논문 소개의200마리와 실제 시트 계수는 다르며 빈칸/반복행을 임의 보정하지 않음. 원본영상0개 |
| Hugging Face 공식 메타데이터/카드4종, Zenodo 원본 메타데이터2종, BEANS README | 버전/해시와 로컬 보관 증거 | 자료 공급·권리·모달리티 조사. 파일 목록 확보를 원본 음원/영상 확보로 계산하지 않음 |

두 새 원본은 공식 기록상 CC BY4.0. 출처표시를 유지한다. BarkMeow 파일명은 **녹음 번호**이며 개체 ID가 아니다. 가정/기기/발성 개체는 미상이다. 동일 해시가 없다는 것만으로 편집/재샘플링된 중복이나 기존 ESC/사전학습 자료와의 중복이 없다고 주장하지 않는다. 새 자료로 학습하거나 배포한 모델은 없다.

## 1. 개체·가정·기기별 자료

| 원본 출처 | 실제 확인·현재 상태 | 다음 연결 |
|---|---|---|
| [AI-Hub59](https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=59), [71878](https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71878) | 사용자 이용승인 있음. 국내PC 원본이 이 환경에 연결되지 않음 | 국내PC의 실제 경로/무결성 보고서로 기존 수집 검사 실행. 개 라벨만 사용, 개체/가정 필드 실제 확인 |
| [DogSpeak](https://huggingface.co/datasets/ArlingtonCL2/DogSpeak_Dataset) | 공식 카드·파일목록 확보. 카드 규모77,202 bark sequences/156개체/5견종, CC BY-NC-SA4.0 | 상업 서비스 학습 사용조건 해결 필요. 원본 음원 미확보. 분할 디렉터리 dog_7a/b를 서로 다른 개로 취급하지 않음 |
| [CATVD](https://huggingface.co/datasets/ArlingtonCL2/Canine-Age-Transition-Vocalization-Dataset) | DogSpeak 공식 카드에 나이·발성 단위·시간 정렬 자료 및 개체 중복 경고 | 별도 원본/조건 검사 필요. DogSpeak와 합칠 때 개체 중복 먼저 확인 |
| [Dog Pain Database](https://zenodo.org/records/15304081) | 표 원본 확보, 임상 관찰·설문·개체 필드 존재 | 일반 가정/건강한 개로의 전이와 전문가 평가 범위 제한. 표의 진료정보를 제품 진단 규칙으로 전환하지 않음 |

견종뿐 아니라 개체, 촬영자/가정, 원본, 연령, 형태, 기기, 거리, 잡음, 보이는 정도가 필요하다. 미상 필드는 null로 유지하며 기록 번호를 개체/가정 ID로 대체하지 않는다.

## 2. 동기화된 영상·음성, 구간·잡음 라벨

| 출처 | 확인 | 판단 |
|---|---|---|
| [InterPet4D](https://huggingface.co/datasets/ohicarip/interpet4d) | 고정revision7835a62bbe1ca3a37cb9957186700b1eb6e40c44 카드·목록 확보. 카드상13개/113세션/227클립, 음성·동작·캡션. CC BY-NC4.0 | 유력한 동기화 후보이나 상업 활용 조건 미충족. 공개 파일목록에 실제 RGB 영상이 있는지도 모달리티별 별도 확인해야 함 |
| [Canine Emotions AV](https://data.mendeley.com/datasets/5g5hg9hrkv/1) | 소개상127개 녹화, CC BY-NC-ND4.0. 감정은 군집 알고리즘으로 부여 | 전문가 감정 정답 아님. 상업 학습 미편입. 직접 파일 접근403으로 원본 미확보 |
| [BarkMeowDB](https://zenodo.org/records/3563990) | 실제 개 음원46개 확보 | 음성 단독 자료. 영상/발성 주체/시작끝 정답을 만들어내지 않음 |
| [BEANS](https://github.com/earthspecies/beans) | 공식 README 확보. 다양한 동물 소리 벤치마크 | 개 하위자료 원저작권/개체/원본 분할 별도 확인. BEANS 코드 라이선스를 음원 라이선스로 간주하지 않음 |
| [AudioSet dog ontology](https://research.google.com/audioset/ontology/dog_1.html) | 짖음/하울링 등 라벨 체계 참고 | 유튜브 ID/라벨은 실제 미디어나 재사용 허락이 아님. 원본영상 미확보 |

기존 AV PTS 정렬 경로와 연결할 때 파일 내 시간축, 음성 주체, 이벤트 경계, 배경 TV/사람/다른 개를 따로 라벨링한다. 이번 확보분에는 검증된 AV 이벤트 정답이 없다.

## 3. 관찰·보호자 보고·전문가 해석

| 출처 | 활용과 한계 |
|---|---|
| [얼굴 랜드마크·수동 ethogram](https://data.mendeley.com/datasets/swk97wxzzg/3) | CC BY4.0, 불꽃놀이/대조 상황의 수동 관찰 및 좌표 자료. 공식 페이지 확인; 직접 다운로드403. 파일 미확보이며 우회하지 않음 |
| [Pawgaze](https://huggingface.co/datasets/pawgaze/pawgaze) | 공식 카드·목록 확보. 카드상7,120 MCQ/923 curated samples. 영상은 유튜브 링크; 명시 라이선스 확인 못 함. 질문의 ground_truth라는 이름만으로 전문가 인증/감정 정답이 되지 않음 |
| [AVSAB](https://avsab.org/resources/position-statements/) | 보상 기반 훈련 권고의 출처 링크. 개별 클립의 원인·감정 라벨이나 우리 모델 성능 증거가 아님 |
| [Dogs Trust body language](https://www.dogstrust.org.uk/dog-advice/understanding-your-dog/body-language), [Battersea](https://www.battersea.org.uk/pet-advice/dog-advice/understanding-your-dogs-body-language) | 몸 전체/환경/개체 차이 관찰 지침 참고. 본문·영상을 대량 학습했다고 기록하지 않음 |
| 강형욱/보듬·EBS 및 기존 국내외 영상 후보 | 기존 공식 링크/권리/분석 파이프라인을 유지. 새 원본영상 학습0. 방송 편집·내레이션을 실시간 동기 관찰이나 확정 원인으로 치환하지 않음 |

새 음원 검토 큐는 사건 구간·발성 종류·리뷰어를 빈칸으로 남긴다. 자동 모델 점수를 전문가 라벨로 복사하지 않는다. 임상 검사나 통증 유발 절차를 사용자에게 수행하도록 권하지 않는다.

## 4. 독립 평가와 자세 자료

| 후보 | 상태 |
|---|---|
| [Movement Sensor Dataset](https://data.mendeley.com/datasets/vxhx934tbn/4) | 공식 논문상45마리/7행동, 목줄·하네스 센서. 스마트폰 영상 모델 정답과 동일하지 않음. 원본 미확보 |
| 기존 AP-10K | 기존 확보 자료 재사용. 사진별 권리/개체/분할 검증은 별도이며 신규 확보량으로 중복 계산하지 않음 |
| [DigiDogs](https://github.com/mshooter/DigiDogs_release), [RGBD-Dog](https://arxiv.org/abs/2004.07788) | 자세 후보. 합성/실제 구분 및 원본 이용조건 확인 후 사용 |
| [B-DoPED](https://huggingface.co/datasets/1Konny/B-DoPED) | 고정 카드·파일목록 확보. research-only 합성 자세 자료; 실제 개 행동 평가 대체 불가 |

이미 구현된 `evaluation/video_contract.py`와 `evaluation/event_evaluation.py`의 개체·가정·원본 분리/독립리뷰 검사를 완화하지 않는다. 새 음원은 분할 가능한 개체ID·생활 잡음 대조군·시간 정답이 없어 생산 평가셋에 미편입이다. 현재 모델의 실제 개선률은 미측정이다.

## 재현과 전달

### 실제 적용된 이용목적 분리

`datasets/registry.json`에 DogSpeak/InterPet4D/BarkMeow/Dog Pain/Pawgaze/B-DoPED/Canine Emotions AV의 출처·고정 버전·조건·상태를 등록했다. `commercial_candidate`는 상업 이용조건 후보일 뿐 라벨/개체/권리 승인 완료가 아니다. `research_review`는 연구 목적의 허용 여부를 검토할 대기열이다. 기업의 제품개발 연구는 비상업 사용으로 자동 인정되지 않는다. `permission_required`는 조건 확인/허가가 필요한 자료다.

`training.data.approve_dataset`은 연구/허가대기 lane과 명시된 NC/ND/research-only 조건을 상업 학습에서 거부한다. 단순히 training_allowed/commercial_allowed를 true로 바꾸어도 이를 통과하지 않는다. 별도 사용권을 확보하면 운영자가 증빙과 실제 적용 라이선스·lane을 함께 검토해야 하며, 기존 승인/정답/분할 검사도 유지된다. 이 분류기는 법률 검증이나 모든 자유형 라이선스 문장의 완전한 해석기가 아니다.

```sh
python -m training.source_routes --registry datasets/registry.json --output artifacts/source-routing-new.json
```

명령은 원본/정책을 변경하지 않고 신규 보고서와 미발송 이용허가 요청 목록을 생성한다. 과거 고양이 자료는 현재 dog-only 요청에서 제외한다. 연구용 학습기 가동/가중치 승격/메일 발송/새 미디어 다운로드는 수행하지 않는다. 신규 학습0 상태는 그대로다.

```sh
python -m scripts.research_acquisition --output data/verified-public-expansion
# 이미 받은 고정 원본을 재검사할 때
python -m scripts.research_acquisition --cached data/research-expansion-20261101 --output data/verified-public-expansion-new
python -m unittest tests.test_research_acquisition
```

고정 공식 URL/크기/SHA256를 검사하고 새 출력 폴더만 생성한다. tar 경로탈출·링크·중복파일·용량초과·잘린 WAV·비유한 float를 거부한다. 원본은 data/에 보관하며 GitHub에는 코드·감사 요약만 올린다. 로컬 클라우드 경로는 국내PC 다운로드 완료를 뜻하지 않는다. 다운로드 중 실패한 폴더는 완료 inventory가 없으므로 확보완료로 세지 않는다.
