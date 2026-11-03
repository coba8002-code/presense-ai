# PetSense 집중 QA — 2026-11-03

## 적용한 GitHub 스킬

스타 수는 조회일의 저장소 전체 수이며 개별 스킬 품질이나 전 세계 순위가 아니다. 널리 쓰이는 후보와 프로젝트 적합성을 함께 검토했다.

| 저장소 | 확인 스타 | 적용 스킬 | 적용 방법 |
|---|---:|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | 311,476 | systematic-debugging, verification-before-completion | 재현 실패 → 원인 → 수정 → 새 검증 증거 |
| [anthropics/skills](https://github.com/anthropics/skills) | 186,929 | webapp-testing | Playwright 실제 Chromium/HTTP/DOM 검증 |
| [trailofbits/skills](https://github.com/trailofbits/skills) | 7,973 | property-based-testing | 데이터 그룹, PCM, 이벤트 시간 불변조건 생성 검사 |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 112,916 | 기존 TDD·보안 스킬 유지 | 실패 선행, 소유자·동의 경계 확인 |

새 스킬 4종과 참고·라이선스 29개 파일을 `.agents/skills/`에 원본 그대로 보존했다. [고정 목록](../agent_skills/qa-skills-lock.json)에 커밋·원본 경로·SHA256·스타 조회일을 기록했다. Superpowers MIT, webapp-testing Apache-2.0, Trail of Bits CC-BY-SA-4.0 원문을 함께 보존한다. 기존 스킬과 Spec Kit을 덮어쓰지 않았다. 스킬의 예제 스크립트를 무조건 실행하지 않으며 프로젝트 지침이 우선한다.

PBT 전용 의존성은 추가하지 않았다. 표준 라이브러리 seeded generator/NumPy로 불변조건을 검사하므로 Hypothesis의 자동 축소·탐색 범위까지 적용한 것은 아니다.

## 발견 및 수정

### QA-01 비정상 인증 헤더가 500을 유발 — 수정

Latin-1로 해석된 비ASCII HTTP 헤더를 `secrets.compare_digest(str, str)`에 넘기면 TypeError가 발생했다. VLM, 실시간 오디오, 오디오 이벤트, 지식검색의 Bearer 검증과 쿠키/헤더 충돌·CSRF 검증에 영향을 준다. 인증 우회는 확인되지 않았으나 잘못된 요청이 정상적인 401/403 대신 서버 오류가 되었다.

`backend/credential_compare.py`가 ASCII 형식을 먼저 확인하고 정상 토큰에만 상수시간 비교를 적용한다. 비정상 자격증명은 거절한다. `tests/test_auth_header_boundaries.py`: 수정 전 8개 실패·2개 오류, 수정 후 전체 통과. 실제 사용자 자격증명은 사용하지 않았다.

### QA-02 관측 누락이 이벤트 후처리를 중단 — 수정

허용된 종료 임계값 `exit=0`에서 누락된 Bark 관측을 0으로 간주해 이벤트에 편입하고 최대 점수 계산 중 KeyError가 발생했다. 관측 없는 창에서 기존 이벤트를 종료한다. 실제 측정 점수 0은 누락과 구분한다. 수정 전 실패와 수정 후 통과를 `tests/test_qa_properties.py`로 확인했다.

### QA 실행기 호출 방식 — 수정

새 실행기가 기존 `browser_smoke.py`를 모듈로 실행해 형제 import를 찾지 못했다. 기존 CI와 같은 `python scripts/browser_smoke.py` 호출로 변경했다. GUI 스크립트 2개의 필수 출력 디렉터리 인자도 추가했다. 이 실행기 문제들은 제품 결함과 별도로 기록하며 원래 실패 로그를 보존한다.

## 실행 범위와 증거

- 수정 전 기존 Python 370개 통과. 수정 후 376개 전체 회귀검사.
- 생성 검사: 무작위 그룹 250개를 독립 그래프 도달성으로 비교, 입력 순서·중복 행 불변성. PCM 102개 길이에서 유한값·극성 대칭과 7개 잘못된 길이. 이벤트 250개에서 시간 이동 불변성과 판단 유보 보존.
- JavaScript 파일 9개(노드 테스트 항목 10개): 취소·동의 철회·마이크 정리·저장 오류·세션·일지·리포트.
- 실제 Chromium/로컬 HTTP: 가짜 마이크→업로드→철회, 영상 검토, 연구 화면, 분석 화면 오류 복구, 작업 큐, HTTPS 가입→프로필→일지→공유/돌봄→복구→삭제, 모바일 뷰포트.
- 로컬 동시 요청 4개, 총 200회: `/healthz`와 `/app`. 모델 추론 부하나 운영 수용량 시험은 아니다.
- `pip-audit==2.10.1`: requirements.lock의 17개 의존성, 알려진 취약점 0건. 선택 모델/브라우저 전체 의존성·미공개 취약점까지 안전하다는 의미는 아니다.
- `pip check`, compileall, 기존 스킬 및 새 29개 스킬 파일 해시 검증.

원본 로그: `artifacts/qa-hardening-20261103/`. 최종 요약은 [검증 증거](evidence/QA_HARDENING_20261103.json)에 기록한다. CI에는 새 스킬 무결성 검사와 로컬 제한 부하 검사를 추가했다. 원격 CI 결과는 해당 PR에서 별도로 확인한다.

## 재현

```sh
python -m scripts.qa_hardening --browser --output artifacts/qa-new-run
uvx pip-audit==2.10.1 -r requirements.lock --strict --no-deps --disable-pip --format json --output artifacts/qa-new-run/runtime-audit.json
```

Python 런타임·requirements.lock·requirements-browser.lock·Chromium·ffmpeg·openssl이 필요하다. 출력은 새 디렉터리만 허용하고 단계별 로그·종료코드를 남긴다. 단계 제한 300초이며 시간 초과 시 테스트 자식 프로세스도 종료한다. 테스트는 현재 Codex 클라우드 작업환경에서 실행했다.

## 아직 검증하지 않은 부분

실제 국내 PC/휴대폰, Safari/iOS, 운영 TLS·백업 복구, 실제 모델 동시 추론의 메모리·속도, 장시간 내구성, 실제 개의 행동 원인·감정·의도 정확도는 별도 검증이 필요하다. 브라우저의 분석 작업자는 모의 모델이다. API·GUI 테스트 성공을 행동 정확도나 출시 준비 완료로 환산하지 않는다. AX 로그인·유료 API·고객자료 외부전송·배포는 실행하지 않았다.
