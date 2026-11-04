# 개 전문 자료 조사와 적용 순서

조사일: 2026-10-19 (Asia/Seoul). 공식 연구·저장소·데이터 카드의 문헌 조사다.
새 가중치 설치, 데이터 다운로드, 실제 개 학습·추론은 이번 조사에서 수행하지 않았다.
기존 PRETRAINED_MODEL_SURVEY.md에는 이미 18개 모델 계열이 조사되어 있었다.
최근 대화에서 조사 범위를 VLM 위주로 설명한 것은 불완전했다. 조사와 실제 적용을
구분해야 하며, 기존 후보 대부분의 PetSense 실행 평가는 여전히 미완료다.

## 후보별 용도와 도입 판단

| 자료 / 공식 출처 | 확인 내용 | PetSense 적용 방향 / 남은 조건 |
|---|---|---|
| [Dog2vec](https://github.com/fispresent/dog2vec) | 개 발성 표현 사전학습 연구, 코드·모델·데이터 안내 | 음향 embedding 후보 1순위. 정확한 가중치 파일·라이선스·실행 환경 확인 전 상업 학습 승인하지 않음 |
| [AVES](https://github.com/earthspecies/aves), [AVEX](https://github.com/earthspecies/avex) | 동물 발성 encoder와 후속 도구 | Dog2vec 비교용 동물 음향 표현. 개 의도 번역기로 취급하지 않음. 개별 가중치 조건 확인 |
| [Wav2Vec2 개 짖음 연구](https://aclanthology.org/2024.lrec-main.1432/) | 사람 음성 표현을 개 짖음 분류에 전이하는 연구 | 논문 실험·라벨·분리 방식을 재현 후보로 지정. 사람 말처럼 개 소리를 번역한다는 증거는 아님 |
| [Phonetic and Lexical Discovery of Canine Vocalization](https://aclanthology.org/2024.findings-emnlp.816/) | 개 발성의 패턴 발견 연구 | 발성 단위와 반복 패턴 연구 참고. 사람 언어와 같은 어휘 의미를 확보했다고 간주하지 않음 |
| [DogSpeak](https://github.com/Lekhak123/DogSpeak-A-Canine-Vocalization-Classification-Dataset), [공식 HF](https://huggingface.co/datasets/ArlingtonCL2/DogSpeak_Dataset) | 156마리·5품종·77,202 발성 시퀀스, 개체·품종·성별 정보 | 음향 표현 연구 후보. CC BY-NC-SA 4.0이므로 상업 학습은 별도 허락 전 보류. 감정 정답 데이터가 아님 |
| [CATVD](https://github.com/Lekhak123/A-Data-driven-Approach-to-the-Longitudinal-Study-of-Canine-Vocal-Pattern-Development) | 연령에 따른 발성 변화 데이터, 개체 정보 | 나이 변화에 강한 모델 평가 후보. DogSpeak와 일부 개체 중복 가능, 전역 ID 검토 필요. 별도 조건 확인 |
| [자동 개 발성 분석 시스템](https://github.com/mkaraaslan-dev/fully-automatic-voice-analysis-system), [논문](https://pmc.ncbi.nlm.nih.gov/articles/PMC11680081/) | 소리 구간과 유형을 분석하는 연구 | 짖음·낑낑거림·하울링 등 목표 라벨과 실제 제공 라벨을 대조할 후보. 제공 코드·원데이터·가중치 권한 별도 확인 |
| [DigiDogs](https://github.com/mshooter/DigiDogs_release) | 합성 학습 기반 단안 개 3D 자세 추정, checkpoint 안내 | 골격 추정 후보. 공식 README CC BY-NC-SA 4.0, 상업 도입 보류. 기존 Python 3.8/CUDA 환경의 이식 비용 있음 |
| [RGBD-Dog](https://github.com/CAMERA-Bath/RGBD-Dog) | RGB-D와 모션캡처를 활용한 개 자세 데이터 | 자세 검증 참고. 데이터 신청·이용 조건 확인, 휴대폰 RGB 입력과 도메인 차이 평가 |
| [DECADE / dogTorch](https://github.com/ehsanik/dogTorch) | 개 시점 영상과 움직임을 연결한 행동 모델링 | 시간적 행동 모델 설계 참고. 코드 MIT와 데이터 권리는 구분; 보호자 시점 영상과 차이 큼 |
| [Pawgaze](https://huggingface.co/datasets/pawgaze/pawgaze) | 개 영상의 행동·상호작용·맥락 문항을 담은 멀티모달 benchmark | VLM 평가 설계 후보. 공개 문항에 관찰과 감정·인과 해석이 섞여 있어 재검수 필요. 이번 페이지에서 라이선스를 확인하지 못함 |
| [InterPet4D](https://interactive-intelligence-lab.github.io/InterPet4D-Homepage/) | 13마리·11품종, 동기화 영상·음성·사람/개 3D 동작 | 영상-소리 동기화 연구 우선 후보. 다량 프레임이 독립 개체 수를 늘리지는 않음. 사이트 템플릿 라이선스를 데이터 라이선스로 해석하지 않음 |
| [DogCentric](https://robotics.ait.kyushu-u.ac.jp/yumi/db/first_dog.html) | 개 시점의 활동 영상 데이터 | 동작 분류 설계 참고. 정확한 배포 조건 확인 및 보호자 촬영 영상으로 외부 평가 |
| [AVSAB 공식 입장문](https://avsab.org/resources/position-statements/) | 근거 기반 행동 관리·보상 기반 훈련 지침 | 검색 기반 설명의 우선 근거. 문서 인용과 대량 복제·학습 권리를 구분 |

음향 기준선 YAMNet/EfficientAT/AST, AP-10K 자세 후보 등은 기존 조사 문서와 함께
비교한다. 개 전문 자료라고 무조건 범용 모델보다 정확하다고 가정하지 않는다.
온라인 자료에서 학습한 모델/데이터의 downstream 평가에는 출처·중복에 의한 누수가
있을 수 있다. 공개 benchmark를 학습에 쓰면 같은 benchmark를 최종 독립 평가로 쓰지 않는다.

## 강형욱 출연 영상의 가치

행동 영상과 사례 이력, 보호자의 설명, 전문가 해석, 개입 전후 반응이 함께 있다는 점은
학습 자료의 강점이다. EBS 공식 보도자료에서도 강형욱 출연 사례를 확인했다.
예: [루샤는 개줄을 싫어해](https://global.ebs.co.kr/board/bbs?boardId=31&boardTypeId=1&cmd=view&no=10&option=&pageNo=616&postId=10002601340&searchCondition=title&searchKeyword=).
이번 확인은 프로그램/사례의 존재에 대한 확인이며 영상을 재생해 행동 라벨을 검증한 것은 아니다.
출연자가 같아도 권리자는 방송사·제작사·채널별로 다를 수 있다.

따라서 사용자의 '효과 있는 자료'라는 판단에 동의한다. 다만 전문가가 방송에서
내린 해석을 모든 개에 적용할 임상 진단 정답으로 그대로 저장해서는 안 된다.
행동 평가는 병력·환경·보호자 면담 등 화면 밖 정보를 포함할 수 있다.

사례 단위로 다음을 분리해 기록하는 설계를 권한다(아직 신규 필드 구현은 아님).

- 출처: 원본 URL, 공식 채널, 회차, 게시일, 시간 구간, 사용 권한과 검토자.
- 직접 관찰: 자세, 거리 변화, 응시 방향, 소리 유형·발성 시점. 가림·편집 여부.
- 전문가 해석: 발언자와 해당 설명 구간, 가설·적용 조건·대안 설명.
- 개입: 자극/보호자 행동/훈련 절차와 직후 관찰된 반응.
- 결과: 후속 관찰 기간·지속 여부. 편집된 성공 장면만으로 인과 효과를 확정하지 않음.
- 검수: 관찰-해석 일치 여부, 독립 검토자의 동의/이견, 보류 사유.

모델이 자막의 정답이나 해설자의 말을 베껴 영상 이해 성능이 높아 보이는 것을 막기 위해
영상만/음성만/둘 모두를 나누어 평가한다. 특히 짖음 분석에는 해설·배경음·효과음·더빙을
기록하고 자연 발성 여부를 확인한다. 같은 개·가정·회차·재편집 클립은 한 split에 묶는다.
한 전문가/프로그램에 편중하지 않고 일반 가정의 정상 행동과 다른 전문가 사례도 포함한다.
교정 지식은 최신 행동학 근거와 교차 검토하며, 현재 AVSAB 보상 기반 훈련 지침을 참고한다.

## 적용 순서와 완료 기준

1. 음향: Dog2vec·AVES와 기존 EfficientAT 기준선의 배포 가중치/권한/입력을 고정.
   통과 조건: 재현 가능한 추론, 짖음·낑낑거림·하울링 라벨 지원 여부 명시.
2. 데이터: 상업 허용 자료 및 직접 동의받은 녹음 우선. DogSpeak·DigiDogs는 별도
   허락 전 상업 학습 제외. 조건 확인 전 자동 registry 승인 금지.
3. 자세: 현재 SmolVLM 정지 자세 평가와 골격 기반 특징 비교. 시간적 행동은 별도 평가.
4. 멀티모달: InterPet4D/Pawgaze의 실제 파일·라벨·조건을 검토하고 독립 평가 설계.
5. 영상 지식: 공식 출처의 사례 카드 후보를 자동 생성하고 사람이 승인한 근거만 검색에 사용.
   강형욱 출연 영상은 우선 후보군에 포함하되 원본별 권한과 관찰/해석 검수 유지.
6. 배포 전: 개체·가정 분리, macro F1/클래스별 recall, 오탐, calibration,
   abstention/coverage, CPU/폰 지연, 배경음·가림·비개체 오류를 측정.

자료 수 자체를 성과 지표로 삼지 않는다. 실제 목적에 맞는 라벨, 권한, 독립 평가에서
개선이 확인된 자료 수를 도입 성과로 기록한다.
