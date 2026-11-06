# Research

- Decision: Flutter stable3.47.9, 공식 태그/브랜치 c197ca5199e9ee5661e865596c9c07294dfab51c.
  Rationale: 기존 아키텍처와 일치하고 한 소스로 Android/iOS 구현. 공식 SDK 메타데이터 URL404 때문에 Git stable로 설치해 실제 버전을 기록.
  Alternatives: 웹뷰는 휴대폰→localhost 접근과 녹음 권한·오프라인 문제를 해결하지 못한다. Kotlin/Swift 두 앱은 중복 구현이 크다.
- Decision: 앱 내부 JSON 파일·원자 교체, path_provider; 메모리 녹음 record.
  Rationale: 소규모(프로필20/기록100) 일지에 별도 DB/클라우드가 필요 없다. 토큰·소리는 저장하지 않는다.
- Decision: 기존 POST /v1/audio/events에 선택적 HTTPS 개발 연결.
  Rationale: 기존 계약은 16kHz PCM16 WAV, X-Audio-Consent/Species와 Bearer 인증을 사용한다. 기본 AST=false인 Windows localhost 서버를 휴대폰용 운영 서버처럼 말하지 않는다.
- Decision: Android 테스트 APK를 먼저 제공, iOS 공통 소스·네이티브 설정 포함.
  Rationale: [공식 Android 빌드](https://docs.flutter.dev/deployment/android)는 Windows에서 가능하지만
  [iOS 빌드](https://docs.flutter.dev/deployment/ios)는 macOS·Xcode·서명이 필요하다.
- Sources: [Android setup](https://docs.flutter.dev/platform-integration/android/setup),
  [JDK](https://developer.android.com/build/jdks), [record](https://pub.dev/packages/record),
  [path_provider](https://pub.dev/packages/path_provider), [SDK tools](https://developer.android.com/studio#command-tools).

연구는 Spec Kit plan 지시에 따라 읽기 전용 조사 에이전트로 병행했고 실제 파일/API와 공식 문서를 대조했다.
