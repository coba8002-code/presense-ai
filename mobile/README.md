# PetSense 모바일 베타 0.1.0

Android·iPhone 공통 Flutter 앱. 서버 없이 개 프로필과 보호자 상황 기록을 사용한다.
기존 웹/서버 코드를 바꾸지 않는다. 개 전용이며 감정 번역·수의 진단·검증된 행동 정확도를 제공하지 않는다.

## 지금 되는 기능

- 개 이름 최대20개, 관찰 노트 최대100개·30일: 직접 관찰/가설/이후 결과를 구분한다.
- 명시적 저장 동의·재시작 조회·개별 삭제·프로필 연결 기록 삭제·전체 초기화.
- 한국어/영어. 원본 음성과 인증 정보는 저장하지 않는다. OS 자동 백업/기기 이전 제외.
- 최대10초16kHz PCM16 메모리 녹음. 취소·앱을 벗어나면 지우며 자동 업로드하지 않는다.
- 사용자가 준비한 HTTPS 개발 서버의 기존 `/v1/audio/events`로 별도 동의 후 단일 분석 요청.
  사건 점수만 표시하고 감정·의도·원인 판단은 보류한다. 결과는 저장하지 않는다.

휴대폰의 마이크/실기기·절전/통화 중단은 기기별 인수가 필요하다. 시뮬레이션 검사는 이를 대체하지 않는다.
기록은 앱을 열거나 바꿀 때 만료를 정리한다. 휴대폰 전원이 꺼진 동안 예약 삭제를 보장하지 않는다.
앱 삭제/초기화 시 로컬 기록은 복구할 수 없고 다른 기기로 자동 복원하지 않는다.

## Android 설치

Android7.0(API24) 이상. `PetSense-Android-0.1.0-beta.apk`를 휴대폰에 내려받아 연다.
필요하면 파일을 연 앱에 대한 '알 수 없는 앱 설치'만 허용한 뒤 설치한다. 설치 뒤 그 허용을 다시 끌 수 있다.
첫 실행에 네트워크나 계정이 없어도 설정→개 이름→관찰 노트 저장을 사용할 수 있다.
마이크 권한은 녹음 버튼을 누를 때 요청한다.

이 APK는 테스트 키로 서명한 개발 베타다. Google Play 정식 배포·향후 서명 키 호환성을 보장하지 않는다.
추가 설치 파일을 Windows EXE로 실행하는 것이 아니라 Android에서 APK로 설치한다.

## 소리 서버 연결

기본 연결은 없다. Windows 설치 파일의 localhost:8765는 휴대폰에서 바로 연결할 수 없고 AST도 기본 꺼져 있다.
임의로 서버를 공개하거나 모델을 내려받지 않는다. 별도로 준비한 HTTPS 개발 서버와 임시 Bearer 토큰이 필요하다.
소리 탭에서 HTTPS origin만 입력한다. 경로·쿼리·사용자 정보를 넣지 않는다.
주소를 바꾸면 토큰·동의를 지운다. 토큰은 저장하지 않으며 화면 이동/백그라운드/취소 때 지운다.
개 소리 확인과 해당 주소 전송 동의를 모두 켠 뒤 분석 버튼을 눌러야 전송한다.
서버가 미준비이면 그 사실을 표시한다. 모델·회원 계정/동기화·카카오톡·영상·유료 API를 자동 활성화하지 않는다.

## 개발/검사

Flutter3.47.9/Dart3.13.7, Android 템플릿 AGP9.1.0/Gradle9.3.1, JDK17, SDK36/NDK28.2.13676358.

```sh
flutter pub get --enforce-lockfile
flutter analyze
flutter test
flutter build apk --release
```

Android 통합 검사는 호스트 오디오를 끈 전용 가상기기에서 실행한다. Flutter 테스트는 기본적으로 종료 후 앱과 권한을 지운다.
먼저 동일한 테스트 APK를 설치하고 권한을 부여한 뒤 유지 옵션으로 실행한다. 실제 사용자 앱 자료가 있는 기기에 테스트하지 않는다.

```sh
flutter build apk --debug -t integration_test/offline_test.dart
adb -s emulator-5580 install -r -t -g build/app/outputs/flutter-apk/app-debug.apk
adb -s emulator-5580 shell pm grant com.petsense.petsense_mobile android.permission.RECORD_AUDIO
flutter test integration_test/offline_test.dart -d emulator-5580 --no-uninstall
```

가상기기의 무음 입력으로 네이티브 녹음·중단·메모리 삭제를 확인한다. 실제 개의 녹음·행동 정확도 검사가 아니다.

루트의 `scripts/build_mobile.ps1`은 검사·APK·소스/배포ZIP·해시를 만든다.
테스트 키/SDK/가상기기·캐시·개인 기록·인증 정보는 소스ZIP에 넣지 않는다.

## iPhone 빌드 준비

iOS15 이상 프로젝트가 포함돼 있다. 이 Windows 환경에서 설치용 IPA는 만들지 않았다.
Mac·Xcode·서명 준비 후 이 폴더에서 `bash scripts/build_ios.sh --simulator`로 먼저 검사한다.
Xcode의 `ios/Runner.xcworkspace`를 열고 본인 개발 팀과 고유 Bundle ID를 설정한다.
현재 기본 Bundle ID는 `com.petsense.petsenseMobile`이며 Apple 등록/소유권을 뜻하지 않는다.
실기기용은 서명 후 `bash scripts/build_ios.sh --ipa`. 서명/프로비저닝과 Apple 개발자 배포 조건을 충족해야 한다.
TestFlight/App Store 업로드·개발자 가입 비용은 자동 실행하지 않는다.

계획과 검사 결과는 `specs/006-mobile-app/`에 있다.
