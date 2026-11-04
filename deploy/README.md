# 국내 Linux/WSL 제한 베타 배포 절차

이 파일들은 템플릿이다. 실제 서버·DNS·TLS·방화벽·이메일 소유 확인·백업 복구는 아직 연결/검증하지 않았다. GitHub는 소스/CI이며 실행 서버가 아니다. Windows 네이티브 서비스는 별도 설정이 필요하며 WSL에서도 외부 포트 전달과 PC 절전/재시작을 검증해야 한다.

1. 국내 서버/도메인을 확정하고 A/AAAA 및80/443의 접근을 확인한다.8000은 외부에 공개하지 않는다.
2. 전용 OS 계정 petsense와 `/var/lib/petsense/private`0700, `/etc/petsense/beta.env`0600을 만든다. 소스는 `/opt/petsense/current`, Python3.12 가상환경은 `/opt/petsense/venv`. `requirements.lock`을 설치한다. 템플릿의 CHANGE_ME는 실제 운영자/도메인/연락처/약관 버전으로 교체한다.
3. 서비스와 worker를 멈춘 상태에서 해당 OS 계정으로 `Store`를 명시적으로 초기화/마이그레이션한다. 기존 DB가 있으면 현재 스키마와 삭제 이력을 확인한다. 버전이 높은 DB를 오래된 코드로 실행하지 않는다.
   `python -c 'import os; from backend.accounts import Store; Store(os.environ["PETSENSE_ACCOUNT_DB"])'`
4. 설정을 환경에 로드하고 `python -m scripts.beta_preflight`를 실행한다. 모든 검사 통과 후 `python -m scripts.serve_beta`. 설정값/이메일 명단은 출력되지 않는다. 첫 실행은 SIGNUP_MODE=closed. 제한 참가자를 정했을 때만 allowlist와 최대100개 주소를 설정한다. allowlist는 이메일 소유 확인이 아니다.
5. Caddy를 설치하고 PETSENSE_DOMAIN을 실제 도메인으로 설정하여 `caddy validate --config deploy/Caddyfile`로 검사한다. 서비스는 템플릿 검토 후 설치한다. Caddy TLS 실패 시 우회용 HTTP/인증서 무시 옵션을 사용하지 않는다.
6. API와 독립 만료 정리 서비스가 재시작 뒤 살아나는지 확인한다. 실제 HTTPS `/healthz`, `/auth`, `/understand` 및 타 사용자 접근 차단을 확인한다. `/healthz`만으로 모델 준비를 판정하지 않는다.
7. 음향 모델 기능은 기본 비활성이다. `requirements-audio-model.txt`, 고정 revision 캐시, 모델 프로세스/CPU·RAM·지연·원본 삭제를 대상 서버에서 검증한 뒤에만 AST_JOBS를 활성화하고 `python -m backend.job_worker --db <private-db> --watch`를 별도 전용 계정 서비스로 운영한다. 외부 호출/클라우드 모델은 자동 활성화하지 않는다.

## 인증·복구 검증

현재 이메일은 미검증 로그인 식별자이고 복구 수단은 가입 시 제공하는 일회용 오프라인 코드다. 신규 코드는 안전한 별도 보관소에 보관한다. 실제 이메일 인증/이메일 복구는 발송 서비스·도메인 설정 후 별도 구현해야 하므로 공개 일반 가입을 출시하지 않는다.

합성 HTTPS CI는 코드 복구→비밀번호 변경→이전 세션 철회→새 코드 발급→탈퇴를 검사한다. 운영 점검에서는 운영자 테스트 계정으로 같은 절차를 반복한다. 코드와 비밀번호를 모두 잃은 경우 임의 이메일 진술로 계정 접근을 풀지 않는다.

## 장애/배포 복구

먼저 가입을 closed로 전환하고 worker를 중지한 뒤 장애 원인과 DB 무결성을 확인한다. 앱 롤백은 DB 스키마 호환 버전으로만 수행한다. 물리 백업 복원은 삭제된 계정/일지/세션을 부활시킬 수 있으므로 단순 파일 덮어쓰기 스크립트를 제공하지 않는다. 암호화 백업 정책·최대보관·삭제 이력의 재적용·세션 무효화·격리 복구 연습을 실제 저장소에 맞춰 정한 후 운영 승격한다. 본 템플릿은 이 검증을 완료했다는 증거가 아니다.

## 실제 휴대폰 인수

iPhone Safari와 Android Chrome 각각 기종/OS/브라우저를 기록한다. HTTPS 가입·복구·녹음 권한 허용/거절/철회·10초 녹음/파일 업로드·백그라운드 이동·연결 끊김/재접속·취소·삭제·발열/배터리를 확인한다. Chromium390px/touch CI는 화면/웹 흐름 에뮬레이션이며 이 시험을 대체하지 않는다. 실데이터·복구 코드가 담긴 스크린샷은 공개 CI에 올리지 않는다.
