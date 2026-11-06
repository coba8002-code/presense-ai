# Data model

LocalState(schema_version=1, language=ko|en, server_url=HTTPS또는빈값, pets[], entries[]).
DogProfile(id, name1..40, created_atUTC). species는 dog 고정, 목록20개 상한.
GuardianEntry(id, pet_id, observed_atUTC, saved_atUTC, expires_atUTC=saved+30일,
observation1..500, hypothesis0..500, follow_up0..500, source=guardian_report).
직접 관찰은 관찰 가능한 행동을 적는 보호자 진술이며 독립 검증된 정답으로 승격하지 않는다.
follow_up은 보호자가 이후 확인해 적은 결과다. 전문가 검증이나 모델 학습 정답이 아니다.
로컬 ID는 Random.secure 기반16바이트 hex. 삭제된 프로필의 기록은 남기지 않는다.

녹음 상태: idle→requestingPermission→recording→ready→uploading→ready/result.
어느 대기 상태든 cancel/background→idle, token/result/PCM 제거. 작업 세대로 늦은 응답 무효화.
PCM≤320000 bytes·짝수 길이. 0.1초 미만은 분석하지 않는다. 원본 파일 없음.
서버 결과는 decision=abstain, production_ready=false, model/provider metadata와 label/score 사건 목록만 사용한다.
