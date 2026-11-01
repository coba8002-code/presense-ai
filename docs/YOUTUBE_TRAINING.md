# 유튜브 출처 영상 → 검토 → 자세 학습

## 구현 범위

공식 링크 수집/분석(`knowledge.worker`) → 관찰 후보/사람 검토(`training.video_review`) → 허가받은 로컬 원본 연결(`training.video_media`) → **정확한 프레임 추출·검토·학습 입력 생성(`training.youtube_frames`)** → 기존 SmolVLM2 LoRA 실험(`training.small_vlm`)을 연결했다.

유튜브 링크는 출처이며 가중치 학습을 위한 영상 픽셀 그 자체가 아니다. 링크 분석은 기존 공식 provider 경로를 사용하고, 실제 자세 학습에는 제작자가 제공하거나 적법하게 보유한 원본 파일이 필요하다. 새로운 유튜브 다운로더나 접근제어 우회는 추가하지 않았다. 기존 NC/ND/연구용 자료의 상업 학습 차단은 유지한다. 회사 연구 목적도 비상업 허가로 자동 인정하지 않는다.

현재 학습 범위는 **서기/앉기/눕기/판단불가의 단일 프레임 자세**다. 원인·감정·의도, 동적 행동, 개소리 종류를 이 프레임으로 학습하지 않는다. 해설자의 발언과 모델 가설을 관찰 정답으로 자동 복사하지 않는다.

## 준비되는 입력

- `knowledge.sqlite3`: 기존 공식 경로로 생성한 현재 관찰 DB. 버전/출처 검증 시각/권리 만료 검사를 적용한다.
- `config.json`: 현재 채널별 분석·지식 활용 권한. 키를 파일에 적지 않는다.
- `reviews.json`: `training.video_review`의 관찰 검토 계약. 최소5개체/2라벨, 각 분할에 라벨 포함, 개체·녹화·원본 분리.
- `registry.json`: 출처 채널을 명시한 데이터 이용 승인. 학습·상업·원본 확보 권한을 각각 검사한다.
- `bindings.json`: 원본 영상의 상대경로/SHA256/유튜브 source_id/시작 오프셋/획득 근거/정렬 검토 기록. 기존 `training.video_media.Binding` 계약을 사용한다.

위 파일의 이름은 예시다. 예시 설정을 권리 승인이나 실제 전문가 검토로 취급하지 않는다. 보호자·개체·가정 ID는 가명으로 관리한다.

## 1. 검토용 프레임 준비

```sh
python -m training.youtube_frames \
  --db data/knowledge.sqlite3 --config config/knowledge.local.json \
  --reviews data/video-reviews.json --registry data/video-registry.json \
  --bindings data/video-bindings.json --media-root data/authorized-videos \
  --output data/youtube-frame-review
```

검증된 관찰 구간의 중간 시점에서 최대200장, 최대640×640 PNG를 추출한다. 새 출력 디렉터리에 `frames/`, `receipt.json`, `frame-reviews.template.json`이 생성된다. `frames.json`은 생성하지 않는다. 후보 label은 null, frame_inspected는 false다. 구간 전체가 동일 자세라는 가정을 하지 않으므로 **추출한 PNG를 직접 보고** 라벨을 정해야 한다.

템플릿의 candidate_id를 유지하고 label(standing/sitting/lying/unknown), 전역 household_id, reviewer, review_evidence, reviewed_at(Unix초), frame_inspected=true를 실제 검토로 채운다. 모델·내레이션을 복사하는 것으로 검토를 대신하지 않는다. 여러 개/가림/확신 부족은 unknown이다. 인간 리뷰어의 자격이나 진실성을 프로그램이 자동 인증하지는 않는다.

## 2. 검토 결과를 학습 입력으로 변환

```sh
python -m training.youtube_frames \
  --db data/knowledge.sqlite3 --config config/knowledge.local.json \
  --reviews data/video-reviews.json --registry data/video-registry.json \
  --bindings data/video-bindings.json --media-root data/authorized-videos \
  --frame-reviews data/completed-frame-reviews.json \
  --output data/youtube-reviewed-frames
```

원본·권리·기존 관찰을 다시 검증하고 프레임을 재생성한다. 원본/관찰/권한/추출 프레임이 달라지면 candidate_id가 달라져 이전 리뷰가 거부된다. 정확히 한 리뷰/프레임, 리뷰 시각, 알려진 가정ID, 가정별 분할 일관성을 검사한다. 이어 기존 VLM 입력 검사를 수행해 개체·녹화·원본 분리, 중복 프레임, 5개체/라벨 분포 조건을 확인한다. 통과 후에만 `frames.json`이 만들어진다.

프레임 파일은 로컬에 남는다. 사본/원본 삭제와 보존은 운영자가 관리하며, 이 오프라인 산출물이 계정 삭제로 자동 지워진다고 주장하지 않는다. 저장된 과거 receipt를 영구 권한 토큰처럼 사용하지 말고 실제 학습 직전에 이 명령으로 재검증한다. 라이선스 승인은 최신 registry로 다시 검사된다. 정책을 학습 도중 바꾼 경우 진행 중인 실험도 운영자가 중단해야 한다.

## 3. 기존 학습기 실행

권한·검토가 완료된 실제 자료와 사용 가능한 컴퓨팅 예산이 있을 때:

```sh
python -m training.small_vlm \
  --manifest data/youtube-reviewed-frames/frames.json \
  --registry data/video-registry.json --steps 100 \
  --output artifacts/youtube-posture-experiment
```

이는 별도의 명시적 실행이다. 프레임 준비 명령은 모델을 다운로드하거나 학습을 시작하지 않는다. 기존 학습기는 검증셋·보류평가셋 성능과 LoRA 산출물을 기록하며 자동 운영 승격하지 않는다. 시험셋을 본 후 같은 시험셋으로 튜닝하면 독립 최종평가가 아니므로 새 평가셋이 필요하다.

## 이번 검증과 미가동 구분

실제 FFmpeg로 만든 **합성 영상5개**에서10프레임 생성→사람 검토를 모사한 입력→기존 VLM 학습 입력 검증을 실행했다. 가정 누출, 미검토 프레임, 오래된/변경된 후보, 권리 철회, 추출 도중 원본 변조를 거부하는 검사가 있다. 합성 색상 영상은 실제 개 자료나 전문가 정답이 아니다. 유튜브 원본 확보·실제 개 학습·정확도 향상을 완료했다고 주장하지 않는다.

실가동에 필요한 것은 허용된 채널/원본, 실제 사람 검토, 개체·가정 분리 데이터다. 공식 링크 분석은 별도로 기존 YouTube/Gemini 인증·허용된 호출 예산이 필요하다. NotebookLM 요약이나 설명문을 만들었다는 것만으로 VLM 가중치가 학습되지는 않는다.
