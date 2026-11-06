# Quickstart

도구: Flutter3.47.9, 템플릿과 맞는 JDK/Android SDK. `cd mobile`, `flutter pub get`, `flutter analyze`, `flutter test`.
Android: `flutter build apk --debug`. `adb install -r build/app/outputs/flutter-apk/app-debug.apk` 후 실행.
앱에서 개 등록→관찰 기록/명시 저장→앱 재시작→조회/삭제, 한/영, 녹음 거절·취소·백그라운드를 확인한다.
소리 분석은 별도 준비된 HTTPS 서버·임시 개발 인증·개 소리/전송 동의가 있어야 가능하다.
기본 Windows localhost 서비스는 휴대폰용 HTTPS 운영 서버가 아니다.

iOS: Mac에서 `flutter pub get`, `flutter build ios --simulator`로 먼저 검사한다.
실기기는 Xcode Runner에서 본인 개발 팀/고유 BundleID를 고른 뒤 서명하고 실행한다.
배포 IPA: `flutter build ipa`와 적절한 signing/export 설정. TestFlight 업로드·비용은 별도 승인한다.
Windows에서 IPA를 만들었다고 하지 않는다. 소리/토큰·개인 기록/키는 소스 묶음에 넣지 않는다.
