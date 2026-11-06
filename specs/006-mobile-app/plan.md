# Implementation Plan: Android·iPhone 앱

**Date**: 2026-11-06 | **Spec**: spec.md | 기존 Git 브랜치 유지

## Summary

Flutter로 두 플랫폼 공통 네이티브 화면을 만든다. 기존 웹뷰로 포장하지 않고
오프라인 개 프로필·관찰/가설/후속 결과 일지와 메모리 녹음·선택적 HTTPS 분석을 제공한다.
APK는 현 Windows에서 빌드한다. iOS 프로젝트/권한/빌드 스크립트를 준비하며 Mac/서명 부재를 명시한다.

## Technical Context

- Flutter stable3.47.9 / Dart 포함, Android·iOS 템플릿, Material3.
- Windows 도구는 build/mobile-tools에만 둔다. 실제 도구 버전/해시는 검증 기록에 남긴다.
- Android SDK/JDK는 생성한 Flutter Gradle 템플릿 요구와 맞춘다. APK는 테스트 debug 서명임을 명시한다.
- path_provider: 앱 내부 파일 경로. record: PCM16 stream, native Android/iOS 권한.
- 네트워크는 dart:io HttpClient로 직접 처리한다. 리다이렉트/자동 재시도 금지, 제한된 응답과 전체 timeout/cancel.
- iOS의 소규모 플랫폼 채널로 기록 폴더 백업 제외·파일 보호를 설정한다. Android 백업/cleartext를 끈다.
- 서버 인증은 현재 개발용 Bearer 토큰을 화면 메모리에만 보관한다. 로그인·서버 동기화는 새로 만들지 않는다.

## Constitution Check

PASS: dog-only, guardian_report·hypothesis·verified_follow_up 별도 필드, 모델 결과는 사건 점수/abstain.
실데이터·가중치·유료 API·운영 서버·기존 계정·Windows 설치 프로그램은 변경하지 않는다.
SDK 설치/로컬 서명·APK는 요청된 개발 범위다. 공개 배포·AppStore 계정 생성·게시·Git 변경 없음.
실제 모바일 실기기와 iOS 빌드 미검증을 구분하며 가짜 IPA를 만들지 않는다.

## Project Structure

- mobile/lib/main.dart, app.dart, l10n.dart: 초기화·한/영·세 탭 화면·오류/빈 상태.
- mobile/lib/models.dart, repository.dart: 검증된 프로필/일지·30일 만료·원자 저장·삭제.
- mobile/lib/audio_capture.dart, audio_api.dart: 녹음 메모리 상한/취소·HTTPS 계약/결과 검증.
- mobile/lib/screens/: 기록 작성/목록·개 프로필·녹음/서버 설정.
- mobile/android/, mobile/ios/: 생성 프로젝트, 최소 권한/백업 차단·앱 이름.
- mobile/test/: 저장/재시작·삭제/만료·UI 한/영·녹음 상태·API 취소/실패·입력 검사.
- mobile/integration_test/: 실제 Android 설치 후 오프라인 핵심 흐름.
- scripts/build_mobile.ps1, mobile/scripts/build_ios.sh: 재현 검사/패키징, macOS 전용 iOS 안내.
- releases/: APK·모바일 소스 ZIP·설치 안내·해시/빌드 정보. 키/SDK/캐시 제외.

## Design

프로필20개·기록100개. 각각 입력 상한을 UI와 모델 경계에서 확인한다.
저장 데이터는 schema1, 언어/HTTPS주소, UUID형 로컬 ID, 개 프로필과 기록뿐이다.
음성/토큰/서버 점수는 저장하지 않는다. 임시 파일로 쓰고 같은 디렉터리에서 원자 교체한다.
손상 파일을 빈 파일로 덮어쓰지 않고 읽기 실패 화면을 보여준다. 전체 초기화는 확인 뒤 수행한다.
로컬 기기 시각 기준30일 만료로 앱 열기/변경 시 정리하며 전원 꺼진 기기의 예약 삭제는 보장하지 않는다.

녹음·업로드는 화면 생명주기/동의/작업 세대 번호로 취소하고 오래된 비동기 결과를 버린다.
최대160000 표본·모노16kHz PCM16, 최대320000바이트를 메모리에 보관한다. WAV 헤더는 앱에서 만든다.
권한 응답이 늦게 와도 취소된 녹음을 시작하지 않는다. 소리 분석 기본 꺼짐/HTTPS만/명시적 주소.
서버 요청은 전송 버튼을 누를 때만 하고 녹음은 서버에 자동 전송하지 않는다.
기존 API 입력/결과를 엄격히 확인하고 서버가 없으면 로컬 기록은 계속 쓴다.

## Verification

모델/저장·동의/취소 경계의 실패 검사→최소 구현→Flutter analyze/test→실제 APK 빌드·서명/권한 검사.
가능한 Android 기기/에뮬레이터를 찾고 실제 설치/실행 여부를 기록한다. 없으면 그 검증만 미완료로 남긴다.
기존 Python/JavaScript는 앱 코드와 분리되어 있으므로 기존 서버 수정 없이 필요한 회귀만 실행한다.
iOS 소스와 plist/Xcode 설정을 검사하고 Mac 조건을 문서화한다.

## Complexity Tracking

새 앱 경계만 추가. 상태 관리 프레임워크·분석 SDK·서버/DB 마이그레이션·공개 인증·광고/추적 없음.
