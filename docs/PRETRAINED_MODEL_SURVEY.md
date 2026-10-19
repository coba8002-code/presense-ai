# PetSense AI 사전학습 모델 조사

조사일: 2026-10-17. 대상: 개·고양이 소리, 동물 자세, 영상 관찰.

## 결론과 조사 범위

우선 비교할 조합은 YAMNet(실시간 소리 탐지), EfficientAT(경량 PyTorch),
AST(서버 기준 모델), RTMPose AP-10K(자세), Qwen2.5-VL-7B(영상 관찰)다.
동물 전용 표현 학습은 AVES와 Dog2vec을 별도 비교한다.
이는 문헌·배포 자료에 근거한 우선순위이며 PetSense에서 측정한 성능 순위가 아니다.

GitHub, Hugging Face, TensorFlow Hub/Kaggle Models, Zenodo, ModelScope,
OpenMMLab 모델 저장소, ISCA/ACL 논문과 Nature 및 연구기관 원문을 조사했다.
공식 저장소가 안내하는 Google Cloud Storage, Google Drive, OneDrive,
Dropbox 배포 경로도 확인했다. 모든 인터넷 자료를 빠짐없이 조사했다는 의미는 아니다.
가중치 파일의 존재/배포 안내를 확인했으며, 바이너리 다운로드·해시 검사·실제 추론은
이번 조사에서 실행하지 않았다. 링크 존재와 현재 다운로드 성공은 다르다.

## 검증 수준

- 공개 벤치마크: 저자 논문/공식 평가 자료가 있는 모델. 독립 재현 완료를 뜻하지 않는다.
- 공식 배포: 모델과 추론 예제가 제공되지만 여기서 비교 가능한 성능 수치를 확인하지 못한 경우.
- 탐색 후보: 커뮤니티 배포 또는 학습 코드만 확인. 제품 성능 근거로 사용하지 않는다.
- 모든 후보의 PetSense 개체 분리 평가, 실제 기기 지연, 보정 검증은 미실행이다.

아래 수치에서 AudioSet mAP, 자세 AP, 분류 정확도는 서로 다른 지표다.
AudioSet 전체 mAP를 개/고양이 정확도 또는 감정 인식 정확도로 표시하지 않는다.

## 18개 모델 계열 비교

| 후보 및 원문 | 공개 가중치/획득 경로 | 확인한 근거와 용도 | 라이선스 및 도입 판단 |
|---|---|---|---|
| [YAMNet](https://www.tensorflow.org/hub/tutorials/yamnet) | [Google Kaggle TFLite v1](https://www.kaggle.com/models/google/yamnet/tfLite/classification-tflite/1?tfhub-redirect=true), TF Hub | 공식 배포. AudioSet 521 소리 이벤트, 16 kHz mono. 고양이 소리 예제 제공. 감정 모델 아님 | 해당 TFLite 배포 Apache-2.0. **실시간 기준선 1순위** |
| [EfficientAT](https://github.com/fschmid56/EfficientAT) | [GitHub Releases](https://github.com/fschmid56/EfficientAT/releases), `mn04_as`, `dymn10_as` 등 | 공식 표: mn04_as 0.983M 파라미터/mAP 43.2%, dymn10_as 10.57M/47.7%. ICASSP 연구와 모델별 복잡도 공개 | 저장소 MIT. 정확한 가중치 적용 조건 보존 후 **경량 PyTorch 비교 1순위** |
| [PANNs](https://github.com/qiuqiangkong/audioset_tagging_cnn) | [Zenodo 3987831](https://zenodo.org/records/3987831), `Cnn14_mAP=0.431.pth` | AudioSet Cnn14 mAP .431 배포 모델. 분류/임베딩 기준선 | 코드 MIT. Zenodo 추출 화면에서 가중치 라이선스 본문이 확인되지 않아 별도 확인. 서버 비교 후보 |
| [AST](https://github.com/YuanGongND/ast) | [MIT HF 모델](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593), safetensors; 원저자 Dropbox/OneDrive 경로 | 저자 README: weight-averaged 단일 모델 AudioSet mAP .459. 16 kHz. HF 카드 86.6M 파라미터 | HF BSD-3-Clause 표기. 카드는 HF 팀 작성이라는 고지 있음. **서버 기준선 1순위** |
| [BEATs](https://github.com/microsoft/unilm/blob/master/beats/README.md) | 공식 OneDrive 체크포인트: iter1~3+, 사전학습/AudioSet fine-tuned 구분 | [Microsoft 논문 소개](https://www.microsoft.com/en-us/research/publication/beats-audio-pre-training-with-acoustic-tokenizers/)에 AudioSet-2M 50.6% mAP/ESC-50 98.1%. 대표 연구 결과이며 모든 체크포인트의 성능이 아님 | UniLM 코드 MIT. 선택 가중치 조건 확인 필요. 16 kHz 표현 학습/정밀 비교 |
| [PaSST](https://github.com/kkoutini/PaSST) | 공식 README pretrained inference/embedding loader | Patchout 논문 및 학습/추론 코드. 이 조사에서는 특정 체크포인트 수치를 확정하지 않음 | 저장소 Apache-2.0. 가중치별 확인 후 추가 비교 |
| [HTS-AT](https://github.com/RetroCirce/HTS-Audio-Transformer) | 공식 Google Drive, `HTSAT_AudioSet_Saved_1.ckpt` | ICASSP 2022. 약 30M 파라미터, AudioSet 분류와 DESED 위치 탐지 평가 안내 | 코드 MIT. 가중치별 조건 확인. 소리 발생 구간 탐지 연구용 비교 |
| [CLAP](https://github.com/LAION-AI/CLAP) | [laion/clap-htsat-unfused](https://huggingface.co/laion/clap-htsat-unfused), fused 변형 | ICASSP 2023. 소리-텍스트 임베딩/zero-shot 분류. 문장 유사도는 행동의 확정 근거가 아님 | 코드 CC0-1.0, 해당 HF 카드 Apache-2.0. 프롬프트 민감도 평가 후 보조 활용 |
| [AVES](https://github.com/earthspecies/aves) | 공식 GCS `aves-base-bio.pt`, 모델별 TorchAudio/ONNX 및 config | 동물 발성 표현 모델. BEANS 평가 공개. bio 기준 표의 평균 .643은 여러 과제 지표 평균으로 정확도가 아님 | 코드 MIT, 가중치 조건 별도 보존. **동물 전용 전이학습 비교 우선** |
| [Perch / Perch v2](https://github.com/google-research/perch) | [Google Kaggle](https://www.kaggle.com/models/google/bird-vocalization-classifier) | 새 중심 종 분류/임베딩, 생물음향 전이학습 논문. 개·고양이 행동 검증을 뜻하지 않음 | 코드 Apache-2.0, 선택 모델 버전의 조건 추가 확인. 반려동물 직접 분류보다 임베딩 비교 후보 |
| [Dog2vec](https://github.com/fispresent/dog2vec) | [Zenodo v1](https://zenodo.org/records/15494042), `dog2vec_130k_9.pt`, 표시 크기 1.1 GB | [Interspeech 2025 논문](https://www.isca-archive.org/interspeech_2025/li25o_interspeech.pdf). 개 짖음 표현, 종류/이벤트 탐지. 저자 보고 상대 8.2% 개선은 정확도 8.2%p가 아님 | 저장소/Zenodo 읽은 화면에서 상업 조건 확정 못함. **권한 검토 후 개 전용 비교** |
| [dima806 cat/dog sounds](https://huggingface.co/dima806/cat_dog_sounds_classification) | HF safetensors, 94.6M 파라미터 | 커뮤니티 Wav2Vec2 fine-tune. [학습 notebook](https://www.kaggle.com/code/dima806/cats-dogs-sounds-classifier) 안내. 카드에서 개체 분리/외부 검증 수치 확인 못함 | HF Apache-2.0 표기만으로 데이터 권한까지 확정하지 않음. 탐색 후보 |
| [Meow-Net](https://github.com/Yfyangd/meow) | 학습 코드 확인; 검토한 README/루트에서 사전학습 체크포인트 확인 못함 | CatMeows의 식사 대기/격리/브러싱 맥락. 학습 맥락을 감정의 정답으로 취급하지 않음 | 코드 MIT, 기반 데이터 비상업 조건. 상업 도입 보류 |
| [MeowFM](https://github.com/zouaynib/MeowFM) | 데이터 도구/계획/테스트 안내. 검토한 README/루트에서 가중치와 수치 결과 확인 못함 | README의 foundation model 주장만으로 검증된 모델로 분류하지 않음 | CatMeows CC-BY라는 README 서술과 원본 이용 조건 충돌. 상업 도입 보류 |
| [NatureLM-audio](https://huggingface.co/EarthSpeciesProject/NatureLM-audio) | HF 공개 가중치, 공식 GitHub | ICLR 2025, BEANS-Zero. 소리 설명/종 분류. 카드에 call-type/lifestage는 새에서만 검증, 정확한 시간 탐지 미지원 명시 | **가중치 CC-BY-NC-SA-4.0. 상업 경로 제외**, 별도 허가 없이는 도입하지 않음 |
| [RTMPose AP-10K](https://github.com/open-mmlab/mmpose/blob/main/configs/animal_2d_keypoint/rtmpose/ap10k/rtmpose_ap10k.yml) | 공식 OpenMMLab `.pth` 링크가 모델 메타데이터에 있음 | `rtmpose-m_8xb64-210e_ap10k-256x256`: AP .722, AP50 .939. 동물 2D 키포인트, 감정 모델 아님 | MMPose 코드와 AP-10K/추가 pretraining 자료의 조건 각각 검토. **자세 후보 1순위** |
| [SuperAnimal-Quadruped](https://huggingface.co/mwmathis/DeepLabCutModelZoo-SuperAnimal-Quadruped) | HF/DeepLabCut Model Zoo | [Nature Communications 2024](https://www.nature.com/articles/s41467-024-48792-2). 동물 자세/전이 평가 공개 | **해당 가중치는 Modified MIT: academic, non-commercial only**. 일반 MIT로 취급 금지. 상업 라이선스 별도 |
| [Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) | HF, [공식 ModelScope](https://modelscope.cn/models/Qwen/Qwen2.5-VL-7B-Instruct) | 카드의 MMMU val 58.6, MVBench 69.6 등 일반 영상 평가. 반려동물 행동 성능 수치는 아님 | 해당 7B 카드 Apache-2.0. **자체 호스팅 VLM 관찰 후보**; 다른 크기/버전으로 조건 일반화 금지 |

## 함께 찾은 자료와 제외 사유

- [AVEX](https://github.com/earthspecies/avex): AVES 후속 도구이며 여러 사전학습 모델/분류 head를 불러오는 라이브러리다. 모델 한 개로 집계하지 않는다. Python 3.11~3.13 지원 안내가 있으며 현재 Python 3.12 환경의 통합 후보다. 래퍼의 MIT가 각 모델의 라이선스를 대체하지 않는다.
- [Barkopedia](https://github.com/UTA-ACL2/Barkopedia): IJCAI 2025 개 발성 챌린지/데이터·평가 경로다. 이 홈페이지 자체를 배포된 분류 모델로 표시하지 않는다. YouTube/Reddit 원본 권한과 개체 분리 평가가 필요하다.
- [CatMeows 원본](https://zenodo.org/records/4008297): 이용 조건에 과학 연구/비상업 용도가 명시돼 있다. 다른 저장소의 MIT/CC-BY 표기를 대신 근거로 삼지 않는다.
- [Suno Bark](https://huggingface.co/suno/bark)는 텍스트에서 소리를 생성하는 모델이다. 이름이 Bark여도 개 짖음 해석 모델이 아니다.
- 사람 음성 감정 모델은 반려동물 감정의 검증된 모델로 취급하지 않는다. 사진의 개/고양이 구분 모델도 오디오 모델과 분리한다.

## PetSense 도입 작업지시

1. YAMNet 공식 TFLite v1과 EfficientAT 경량 모델, AST HF 모델의 정확한 revision/파일/라이선스/해시를 고정한다. 이번 조사는 승인 상태를 변경하지 않는다.
2. 기존 `PETSENSE_AUDIO_MODEL`은 자체 NumPy JSON 형식만 받는다. 외부 체크포인트를 그대로 넣지 말고 별도의 추론 어댑터/클래스 매핑/전처리 계약을 구현한다.
3. 16 kHz 1초 청크와 모델별 입력 창을 맞춘다. 32/48 kHz 모델에 단순 리샘플링해도 원래 잃은 고주파 정보는 돌아오지 않는다. 필요하면 캡처 프로토콜을 변경하고 품질 차이를 측정한다.
4. 스트림의 누락 청크와 sequence gap을 처리한다. 현재 브라우저는 무음과 밀린 청크를 버리므로 받은 청크를 무조건 이어 붙이면 시간축이 틀어진다. 문맥 창이 필요한 모델은 gap reset 또는 시간 보존 버퍼가 필요하다.
5. 초기 출력은 짖음/야옹/으르렁 등 모델 라벨에 실제 존재하는 소리 사건으로 제한한다. 원본 class map을 읽어 선택하며, 감정 라벨을 임의로 덧붙이지 않는다. 여러 소리가 동시에 존재하는 multi-label 출력도 유지한다.
6. 사용 권한이 확보된 실제 개·고양이 녹음으로 학습/검증/테스트를 개체 및 가정/세션 단위로 분리한다. TV 재생음, 사람 말, 무음, 생활 잡음, 멀리 있는 동물, 종 혼합을 음성/음성 아님 평가에 포함한다.
7. 모델마다 정확도, macro F1, 클래스별 precision/recall, confusion matrix, calibration, abstention 및 coverage를 보고한다. 탐지는 이벤트 recall와 시간당 오탐도 함께 측정한다. 개체 단위 bootstrap 신뢰구간을 기록한다.
8. latency는 캡처 창+업로드+전처리+추론+응답 전체 p50/p95와 모델 단독 시간을 구분한다. CPU/모바일 RAM, 모델 크기, 배터리, 동시 요청 부하도 측정한다. 목표값은 실행 전에 제품 요구로 고정하고 테스트 결과에 맞춰 낮추지 않는다.
9. RTMPose는 동물 박스 검출 단계와 함께 평가하고, 가림/다중 동물/귀·꼬리 keypoint 지원 범위를 확인한다. Qwen은 이미지 관찰만 구조화하고 근거 없는 행동 단정은 보류한다.
10. 권한이 정리된 AVES/Dog2vec의 frozen embedding + 작은 분류 head를 먼저 비교한다. 이후에만 fine-tuning을 결정한다. 새 모델이 현재 기준선을 이기지 못하면 그대로 기록한다.

이번 산출물은 후보 조사와 선택 근거다. 새 가중치 설치·실제 동물 성능 검증·학습·배포 완료를 뜻하지 않는다.
