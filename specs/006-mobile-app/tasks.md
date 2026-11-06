# Tasks: 모바일 앱

## Foundation

- [x] T001 specs/006-mobile-app/ 에 요구·계획·계약·체크리스트를 작성하고 공식 도구/API를 조사한다. FR-001~009.
- [x] T002 mobile/ 에 Flutter Android/iOS 프로젝트와 고정 의존성·빌드 도구를 준비한다. FR-001/007/008.

## US1 — 오프라인 기록

- [x] T003 [US1] mobile/test/repository_test.dart 에 명시 저장·재시작·삭제·만료·손상 보존·상한 검사를 먼저 작성한다. FR-001/002/003.
- [x] T004 [US1] mobile/lib/models.dart, repository.dart 에 프로필·분리된 관찰/가설/후속 결과와 안전 저장을 구현한다. FR-001/002/003.
- [x] T005 [US1] mobile/lib/app.dart, l10n.dart, screens/ 에 기록·프로필·삭제·한/영·빈/오류 화면을 구현하고 mobile/test/app_test.dart 로 검사한다. FR-001/002/003/006.

## US2 — 소리

- [x] T006 [US2] mobile/test/audio_test.dart, api_test.dart 에 녹음/권한 취소·상한·동의·URL·API 실패/응답·늦은 결과 검사를 먼저 작성한다. FR-004/005/006.
- [x] T007 [US2] mobile/lib/audio_capture.dart, audio_api.dart 에 메모리 녹음·WAV·HTTPS 단일 전송·취소를 구현한다. FR-004/005/006.
- [x] T008 [US2] mobile/lib/screens/sound_screen.dart 에 녹음·동의·서버 미준비·점수/보류 UI와 생명주기 중단을 연결한다. FR-004/005/006.

## US3 — 설치/배포 파일

- [x] T009 [US3] mobile/android/, mobile/ios/ 에 최소 권한·백업/cleartext 차단·이름과 iOS 파일 보호를 설정한다. FR-003/007/008/009.
- [x] T010 [US3] scripts/build_mobile.ps1, mobile/scripts/build_ios.sh 와 mobile/README.md 에 재현 빌드·패키징·아이폰 준비를 만든다. FR-007/008.
- [x] T011 [US3] mobile/integration_test/ 에 핵심 오프라인 흐름을 검증하고 실제 APK 빌드/서명/권한·Android 실행 가능 환경을 확인한다. FR-007/009.

## Validation

- [x] T012 Flutter analyze/test·필요한 회귀를 실행하고 specs/006-mobile-app/verification.md 에 실제 검사·한계·요구 매핑을 기록한다. FR-001~009.
- [x] T013 releases/ 에 APK·모바일 소스 ZIP·안내·SHA256을 제공하고 tasks/todo.md 에 완료/후속을 구분한다. FR-007/008/009.

## Dependencies

T001→T002→T003→T004→T005; T004→T006→T007→T008; T002→T009; T005/008/009→T010→T011→T012→T013.
체크리스트6개 통과. 요구9개 모두 작업과 검사에 연결. 명시적인 후속(회원 동기화·영상·스토어·Mac 서명)은 현재 베타 완료로 처리하지 않는다.
