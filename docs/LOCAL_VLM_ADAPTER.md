# 로컬 VLM 연결 계약 — 2026-10-31

기존 회사 LLM 우선 사용 요청의 독립 구현 단위. 운영 서버/계정/포트/기존 AX 작업자는 변경하지 않는다. 회사 운영 자료에서 Ollama 루프백 운영과 AX 작업 경로는 찾았으나 실제 관리자 인증/작업자 상태/모델 추론은 미확인이다. 중단된 검사 프로세스가 남아 있지 않고 비밀번호 입력도 진행하지 않았으므로 인증 성공으로 기록하지 않는다. 비밀을 새로 보관하거나 로그인 재시도하지 않는다.

POST /v1/me/vision/local-observe: 기본 비활성. 기존 계정/쿠키/CSRF를 사용한다. operator-only 환경 설정 PETSENSE_ENABLE_LOCAL_VLM=true, PETSENSE_LOCAL_VLM_BASE_URL(끝 /v1), PETSENSE_LOCAL_VLM_MODEL 및 선택 PETSENSE_LOCAL_VLM_KEY. 로컬 OpenAI 호환 API의 chat/completions 프로토콜을 쓰며 OpenAI 서비스 호출이 아니다. http는 localhost/loopback만 허용하며 비로컬은 https만 허용한다. URL 사용자정보/쿼리/fragment는 거절한다. 클라이언트가 endpoint/model/header를 고를 수 없다. 서버 관리자 비밀번호는 API 키가 아니며 이 설정에 넣지 않는다.

입력: 기존 VisionInput 이미지/consent, PNG/JPEG512KB 이하(기존 signature 검사), JSON750KB/업로드15초. 각 요청에 consent=true를 요구하고 다른 필드는 거절한다. 동시 추론은 API 프로세스당1개. 대기열·재시도·클라우드 fallback 없음. 출력은 기존 VisionResult 엄격 스키마와 dog-only/불명확/낮은 점수 판단 보류. 의미/질병/효과의 정답으로 취급하지 않는다.

전송은20초 절대 제한, 응답64KB, redirect 미허용, 로컬 서버 전용 키만 해당 고정 주소에 전달. 사용자 연결 종료/요청 취소 시 HTTP 대기 태스크를 취소/회수한다. 원격 모델 서버 자체의 GPU 연산 중단을 보장하지 않는다. 결과 반환 전 계정을 재검사한다. 원문/결과를 저장하지 않고 공급자 오류·자격증명을 응답에 노출하지 않는다. 모델명/목록 조회를 이미지 능력 검증으로 표시하지 않는다.

검증: 합성 MockTransport만 사용해 consent/no-call, key/endpoint 고정, 비동기 timeout/cancel, 리다이렉트/429/잘못된 schema/큰 응답/비개체 판단 보류, 인증·세션 철회/요청 경계·동시 실행 한도를 검사한다. 실제 서버 합성 생성과 VLM 이미지 적합성 평가는 승인된 연결 대상이 준비된 후 별도 수행한다. 개발 베타 preflight는 이 기능을 자동 활성화하지 않는다.
