# 국내 Windows PC 제한 베타 실행 안내

사용자가2026-10-31 국내 PC 운영을 선택했다. 이전 Windows 화면을 근거로 WSL2/Linux 구성을 제안하며 실제 설치 상태는 확인하지 못했다. 아직 해당 PC 원격 연결·HTTPS 주소가 제공되지 않았고 여기서 PC 설정을 변경한 적이 없다.

## 먼저 PC에서 확인
PowerShell: `wsl --status`, `wsl --list --verbose`. WSL2 배포판과 systemd 지원 여부를 확인한다. Docker나 GPU는 이번 계정/기록 제한 베타의 필수 조건이 아니다. 국내 저장 정책을 유지하고 실제 원본/DB를 GitHub에 올리지 않는다.

WSL에서 Python3.12와 Caddy가 필요하다. 소스/가상환경·전용 계정과 환경 파일 경로는 deploy/README.md를 따른다. DB는 Windows 공유 폴더(/mnt/c 등)가 아닌 WSL Linux의 비공개 파일시스템에 두어 POSIX 권한을 검증한다. 전용 계정이 실행하고 DB 부모0700/파일0600, 환경 파일0600을 유지한다.

## 실행 순서
1. source ZIP 또는 codex/private-beta-readiness-20261031 브랜치 소스를 PC로 가져온다. 프로젝트 루트에서 기본 requirements.lock을 설치하고 전체 테스트를 실행한다. 미확인 바이너리나 공유 인증 코드를 추가하지 않는다.
2. beta.env.example을 비공개 beta.env로 복사해 실제 HTTPS주소/운영자/연락처/약관버전을 설정한다. SIGNUP_MODE는 closed를 유지한다. 환경 파일을 서비스의 EnvironmentFile로 연결하고 임의 셸 실행에 붙여넣지 않는다.
3. 데이터 폴더와 DB를 초기화/마이그레이션한다. 기존자료가 있으면 정합성·삭제 이력을 확인한 뒤 진행한다. `python -m scripts.beta_preflight`의 모든 구성 검사 통과 여부를 확인한다.
4. `python -m scripts.serve_beta` 또는 petsense-api.service를 사용한다. 서비스 실행 Python은 requirements.lock을 설치한 가상환경이다. API는127.0.0.1:8000만 수신한다.
5. 도메인 DNS와 Caddy의80/443 접근을 연결한다. Windows 방화벽·WSL 네트워크 모드·공유기 포트 전달/통신사 NAT를 실제 환경에서 확인해야 한다. 광범위한 방화벽 비활성화나8000포트 공개로 우회하지 않는다. 도메인/TLS가 없으면 계정서비스를 HTTP로 외부 공개하지 않는다.
6. Caddy 경유 실제 HTTPS에서 테스트 계정 생성→로그인→프로필→일지/공유/계획→복구→탈퇴를 확인한다. `PETSENSE_SIGNUP_MODE=allowlist`로 전환할 때 등록한 주소만 받지만 이메일 소유 확인은 여전히 없다.
7. petsense-maintenance.service를 실행해 요청이 없는 동안에도 만료 정리가 이루어지는지 확인한다. PC/WSL 재시작·절전·네트워크 단절 뒤 API와 정리 서비스가 회복되는지 확인한다. Windows 로그인 전에 WSL이 시작되는지는 별도 운영 설정이며 이 템플릿이 보장하지 않는다.
8. 음향 기능은 실제 CPU/GPU·모델 캐시·worker·처리시간을 PC에서 확인한 뒤에만 켠다. 모델 훈련을 자동 시작하거나 유료 API를 호출하지 않는다.

## 이 환경으로 돌려줄 비밀 없는 결과
- WSL 배포판/버전, Python버전, CPU/GPU/VRAM 요약
- 배포 전 검사 JSON(값/비밀 제외), 서비스 정상 여부와 실제 HTTPS 주소
- AI-Hub59/71878 다운로드·크기/해시/CRC 결과와 비식별 라벨 구조
- iPhone/Android 기종/OS별 시험 결과
키·비밀번호·복구 코드·원본 개인정보는 채팅으로 보내지 않는다. 이 결과가 오기 전에는 실제 PC 배포/학습/휴대폰 검증을 완료 처리하지 않는다.
