# 승인된 개 영상과 검수 주석 연결

현재 개 전용 MVP의 VLM-04 단계다. `training.video_media`는 기존 검수 파일을 현재 DB·권한으로 다시 검증하고, 이미 확보한 로컬 영상을 연결한다. 인터넷 영상 다운로드, API 호출, 모델 학습은 수행하지 않는다.

## 필요한 입력

- 현재 knowledge DB와 채널 정책 설정
- [VLM 검수 파일](VLM_TRAINING_TODO.md) 및 승인된 dataset registry
- registry 항목의 `media_acquisition_allowed: true` — 기존 학습·상업 이용 승인 및 video_channels와 별개로 요구
- 운영자가 허가된 경로로 확보한 로컬 MP4/MOV/MKV/AVI 파일
- FFmpeg와 ffprobe: Debian/Ubuntu의 `ffmpeg` 패키지. CI에도 설치한다. 버전은 OS 패키지에 따르며 모델 성능 재현 시 별도로 기록해야 한다.

bindings.json은 원본 영상별 객체 배열이다. 다음은 형식 안내이며 실제 권한·검수 또는 해시 값이 아니다.

```json
[
  {
    "source_id": "abcdefghijk",
    "path": "dog-session-01.mp4",
    "sha256": "파일 전체의 실제 64자리 SHA-256",
    "source_start_seconds": 10.0,
    "acquisition_evidence": "파일 제공 계약 또는 확보 기록",
    "alignment_reviewer": "검수자 ID",
    "alignment_evidence": "원본 10초와 로컬 0초가 일치함을 확인한 기록",
    "alignment_reviewed_at": 1792195200
  }
]
```

path는 media-root 아래의 상대 경로다. URL, 절대 경로, 상위 경로 이동, 루트 밖으로 나가는 심볼릭 링크는 차단한다. SHA-256은 `sha256sum 파일명` 등으로 계산한다. 하나의 원본 영상에는 하나의 로컬 파일만 연결한다. 해당 원본의 검수된 모든 구간이 그 파일에 들어 있어야 한다.

원본 영상의 10초부터 잘라낸 파일이라면 source_start_seconds는 10이다. 원본 [12,14)초 주석은 로컬 [2,4)초로 변환된다. 배속 변경, 내부 장면 삭제·순서 변경 등 선형 시간 오프셋으로 표현할 수 없는 편집본은 입력하지 않는다. 시작 PTS가 0이 아닌 파일도 차단한다. 원본과 같은 영상인지, 오프셋이 정확한지는 검수자가 확인해야 한다. 자동 검사는 그 확인을 대체하지 않는다.

## 실행

```bash
python -m training.video_media \
  --db data/knowledge.sqlite3 \
  --config config/knowledge.local.json \
  --reviews data/video-reviews.json \
  --registry datasets/registry.json \
  --bindings data/video-bindings.json \
  --media-root data/approved-videos > data/video-media-receipt.json
```

## 검사 범위

1. 현재 권한, 개체·촬영 세션·원본 영상 분할, 주석 변경 여부를 기존 검수 검증기로 재확인한다.
2. 파일당 최대 128 MiB, 한 번에 20개·총 512 MiB까지 임시 스냅샷을 만든다. 원본은 수정하지 않고 임시 복사본은 종료 시 삭제한다.
3. 스냅샷 SHA-256이 운영자가 제출한 해시와 일치해야 한다. 서로 다른 원본 ID에 같은 파일 내용이 연결되면 분할과 관계없이 거부한다.
4. ffprobe로 첫 영상 트랙의 메타데이터를 읽고 FFmpeg로 전체 트랙을 디코딩한다. 로컬 파일 프로토콜과 제한된 컨테이너만 허용한다. 메타데이터 조회는 15초, 디코딩은 파일당 60초 제한이다.
5. 최대 30분, 최대 1920×1080, 평균 60fps까지 허용한다. 양수 길이와 프레임 수가 필요하다. 주석이 로컬 영상 범위를 벗어나거나 파일이 원본 길이를 넘으면 거부한다.
6. 결과 출력 전 파일 해시, 권한과 관찰을 다시 확인한다. 성공 기록에 로컬 구간·파일 해시·디코딩 프레임 수·입력 근거를 남긴다.

성공 상태는 `media_validated_model_pending`, `training_ready=false`다. 초 단위 범위 검증이며 VFR 영상의 정확한 프레임 인덱스 매핑, 오디오 동기화, 유사·재인코딩·부분 중복 탐지 및 영상 전처리/모델 연결은 후속 작업이다. 파일은 이후 바뀔 수 있으므로 모델 입력 직전에도 검증을 다시 수행해야 한다. 기존 오디오 학습 큐에 이 결과물을 넣지 않는다.

검증 테스트는 합성 색상 영상으로 실제 컨테이너·디코더와 CLI를 실행한다. 동물 영상 성능이나 전문가 검수의 정확도를 측정한 결과가 아니다. 로컬 CLI는 신뢰하는 운영자가 사용하는 도구이며 업로드 공개 서버나 컨테이너 격리 디코더는 아직 구현하지 않았다.
