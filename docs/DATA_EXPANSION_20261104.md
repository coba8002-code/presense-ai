# 국내외 개 데이터 조사·연결 — 2026-11-04

이 기록은 11월1일 확보분을 대체하지 않고 후속 상태를 기록한다. 검색된 공급 규모, 이 환경에서 확보한 원본, 검수 및 모델 학습은 별도로 집계한다.

## 국내 자료 적용

[AI-Hub59](https://www.aihub.or.kr/aihubdata/data/view.do?aihubDataSe=data&currMenu=120&dataSetSn=59&topMenu=)의 공식 페이지에서 종·행동·프레임·관절 필드를 재확인했다. 공개 총량은 개와 고양이 합계이므로 개 데이터 확보량으로 계산하지 않는다. `scripts/aihub59_review.py`는 국내 PC의 **압축 해제된 JSON 라벨 폴더**를 읽어 개만 검수 큐로 연결한다. 보호자/검수자 감정 설명을 정답으로 내보내지 않고, 파일 번호를 개체 ID로 바꾸지 않는다. 관절 객체·시각 필드의 존재를 집계하지만 좌표 유효성, 영상 매칭, 시각 단위까지 검증한 것은 아니다. 원본을 읽기만 하며 출력은 새 파일만 허용한다.

```sh
python -m local_pc.pc inventory --input /path/to/aihub59 --output inventory59.json
python -m scripts.aihub59_review --input /path/to/extracted-labels59 --output review59.json
```

[AI-Hub71878](https://www.aihub.or.kr/aihubdata/data/view.do?aihubDataSe=data&currMenu=115&dataSetSn=71878&pageIndex=1)은 공식 페이지상 보행 영상2094건·키포인트 이미지126092건, 14개 부위 및 진료·압력 정보다. 일반 감정 자료로 해석하지 않는다. 공개 페이지의 포맷 설명에 AVI/MP4가 함께 있어 실제 원본을 확인해야 한다. 59와 JSON 스키마가 다르므로 위 어댑터를 재사용하지 않는다. 사용자가 두 자료 이용승인을 보고했으며 이를 다시 요구하지 않는다. 국내 PC 파일은 이 실행환경에 연결되지 않아 새 실자료 검사·학습 완료로 표시하지 않는다.

## 해외 추가 조사

- [Zenodo20571465](https://zenodo.org/records/20571465): 공식 API에서 CC BY4.0 및 963585822바이트 ZIP을 확인했다. 원본 목록2548항목 중 명시적인 dog_bark/growl/grunt train/test 폴더에서 WAV113개를 발견했다. 게시자 폴더명은 미검수 이벤트 라벨이며 감정·개체 정답이 아니다. 실제113개(서로 다른 원본 해시113개)를 확보했고, 기존 원본과 바이트가 같은 파일46개를 확인했다. 나머지67개는 원본 해시 기준 추가분이며 편집·재샘플링 중복과 개체 독립성은 미확인이다. 총 전송량31794974바이트로 멤버 CRC를 검증했다. 110개는 기존 WAV 형식 검사에 통과했고 3개는 미지원/유효성 재검토로 보류했다. 지원 음원의 합산 길이는 약523.26초다. 원본별 상세 결과는 아래 증거 JSON에 기록한다.
- [Speak Like a Dog](https://github.com/suzuki256/dog-dataset/tree/40f28020f774e0fc18c475f676a21f54d7bd892c): README/라이선스 원문 확보. adult/puppy는 음높이에 따른 구분이므로 실제 연령 정답으로 사용하지 않는다. ESC/BarkMeow/UrbanSound 및 혼합 조건 원출처를 재사용한다. 집계1080개를 신규 독립 자료로 더하지 않고 상업 학습에 편입하지 않았다.
- [AV 개체 식별 연구](https://arxiv.org/abs/2610.21011): 실제 영상46개·수동 짖음 이벤트213개의 평가 사례와 화면 밖 발성 처리를 확인했다. 발성 개체가 미확인일 때 보류하는 기존 방향에 참고한다. 원본 배포·라이선스가 확인되지 않아 논문 성능을 제품 성능으로 표시하거나 미디어를 확보했다고 쓰지 않는다.
- [ETH Acoustic Event Dataset](https://data.vision.ee.ethz.ch/cvl/ae_dataset/): 공식 페이지는 dog_barking113개·약9.2분을 소개한다. 별도 GitHub의 CC0 설명만으로 공식 원본 권리를 확정하지 않았다. 혼합 파생본을 받기보다 원출처 조건을 확인하는 후보로 유지한다.
- 기존 DogSpeak/InterPet4D/Pawgaze는 대규모 후보지만 이용 조건·원본 확보 상태는 기존 [DATA_EXPANSION](DATA_EXPANSION.md)을 유지한다. 야생 들개·고양이 자료는 반려견 학습량에 포함하지 않는다.

## 실제 코드 연결

`datasets/registry.json`에 국내2개·해외3개 공급원을 미검수 상태로 등록했다. `scripts/public_dog_zip.py`는 고정 Zenodo URL의 HTTP206/Content-Range/응답 길이를 검증하고 개 폴더만 선택한다. 한 번의 요청 크기, 전체 전송량200MB, 확장량150MB, 실행시간300초를 제한한다. 잘못된 전체 응답을 이어붙이지 않는다. ZIP 멤버 CRC와 각 WAV의 SHA256를 기록하고 기존 BarkMeow/ESC 원본과 바이트 중복을 대조한다. 검증 전 임시 출력은 완성 디렉터리로 공개하지 않는다.

전체 ZIP을 내려받지 않으므로 **전체 archive MD5 검증 완료가 아니다.** 원본 메타데이터와 멤버별 CRC/SHA를 보관하며, 파일 재샘플링/편집 중복·동일개체·원출처 권리는 별도 검토한다. 처음 시작한 전체 다운로드는 부분 요청 지원 확인 후 중단했고 `.partial` 파일은 확보 원본으로 집계하지 않는다.

```sh
python -m scripts.public_dog_zip --output data/dog-zip-new
python -m training.source_routes --registry datasets/registry.json --output artifacts/source-routing-new.json
```

새 자료는 기존 학습 승인·개체 분리·외부 평가 조건을 통과한 학습 manifest가 아니라 **검수 입력**이다. 보호자/전문가 라벨·검수 증거·개체와 가정 ID·중복 연결·음성 주체·시간 정답이 확보되기 전 모델 가중치 갱신과 배포로 진행하지 않는다. 학습은 이번 실행에 포함되지 않았다.

## 검증 및 다음 단계

새 검사5개: 정확한206/길이/범위 강제, seek·캐시, 경로탈출·종 필터, 국내 스키마 미상/링크 차단, 감정·개체 오염 방지. 전체 Python383개 통과. 이 중 실제 국내 원본 검사는 없고 합성 라벨 검증이다. 실제 해외 원본 집계는 [실행 증거](evidence/DATA_EXPANSION_20261104.json)에 둔다.

다음은 실제 원본의 중복·게시자 이벤트 라벨 청취 검토 → 국내PC 라벨/영상/개체 대응표 연결 → 학습용 변환·독립 평가 분할이다. 기존 QA에서 확인한 Transformers/Accelerate 보안 공지는 별도 미해결 상태이며 본 데이터 연결로 해소됐다고 보지 않는다.
