# 요청별 독립 오디오 프로세스

기존 API의 모델 스레드 방식은 대기를 취소해도 계산을 종료하지 못했다. 현재 /v1/audio/events는 각 분석을 별도 Python 프로세스로 실행하고 제한시간 초과·요청 취소·연결 종료 시 해당 자식을 종료·회수한다. 기존 메모/브라우저 입력 계약과 고정 AST 출력은 유지한다.

## 실행
AST 라이브러리와 서버를 같은 가상환경에 설치한다. 먼저 공개 가중치를 준비한다.
```
python -m scripts.cache_audio_model --cache-dir data/model-cache
```
서버 실행 환경에 HF_HOME을 위 캐시의 절대 경로로 지정하고 PETSENSE_ENABLE_AST=true, 로컬 PETSENSE_API_TOKEN을 설정한다. 원래의 localhost 서버 실행 명령을 사용한다. 런타임 자식은 HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE을 강제로 켜므로 서비스 요청이 모델 다운로드를 시작하지 않는다. 캐시가 없으면503을 반환한다. 기존 환경의 인증서 패치가 적용되도록 최신 requirements.lock도 재설치해야 한다.

## 경계
- 16kHz PCM16 WAV0.1~10초·2MB 입력을 API와 작업자에서 재검사한다.
- 원본 음성은 stdin으로만 전달하며 임시 미디어 파일을 만들지 않는다.
- 모델 프로세스의 결과는64KB 제한, 입력 해시·모델/revision·7개 라벨·유한 점수·abstain/비운영 판정을 검증한다.
- 한 API 프로세스에 분석1개, 업로드15초·작업60초. 혼잡429, 업로드408, 프로세스 기한504, 작업/캐시 오류503.
- 일반적인 TOKEN/SECRET/API_KEY/PASSWORD/PETSENSE 환경변수는 자식에게 전달하지 않는다. 데이터/토큰을 프로세스 명령 인자로 전달하지 않는다.
- POSIX는 새 세션의 프로세스 그룹을 종료하고 Windows는 자식을 종료한다. Windows의 임의 후손 전체 종료는 별도 검증이 필요하다.

## 검증과 한계
실제 작은 자식 프로세스를 띄운 프로토콜·타임아웃·취소·종료 회수 검사와 HTTP 연결 종료에 따른 작업 취소 검사를 포함한다. 실제 AST 가중치를 쓰는 Chromium→HTTP→독립 작업자→브라우저 저장·삭제는 pretrained-audio-smoke의 별도 CI로 확인한다. 모의 AST 브라우저 검사와 구분한다.
요청마다 모델을 다시 읽으므로 지연이 증가할 수 있다. 현재 방식은 자원 격리의 개발 기반이며 운영 지연 목표 달성을 의미하지 않는다. 원본 파일 보관은 없지만 OS의 스왑/메모리 덤프까지 지우는 보장은 하지 않는다.
이 구현은 OS 네트워크/파일 접근 통제나 CPU/RAM cgroup을 제공하는 보안 샌드박스가 아니다. 별도 워커 프로세스·강제 종료가 구현된 것이며 durable job queue, 사용자별 예산/멱등성, 재시작 복구, 운영 인증과 실기기 검증은 다음 단계다. 운영용 다중 API 인스턴스의 동시성 제한은 공유 큐로 구현해야 한다.

## 계정 세션 모드
PETSENSE_REQUIRE_ACCOUNT=true와 PETSENSE_ACCOUNT_DB를 설정하면 분석 API는 X-PetSense-Session만 인정하고 공유 개발 토큰으로의 우회를 차단한다. 앱의 분석 인증 방식을 ‘계정 세션 사용’으로 고르고 계정별 메모 영역에 발급된 세션을 입력한다. 분석 시작과 결과 반환 직전에 세션을 검사해 만료/철회된 세션으로 결과를 받지 못하게 한다. 세션 철회가 실행 중인 CPU 작업을 즉시 종료한다는 보장은 하지 않으며 결과 전달을 차단한다.
이 모드는 기존 운영자 발급 세션을 분석 권한에 연결한 개발 기반이다. 셀프가입·본인확인·복구·소셜로그인·사용자별 사용량 원장까지 완료한 것은 아니다. 기본false는 기존 localhost 개발 토큰과의 호환을 위한 것이다. 계정이 필요한 공개 서비스에서 이 기본값을 그대로 사용하지 않는다.

## 원격 확인 결과
실행 코드1ecab3b5dfb75267db9471a1b98a6f7009321f36, PR #5. 실제 가중치 실행41051446917에서 고정 AST·합성 음성·실제 Chromium/HTTP·계정 세션·독립 프로세스·기록 저장/삭제가 성공했다. https://github.com/coba8002-code/presense-ai/actions/runs/41051446917
동일 실행의 synthetic-ast-inference-not-dog-accuracy artifact12974038859에 ast-browser.json을 보존했다. 입력 SHA256·모델/revision·단일 browser_to_api_seconds·HTTP 상태를 기록한다. 단일 합성 smoke이며 개 행동 성능이나 p50/p95의 근거가 아니다.
backend/browser41051446920에서 브라우저 offline, 모의429/503, 주입된 quota 오류와 수동 복구도 성공했다. 실제 통신 장애/휴대폰 저장장치 시험은 별도다.
