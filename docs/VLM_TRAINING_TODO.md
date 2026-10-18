# VLM 활용·학습 실행 TODO

> 현재 제품 범위: **개 전용 MVP**. 고양이 학습·분석은 후속 단계로 보류합니다.

현재 작업은 검수용 관찰 데이터 흐름이다. VLM이 만든 문장을 학습 정답으로 자동 승인하지 않는다. 기존 URL 분석은 knowledge.worker, 이미지 관찰은 /v1/vision/observe에 있다. 실제 API 연결 및 실제 영상 정확도 평가 전이다.

| 순서 | 작업 | 완료 기준 | 상태 |
|---|---|---|---|
| VLM-01 | 관찰 후보 내보내기 | 출처·시각·모델·내용 해시 보존, 가설/발언 제외 | 구현 |
| VLM-02 | 검수 입력 계약 | 행동 라벨, 동물·세션 ID, 검수자와 근거 필수 | 구현 |
| VLM-03 | 학습 준비 검증 | 권한 재확인, 변경된 관찰 거부, 개체/영상/세션 분리 | 주석 검증 구현 |
| VLM-04 | 허용된 로컬 영상 연결 | 파일 해시·동일 파일 중복·실제 디코딩·초 단위 구간 검사 | 구현; 유사 영상·프레임 정렬 후속 |
| VLM-05 | 검수 UI | 로컬 영상 구간 재생, 라벨 승인·취소, 검수 JSON 출력 | 로컬 화면 구현; 공동 저장·감사 인증 후속 |
| VLM-06 | 실제 VLM 평가 | API 인증 또는 로컬 모델 확보 후 전문가 라벨과 비교 | 외부 전제 대기 |
| VLM-07 | 사전학습 기준선 | AST/자세 모델의 고정 버전 설치·실제 추론 | 대기 |
| VLM-08 | 행동 전이학습 | 음성/영상/융합 비교, 개체 분리 F1·보정·유보 평가 | 데이터 준비 후 |
| VLM-09 | 실시간 영상 | 이벤트 구간 추출, 누락 프레임 처리, 비용·지연 평가 | 대기 |

## 후보 생성

```bash
python -m training.video_review --db data/knowledge.sqlite3 \
  --config config/knowledge.local.json > data/video-proposals.json
```

외부 호출 없이 현재 로컬 지식 DB를 읽는다. 공개 메타데이터가 24시간 이내이며 보존기간·현재 이용 권한이 유효한 관찰만 출력한다. 가설, 전문가 발언, 종을 확인하지 못한 결과, 길이가 없는 구간은 제외한다. 모든 후보는 미검수이며 자동 행동 라벨을 붙이지 않는다. 낮은 VLM 확신도도 검수자가 판단할 수 있도록 원래 값으로 보존한다.

## 검수 파일

각 proposal_id를 확인한 검수자가 아래 형식의 객체를 배열로 저장한다. 리뷰 파일은 신뢰하는 운영자가 관리하는 입력이며 이 CLI는 검수자의 실제 자격을 인증하지 않는다. 검수 UI·서명·역할 인증은 후속 작업이다.

```json
{
  "proposal_id": "내보내기 결과의 실제 64자리 해시",
  "decision": "approved",
  "label": "walking",
  "animal_id": "전역적으로 동일 동물을 식별하는 ID",
  "recording_group": "촬영 세션 ID",
  "dataset": "승인된 registry 항목 이름",
  "split": "train",
  "reviewer": "검수자 ID",
  "review_evidence": "검수 기록 위치",
  "reviewed_at": 1792195200
}
```

reviewed_at은 실제 검수 UTC Unix timestamp이며 분석 이후·현재 이전이어야 한다. 예제 값은 실제 검수 기록이 아니다. 라벨은 walking/running/sitting/standing/lying/grooming/eating/drinking/approaching/retreating이다. 행동 정의: 걷기/달리기는 보행, sitting은 뒷부분을 바닥에 댄 앉은 자세, standing은 네 발로 지지하는 정지 자세, lying은 몸통을 바닥에 댄 자세다. grooming은 신체를 핥거나 손질하는 행동, eating/drinking은 실제 섭취 동작, approaching/retreating은 확인 가능한 대상과의 거리가 감소/증가하는 행동이다. 모호하거나 다수 동물 중 개체를 특정하지 못한 구간은 승인하지 않는다. 감정·질병·교정 성공 여부는 이 라벨 계약에 포함하지 않는다.

```bash
python -m training.video_review --db data/knowledge.sqlite3 \
  --config config/knowledge.local.json --reviews data/video-reviews.json \
  --registry datasets/registry.json > data/video-annotations.json
```

registry의 기존 상업적 학습 승인 필드와 함께 `video_channels`에 실제 허가된 채널 ID 배열을 명시해야 한다. 유효한 지식 저장 권한만으로 학습 권한을 대신하지 않는다. 원본 내용·모델·분석시각 변경 또는 권한 철회 시 기존 후보를 다시 검수한다.

최소 5개 동물과 2개 이상의 종/행동 조합, 각 train/validation/test 분할의 동일한 라벨 범위를 요구한다. 동일 동물·촬영 세션·원본 영상이 서로 다른 분할에 들어가면 실패한다. 한 원본 영상에 서로 다른 동물이 나와도 원본 단위로 분할한다. 다른 URL의 동일 영상 탐지는 로컬 미디어 연결 단계에서 추가한다.

통과 결과는 `annotations_validated_media_pending`, `training_ready=false`이다. 로컬 영상 검증이나 모델 학습을 수행한 결과가 아니다. 현재 오디오 학습 큐에 이 JSON을 넣지 않는다. 내보낸 파일은 자동 삭제되지 않으므로 운영자가 보존·철회 시 삭제를 관리하고, 사용 전에 현재 DB와 registry로 재검증해야 한다.

로컬 영상 검증 실행: [VIDEO_MEDIA.md](VIDEO_MEDIA.md). 성공해도 모델 학습 완료 상태로 바꾸지 않는다.

브라우저 검수 화면: [REVIEW_UI.md](REVIEW_UI.md). 기본 주소는 `/review`이며 서버 업로드 없이 로컬 파일을 사용한다.
