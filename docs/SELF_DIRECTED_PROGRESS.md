# 자율 개발 진행 기록

2026-10-30 KST. 아래의 실행 완료와 실행 중 상태를 구분한다.

## 완료한 개발과 확인 증거
- PR #3 https://github.com/coba8002-code/presense-ai/pull/3 에 보호자 앱·음성 변환·취소·계정별 메모·계획을 반영했다. #2의 미병합 브랜치 위에 쌓은 검토용 PR이다.
- commit224f8d2339dd23740be91515a32146a3f53f2cad의 backend/browser 실행41023899244·41024327752가 성공했다. 새 Chromium 시나리오는 실제 브라우저 Web Audio 변환·HTTP 계정 메모·브라우저 저장을 검증했다. AST 응답은 모의 처리한다.
- 같은 커밋의 실제 고정 AST 가중치 합성 입력 smoke41023899252가 성공했다. 실제 개 정확도 근거는 아니다.
- PR #4 https://github.com/coba8002-code/presense-ai/pull/4 에 공개 ESC-10 수집·400개 추론·순위 평가 도구를 추가했다. 로컬137개 테스트와 해당 커밋의 backend/browser CI41025543754·41025636362가 성공했다.
- scripts/verify_release.py로 오프라인 검증을 단일 명령으로 재실행하며 실제 테스트 수와 소스 SHA256/로그를 보존하도록 했다. artifacts/release-verification-20261030.json은 로컬137개 및 Node3종·컴파일·기존 스킬 지문 검사 통과를 기록한다.

## 실제 공개 음향 실행 중
실행41025543775 https://github.com/coba8002-code/presense-ai/actions/runs/41025543775 에서 공개 자료400개 수집과 전처리가 통과하고 AST 실제 가중치 추론이 진행 중인 것을 확인했다. 성능 수치는 결과 artifact를 읽기 전 확정하지 않는다. 이후 상태가 바뀌면 이 문서를 갱신한다. 최종 분석 범위와 제한은 PUBLIC_AUDIO_BENCHMARK.md를 따른다.

## 조사와 적용
MDN AbortController https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort 를 근거로 요청 취소와 오래된 결과 폐기를 연결했다. Python3.12 asyncio timeout https://docs.python.org/3.12/library/asyncio-task.html#asyncio.timeout 을 근거로 업로드/추론 대기 제한을 나누었다. 대기 취소가 모델 스레드를 강제 종료하지 않는다는 한계를 반영해 worker 잠금을 유지했다. 강제 종료·메모리 격리는 별도 프로세스 기반 분석 작업으로 후속 구현한다.

## 사용자 연결/참여가 있어야 하는 부분
국내 PC의 AI-Hub 원본과 다운로드 무결성 결과, 실제 휴대폰·마이크·HTTPS 접속 환경은 현재 환경에서 확인되지 않았다. 로커리의 실제 검사 결과를 수신해야 한다. 상업 이용 별도 허락이 필요한 데이터/방송 자료와 고객 인터뷰·파일럿 모집도 실행 완료로 대신할 수 없다.
운영 배포·결제·유료 모델 활성화·공유 브랜치 병합은 아직 수행하지 않았다. 모델 정확도가 확보됐다는 표현으로 앱을 공개하지 않는다.
