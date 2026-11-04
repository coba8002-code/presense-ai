# GitHub · Supabase · Vercel 테스트 운영

사용자 선택: 2026-11-04. 기존 개발 소스는 PR #37로 develop에 병합했다.
병합 SHA a0330a0424dd6c5881dea85cb3f3b5e905801705, 병합 후 CI 41763854944 성공.
main은 이전 상태로 유지한다. 운영용 소스는 검증한 develop 또는 명시한 클라우드 PR HEAD다.

## 구현 범위

같은 저장소의 cloud/는 Vite 브라우저 앱이고 Supabase Auth와 Postgres를 사용한다.
기존 FastAPI/SQLite 앱을 Vercel의 임시 파일시스템에 그대로 올리지 않는다.
로컬 앱 전체의 기능 동등 이전은 아니며 다음 기능부터 클라우드 테스트한다.

- 이메일 가입·로그인·재설정, 기록 보관 동의
- 개 프로필, 보호자 관찰 노트, 텍스트 요청 이력, 돌봄 계획
- 기록 내보내기/삭제, 재인증 후 회원 탈퇴
- 기존 기기 내 영상 관찰 화면. 파일은 서버 전송하지 않음

AI 미연결 요청은 awaiting_model이며 완료/감정 확률/진단을 생성하지 않는다.
사진·오디오 서버 분석, 자동 학습, 공유/리포트 등 기존 로컬 기능의 클라우드 전환은 이번 범위에 포함하지 않는다.
연구 모델을 자동 승격하거나 고객 원본을 이전하지 않는다.

## 배포 순서와 실제 상태

1. 전용 Supabase 프로젝트: 조직 선택 답변 대기. 기존 roomax 등 다른 서비스 DB는 사용하지 않는다.
2. 조직 확인 후 MCP get_cost 비용을 제시하고 동의 확인 후 생성한다. 서울 ap-northeast-2 권장.
3. 기존 테이블/권한 확인 후 supabase/migrations SQL 적용. 보안·성능 advisors와 실 DB 테스트 확인.
4. pg_cron 정리 작업의 실제 등록/실행을 확인한다. 만료 RLS 차단과 물리 정리는 별개다.
5. Vercel 프로젝트 rootDirectory=cloud, Node 24, Vite, outputDirectory=dist.
   기존 영상 파일을 빌드 중 읽으므로 프로젝트의 루트 외부 소스 접근을 허용해야 한다.
6. VITE_SUPABASE_URL과 VITE_SUPABASE_PUBLISHABLE_KEY만 공개 빌드 변수로 설정한다.
   service_role/secret 키를 VITE_ 변수에 넣으면 안 된다. 프로젝트 키는 문서에 저장하지 않는다.
7. 회원 탈퇴 함수 배포 및 PETSENSE_ALLOWED_ORIGINS에 실제 Vercel 원점만 설정.
   함수에서 직접 getUser 및 활성 session_id를 검증한다. 공개 API 키는 사용자 인증이 아니다.
   비밀 service_role은 Supabase 기본 Edge 환경 안에서만 사용한다.
8. Auth Site URL/redirect allowlist를 실제 배포 URL로 설정하고 테스트 소유자가 직접 이메일 인증·복구를 확인한다.
   기본 이메일 발송 제한/SMTP, 비밀번호 서버 정책은 실제 프로젝트 설정 확인 전 완료로 보지 않는다.
9. 보호된 preview에서 가입→개 등록→관찰/요청 취소→내보내기→탈퇴까지 실 연결 확인 후 테스트 운영.

인증 정보가 없는 빌드는 연결 준비 안내와 로컬 영상 화면만 제공하며 로그인 폼을 숨긴다.
이 상태를 운영 가능한 전체 서비스라고 표시하지 않는다. Supabase 계정은 명시적 탈퇴까지 유지되며
프로필/노트/요청/계획은 생성 후 30일 표시, 시간당 정리 작업으로 물리 삭제한다.
실 DB/cron 적용 전 현재 상태는 스키마 준비이며 실제 정리 가동을 의미하지 않는다.

## 검증 증거와 재현

```sh
npm --prefix cloud ci --ignore-scripts
npm --prefix cloud test
npm --prefix cloud run build
```

Node 테스트 9개: 공개 키/입력, 실제 PGlite Postgres의 RLS·교차 계정 FK·소유권·세션 철회·쿼터·보관기간,
탈퇴의 원점/활성 세션/선행 세션 철회/관리자 삭제 실패 처리. Auth 스키마는 테스트 전용 모사다.
브라우저 검사는 합성 Auth/REST 응답으로 Chromium의 로그인/동의/프로필/텍스트 요청 취소/노트/돌봄 완료/
390px 레이아웃/로그아웃 정리/영상 화면을 검증한다. 실제 Supabase 이메일·배포·AI 정확도 증거가 아니다.

```sh
VITE_SUPABASE_URL=https://synthetic.supabase.co \
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_synthetic_browser_fixture \
npm --prefix cloud run build
python .agents/skills/webapp-testing/scripts/with_server.py \
  --server 'cd cloud && exec node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 5174 --strictPort' \
  --port 5174 -- python cloud/tests/browser_smoke.py
```

배포 빌드에는 synthetic 설정을 쓰지 않는다. 설정 없는 빌드는 인증을 차단한다.
환경 변수 설정만으로 실 연동 완료 처리하지 않는다. 내부 LLM 포트 개방, AX 로그인, 유료 모델 호출은 필요 없다.
