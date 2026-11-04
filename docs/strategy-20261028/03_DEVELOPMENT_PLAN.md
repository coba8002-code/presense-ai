# PetSense AI 개발기획서
> 2026-10-28 · v5 · 재현 가능한 실험에서 운영 제품으로

## 현재 구조와 이번 변경
현재 FastAPI가 실시간 소리 데모·VLM 관찰 어댑터·영상 검수 화면을 제공한다. 이번에 /app 보호자 웹 앱과 /v1/audio/events 전체 WAV 사건 점수 API를 연결했다. AST 가중치 로더는 선택적으로 동작하며 모델 준비 전 기본 비활성화다. 기존 /v1/audio/chunks는 1초 PCM 흐름이고 새 WAV API와 입력 계약이 다르다.

브라우저 → 명시적 동의 + 인증 토큰 → 제한된 WAV 파서 → CPU AST 추론 → 7개 사건 점수/abstain → 선택적 브라우저 기록.
국내 PC → AI-Hub 공식 다운로드 → 파일/권리/개체 검수 → 변환/분할 → 독립 평가 → 후보 학습 → 승인 모델 배포.
GitHub → 소스/테스트/CI. 실제 AI-Hub 원본과 개인 기록은 국내 승인 저장소에 둔다.

## 구성요소별 책임
|구성|책임|현재/목표|
|브라우저 앱|입력·상태·결과·기록|구현; 실제 기기 검증 필요|
|FastAPI|인증·동의·제한·오류 계약|로컬 개발용 구현; 운영 인증 후속|
|AST|개 관련 소리 사건 점수|어댑터 구현; 실데이터 정확도 미확정|
|경량 VLM|보이는 자세·상황 관찰|실험 코드; API와 제품 품질 연결 후속|
|관절 추정|행동의 시간적 특징 보조|AP-10K 자료 확보; 추론 통합 후속|
|RAG|출처가 있는 사례·관리 설명|기존 지식 경로; 제품 화면 연결 후속|
|정형 계산|기간별 빈도/시간/수집량 비교|결정적 계산으로 구현 예정|
|LLM 문장화|관찰·근거 범위 안에서 설명|출처/보류를 보존하는 후속 기능|

## API 계약과 데이터
POST /v1/audio/events: Content-Type audio/wav, Authorization Bearer, X-Audio-Consent=true, X-Audio-Species=dog. PCM16, 16kHz, mono/stereo, 0.1~10초, 최대2MB. 활성화 PETSENSE_ENABLE_AST=true. 401 인증, 403 동의, 413 크기, 415 유형, 422 입력/종, 429 부하, 503 모델 준비 실패.
출력은 model/revision/input_sha256/duration_seconds/dog_event_scores/decision/production_ready. 점수는 독립 sigmoid이며 보정 확률이 아니다. API는 원본을 파일로 저장하지 않는다. 최초 가중치 준비에는 다운로드가 필요하며 운영에서는 배포 전에 캐시한다.

앱 기록 v1: id, at, pet, context, result. localStorage 키 petsense.observations.v1, 100개 상한. 서버 토큰과 원본 미디어는 저장하지 않는다. 현재는 단일 브라우저 저장이며 다중 계정/동기화/충돌 해결/백업을 제공하지 않는다.
목표 DB: users, pets, consent_events, media_objects, analysis_jobs, observations, reviewed_evidence, feedback, shares, deletion_jobs, model_versions. 각 행에 owner/tenant 식별자, 시각, 스키마 버전과 모델 버전을 둔다. 현재 DB 마이그레이션이 구현된 것으로 표시하지 않는다.

## 국내 데이터·학습 경로
ESC-10: 400 WAV 중 dog 40, source ID 기반으로 그룹화 가능. 실제 개체 ID가 없어 개체 분리 성능 증명에 사용하지 않는다. 16kHz 변환과 해시 검증 완료. AP-10K: 개 이미지 1,000장·관절 주석, 3가지 공식 분할안을 합치지 않는다.
AI-Hub59/71878: 사용자 승인 진술은 있음. 원본은 국내 PC 인증 경로에서 수령 후 스키마 확인. species, animal/household/session identity를 실제 필드에 매핑하기 전 자동 학습 등록 금지.
DogSpeak/InterPet4D와 보듬TV는 상업 이용 허락 해결 전 학습 대상에 넣지 않는다. 문서와 링크를 확보한 것을 미디어 학습 완료로 취급하지 않는다.

실험 E1: 무학습 AST 기준 점수·음향 오탐 평가. E2: 검수된 발성 데이터로 frozen encoder+작은 head. E3: 관절/프레임 모델 비교. E4: 동기화 음성+영상 결합. 같은 독립 평가셋에서 오디오만/영상만/융합 성능과 비용을 비교한다. 전문가 해설을 들은 모델이 영상 이해 성능으로 평가되는 누수를 차단한다.

## 개발 순서와 완료 조건
|작업|의존|결과물|완료 기준|
|D01 보호자 웹 첫 흐름|기존 API|/app·기록 관리|입력/오류/결과/삭제 검사|
|D02 실제 기준 평가|권리 확인 음향|모델 버전·표본별 결과|실제 파일 실행 및 재현 로그|
|D03 모바일 입력|D01|마이크/영상 선택·형식 변환|실기기 iOS/Android, 취소·권한 철회·10초 분할|
|D04 운영 계정|D01|사용자 인증·개별 접근|다른 사용자 기록 접근 불가, 토큰 회전|
|D05 비동기 분석|D02,D04|job queue·상태조회|멱등 요청·재시도·시간제한·취소|
|D06 보관/삭제|D04|국내 객체저장·삭제 worker|원본·파생물·검색 인덱스 삭제 검증|
|D07 변화 리포트|반복 기록 확보|수집량 보정 통계|기간/누락 표시, 근거 없는 추세 차단|
|D08 전문가 공유|D04,D06|기간 제한 공유|철회 즉시 접근 차단·접근 감사|
|D09 요금·기관|유료 실증|구독·한도·tenant|정산/환불·기관 격리 검사|

## 실행 계획 — 인력과 데이터 준비 조건부
1~2주: D01 검사·D02 기준 평가와 데이터 스키마. 3~4주: D03·D04. 5~8주: D05·D06·30가정 파일럿. 9~12주: D07·D08·가격/기관 실증. 미확보 데이터·담당 인력·검수 계약에 따라 조정하며 확정 납기가 아니다. 전국 배포는 기능 완성이 아니라 품질·삭제·인증·비용·지원 대응의 통과 후 결정한다.

## 검증·운영
단위/계약: 동의/종/토큰/크기/비정상 WAV 거절, 모델 오류의 안전한 응답, API 반환 계약. UI: 입력·전송 중 중복·503 안내·저장 실패·전체 삭제·내보내기. E2E: 브라우저→실제 모델→저장→재열기→삭제를 국내 PC에서 확인한다.
CI는 합성 자료와 모의 모델 검사를 기본으로 하며 실제 가중치 smoke를 별도 선택 실행한다. 테스트 통과를 실제 개 행동 정확도로 설명하지 않는다. Windows/WSL와 실제 휴대폰 측정은 별도 기록한다.
운영 목표: 사용자별 인증, 공유 rate limit, 프로세스별 단일 모델 worker, GPU/CPU 자원 제한, 원본 제외 로그, request ID·모델 버전·지연·실패율 계측. 현재 단일 프로세스 토큰과 메모리 제한은 공용 인터넷 배포에 충분하지 않다.
롤백: 모델 버전 고정, 신규 모델 제한 노출, 품질/지연 악화 시 이전 버전으로 복귀. 학습 자동화는 후보 저장까지만 수행하고 검수 없는 자동 운영 교체를 하지 않는다.

## 실행 방법
기본 서버: README.md의 Python3.12 환경과 requirements.lock 설치.
AST와 서버를 한 환경에서 실행하려면 local_pc/setup_audio_cpu.sh 실행 후 같은 .venv-audio에 requirements.lock을 추가 설치하고 pip check로 충돌 확인.
PETSENSE_ENABLE_AST=true, PETSENSE_API_TOKEN을 로컬 환경변수로 설정하고 python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 실행. 브라우저에서 http://127.0.0.1:8000/app 접속.
토큰은 채팅이나 GitHub에 기록하지 않는다. 모델 사용을 끄면 앱은 연결 준비 오류를 표시한다. 실제 공개 배포는 이 명령의 범위 밖이다.

## 2차 개발 반영 — 입력과 기록 활용
구현: 마이크 최대10초 녹음, 사용자가 고른 음성 파일에서 시작 구간 선택, 브라우저 내 mono/16kHz PCM16 WAV 변환. 원본 파일20MB 제한, 동의 해제/취소/화면 이탈 시 마이크 해제. 선택 구간 표시와 최근7일(KST 날짜)의 기록 수·기록일 수, 상담 준비 텍스트 내보내기를 추가했다. 데이터는 브라우저의 최대100개 저장 기록 범위다. 같은 이름은 합산되므로 개체 ID를 갖춘 다견 계정 기능은 후속이다.
이는 통제된 관찰시간을 바탕으로 한 행동 추세 분석이 아니다. 센서 관찰 누락·노출시간이 없어 개선/악화를 판정하지 않는다. 원본은 자동 저장하지 않으며 다운로드 보고서는 사용자가 공유 여부를 결정한다.
검증: Python122개 테스트, Node 모의 DOM 및 WAV/변환/주간 집계 검사 통과. 마이크 permission 대기 중 취소·동의 철회·정상 종료 시 track 해제를 모의로 확인했다. 실제 브라우저의 Web Audio 렌더링과 모바일 코덱은 미검증이다. 마이크는 HTTPS/localhost에서만 지원되며 휴대폰에서 PC의 HTTP LAN 주소로 접속하는 경우 파일 선택을 사용하거나 별도 HTTPS 구성이 필요하다.
다음 우선순위는 국내 PC·실제 휴대폰 E2E, 운영 사용자 인증·계정별 기록 접근, 비동기 분석/오류 복구다. D03 음성 입력 부분은 구현됐고 영상 파일 처리 및 실기기 완료 조건은 남아 있다.

## 3차 개발: 계정별 보호자 메모
EXEC 순서는 tasks/todo.md를 기준으로 한다. /v1/me/notes와 /v1/me/account는 X-PetSense-Session을 사용한다. PETSENSE_ACCOUNT_DB가 없으면 비활성화된다. 이는 단일 PC에서 CLI가 발급한 세션으로 연결하는 개발 기반이며 운영 로그인·본인 확인·다견 프로필 완성이 아니다.

국내 PC에서 프로젝트 루트 기준:
```
python -m backend.accounts --db data/private/notes.sqlite3 --token-file data/private/local-session.json
```
CLI가 data/private/를 생성하며 이미 있는 세션 파일은 덮어쓰지 않는다. 원문 세션은 지정된 로컬 파일에만 기록하고 DB에는 해시만 저장한다. 기본24시간, --ttl로 60초~7일까지 지정 가능. 동일 사용자의 새 세션은 --owner 기존UUID로 운영자가 발급한다. 세션 파일을 채팅·GitHub에 올리지 않는다.
서버 실행 환경에서 PETSENSE_ACCOUNT_DB=data/private/notes.sqlite3을 지정한다. 앱의 ‘계정별 보호자 메모’ 영역에 세션을 입력하고 보관 동의를 체크하면 이름·상황만 저장한다. AST 분석 토큰과 별도다. 분석 결과의 계정 동기화는 아직 구현하지 않았다.

POST /v1/me/notes는 X-Storage-Consent=true와 pet/context JSON만 받으며 임의 owner나 모델 결과를 거절한다. 메모는30일 보관, 사용자당500개, 목록100개 단위 offset 조회. DELETE /v1/me/notes/{id}는 소유자만 삭제. DELETE /v1/me/account는 X-Delete-Confirm=delete-account가 필요하며 메모와 모든 세션을 같은 DB 트랜잭션에서 삭제한다. 브라우저 관찰 기록은 별도 삭제한다.
30일은 접근 시 정리하는 개발 보관 규칙이다. 사용되지 않는 DB의 정기 삭제 작업, 백업 삭제/파기, 암호화·국내 호스팅 설정은 운영 게이트에 남는다. SQLite secure_delete와 파일 권한은 백업/저장장치 전체의 물리 삭제 보장이 아니다. 현재 단일 PC DB는 공개 인터넷 운영 구성이 아니다.

## 2026-10-30: 취소·기한·검증 자동화
분석 요청 취소, 파일 변경, 동의 철회, 화면 이탈은 fetch를 AbortController로 취소하고 이전 요청에서 늦게 온 결과를 표시/저장하지 않는다. 브라우저에서 음성 변환 자체를 강제 중단하는 기능은 아니며 변환 후 전송을 차단한다. 요청 전체의 화면 대기는90초로 제한한다. 자동 재전송은 하지 않는다.
서버 업로드는15초, 추론 대기는60초 제한이다. asyncio timeout은 실행 중인 모델 스레드를 강제 종료하지 않으므로 단일 worker lock을 유지하며 새 요청은429를 받을 수 있다. 운영의 강제 중단·메모리 격리는 후속 프로세스 기반 worker가 필요하다. 408 업로드 제한, 504 추론 제한, 429 worker혼잡을 구분한다.
검증: Python133개 및 Node모의 검사3종 통과. 새 scripts/product_browser_smoke.py는 실제 Chromium·HTTP·Web Audio 변환과 계정 메모 API를 검사하지만 AST 응답은 모의 처리한다. 작성/로컬 정적검사는 완료했고 원격 실행 결과는 별도 기록한다.
공식 근거: https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort 및 https://docs.python.org/3.12/library/asyncio-task.html#asyncio.timeout . 새 외부 라이브러리 추가 없이 브라우저/표준 Python 기능으로 적용했다.

## 2026-10-30 후속 검증 완료: 요청별 프로세스와 계정 분석
이전 단락의 모델 스레드 추론은 /v1/audio/events에서 요청별 자식 프로세스로 대체했다. 업로드15초·작업60초, 취소/연결 종료/시간초과 시 자식 종료·회수, offline 캐시·입력/결과 한도와 모델/원본 해시 검증을 적용했다. PETSENSE_REQUIRE_ACCOUNT=true에서는 메모와 같은 계정 세션을 분석 권한에 사용하고 공유 개발 토큰을 차단한다. 결과 반환 전 세션도 재검사한다. 국내 저장소·지속 job·운영 로그인·가족 권한은 미구현이다.
실행 코드1ecab3b의 실제 가중치 Chromium→계정 인증→API→독립 AST→결과/저장/삭제 CI41051446917이 성공했다. 합성 음성이며 실제 개 정확도 근거가 아니다. backend/browser41051446920에서 모의429/503·offline·quota 오류와 수동 복구도 확인했다. Windows/iOS/Android 물리 기기 검증은 남는다. 상세와 실행 명령: docs/ISOLATED_AUDIO.md.

## 독립 정답 확보와 검증
영상 정답 계약/CLI는 PR #6, 실행 코드b0b9996의 backend/browser41053114599·41053123664로 검증했다. 기존 주석과 일반 관찰 검수를 활용하고 전문가는 기준·불일치·표본에 집중한다. 전수 전문가 연동은 요구하지 않는다. 모델 후보 라벨·보호자 상황 보고·전문 해석을 독립 관찰 정답과 구분한다. 실제 정답/영상/성능은 별도 확보 조건이며 현재 계약 검증은 evaluation_ready=false다. 세부 전략: docs/LABEL_ACQUISITION.md, docs/VIDEO_EVALUATION.md. 로컬 최종153개 Python 및 Node3종 통과.

## 프로필·영속 분석 큐·서비스 GUI 후속
PR #8 프로필/소유권과 PR #9 동의 기반 SQLite 큐·별도 worker·멱등/취소·한도를 구현했다. 실행 코드f5e76dc의 실제 고정 AST 큐 Chromium41063644634가 성공했다. PR #10의 GUI 포함 backend/browser41065800327·41065842171,186개 Python·Node3종도 통과했다. /design은 가입부터 결과까지6화면 시안이고 실제 가입/API 호출은 하지 않는다. 상세는 PET_PROFILES.md, AUDIO_JOBS.md, SERVICE_GUI.md와 현재 tasks/todo.md를 따른다. 운영 인증/가족 권한/공유 입구 제한/정리 타이머·백업 삭제/실기기·실제 개체 품질은 남는다.
