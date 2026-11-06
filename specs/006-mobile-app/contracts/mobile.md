# Mobile contracts

화면: 기록(개 선택·직접 관찰·보호자 생각·이후 결과·저장 동의·목록/삭제), 소리(녹음/중단/취소·연결·전송), 설정(언어·개 관리·전체 삭제).
빈 상태·저장/권한/연결 실패에서 재시도 가능한 이유를 표시한다. 저장 동의는 저장마다 새로 확인한다.
녹음과 입력은 탭 이동/앱 중단 때 전송하지 않고 녹음을 지운다. 비밀은 앱 재시작/백그라운드/취소 때 지운다.

HTTPS origin만 허용: credentials/query/fragment/path 없음(또는 /), 포트 허용.
POST /v1/audio/events: Content-Type: audio/wav, Authorization: Bearer <메모리 토큰>, X-Audio-Consent:true, X-Audio-Species:dog.
요청은 최대320044bytes. 사용자 동의 없이 요청 없음. 전체70초/응답64KB, 리다이렉트 금지·자동 재시도 없음.
401/403=인증/동의 확인, 429=바쁨, 503=서버/모델 미준비, timeout=연결 지연.
결과 사건 label≤100자·유한 score0..1·최대20건. production_ready!=false 또는 decision!=abstain은 거부.
JSON 원문/오류 원문·개인정보·인증값을 로그나 기록에 넣지 않는다.

APK는 com.petsense.petsense_mobile, beta 버전. 서명 키는 빌드 환경의 테스트 키이며 소스 ZIP에 포함하지 않는다.
iOS bundle도 같은 기본 식별자이며 Apple에 등록된 소유권을 주장하지 않는다. 배포 전 본인 팀/고유ID로 설정한다.
