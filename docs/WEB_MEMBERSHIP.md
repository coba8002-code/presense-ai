# 실제 웹 계정 베타

## 제공하는 흐름
`/auth`에서 이메일 식별자·비밀번호로 가입하고 한 번 표시되는 복구 코드를 보관한다. `/app`에서 로그인 쿠키로 반려견 프로필·상황 메모·소리 분석 작업을 사용한다. 로그아웃하면 화면 입력·선택한 파일·녹음 버퍼·프로필·메모·작업 표시를 초기화한다. 다시 로그인하면 서버 자료를 조회할 수 있다. 기존 브라우저 공용 관찰 기록을 회원 계정에 자동 연결하거나 읽지 않는다.

이메일은 **소유 확인하지 않은 로그인 식별자**다. 확인 메일·메일 복구·소셜 로그인·결제는 제공하지 않는다. 계정 설정에서 현재 비밀번호를 확인해 비밀번호/복구 코드를 바꾸거나 탈퇴한다. 복구 또는 비밀번호 변경은 기존 모든 세션과 이전 복구 코드를 철회한다. 비밀번호와 복구 코드를 모두 잃으면 자동 복구할 수 없다.

`/design`은 API를 사용하지 않는 별도 디자인 시안이다. 실제 화면인 `/auth`, `/app`과 구분한다. 이름/상황 메모는30일, 분석 결과는24시간이라는 베타 보관 규칙이므로 장기 행동 일지·가족/기관 공유가 완성된 서비스는 아니다.

## 실행 준비
기존 Python 의존성과 소리 모델 의존성을 설치하고 고정 AST 가중치를 명시적으로 캐시한다. [AUDIO_JOBS.md](AUDIO_JOBS.md)의 준비 절차를 따른다. 계정 기능 자체는 외부 인증 서비스나 유료 API를 호출하지 않는다.

서버 프로세스에 다음 값을 명시적으로 설정한다. `.env.example`은 자동 로딩되지 않는다. 실제 운영자명·연락처와 검토한 이용 안내/개인정보 버전을 사용한다. 이 설정만으로 법률 검토가 완료되는 것은 아니다.

|환경변수|설정|
|---|---|
|PETSENSE_ENABLE_WEB_AUTH|true|
|PETSENSE_PUBLIC_ORIGIN|접속할 고정 HTTPS origin. 예: https://petsense.example.kr; 경로 없이 지정|
|PETSENSE_OPERATOR_NAME|실제 운영자 이름|
|PETSENSE_PRIVACY_CONTACT|개인정보 문의 이메일|
|PETSENSE_TERMS_VERSION / PETSENSE_PRIVACY_VERSION|동의할 안내의 버전|
|PETSENSE_ACCOUNT_DB|저장소 밖의 비공개 SQLite 절대 경로|
|PETSENSE_ENABLE_AST_JOBS|true|
|HF_HOME|준비한 고정 모델 캐시의 절대 경로|

신뢰할 수 있는 HTTPS 인증서가 준비된 국내 PC에서 서버와 worker를 별도로 실행한다. 아래 경로는 실제 파일로 대체한다. 인증서 개인키·DB·복구 코드·계정 정보를 GitHub에 올리지 않는다.

```sh
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8443 --no-proxy-headers --ssl-certfile /private/fullchain.pem --ssl-keyfile /private/privkey.pem
python -m backend.job_worker --db /private/petsense.sqlite3 --watch
```

이 명령은 로컬 실행 예시이며 공용 배포를 수행하지 않는다. 포트가8443이면 공개 origin에도 그 포트를 포함한다. 앞단 TLS 프록시를 쓰는 실제 배포에서는 고정 Host·HTTPS 전달과 신뢰할 프록시 IP만 별도로 설정한다. `forwarded-allow-ips=*`로 외부 헤더 전체를 신뢰하지 않는다. HTTP나 다른 Host로 계정/쿠키를 우회하는 운영 옵션은 없다.

## 검증 재현
```sh
python -m unittest discover -s tests -q
node tests/test_web_session.cjs
python -m scripts.member_browser_smoke --output artifacts/member-smoke-fresh.json
python -m scripts.member_browser_smoke --real-ast --output artifacts/ast-member-smoke-fresh.json
```

브라우저 검사는 Playwright Chromium·OpenSSL·로컬 소켓 실행 권한이 필요하다. 임시 자체 서명 HTTPS 인증서의 SPKI만 Chromium에 신뢰시키고 종료 시 계정 DB/키를 삭제한다. 인증서 검증을 전역 해제하지 않는다. 기본 모델은 명시적 모의 실행이고 `--real-ast`만 실제 고정 가중치·별도 worker를 사용한다. 가입→쿠키/CSRF→프로필/메모→합성 WAV 작업→로그아웃/재로그인→복구→비밀번호 재확인 탈퇴와 데이터 삭제를 검사한다. 증거 JSON에는 비밀번호·이메일·세션·CSRF·복구 코드를 넣지 않는다.

## 보안·운영 경계
쿠키는 HttpOnly/Secure/SameSite=Strict,24시간이며 세션 원문을 JSON·브라우저 저장소에 넣지 않는다. 비밀번호는 scrypt, 복구/세션은 해시만 DB에 보관한다. 고정 Origin·세션 CSRF·입력4KB/10초 제한·DB 공유 요청/KDF 제한을 적용한다. 자세한 계약은 [WEB_AUTH_SPEC.md](WEB_AUTH_SPEC.md)에 있다.

공개 운영에는 메일 소유 확인/복구 방식 결정, 입구 제한·OS 자원 격리, [독립 정리 프로그램](PRIVACY_MAINTENANCE.md)의 국내 PC 서비스 설치·감시와 백업 삭제, 국내 PC/실제 휴대폰 검증, 모니터링·복구·개인정보/약관 검토가 남는다. 이 베타를 공개 운영 보안 심사나 실동물 분석 정확도 증거로 표현하지 않는다. GitHub는 소스·CI이며 사용자 서비스의 추론 서버를 대신하지 않는다.
