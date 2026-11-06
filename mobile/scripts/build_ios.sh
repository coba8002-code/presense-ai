#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ $(uname -s) != Darwin ]]; then
  echo 'iOS builds require macOS and Xcode. No IPA was created.' >&2
  exit 2
fi
mode=${1:---simulator}
if [[ $# -gt 1 || ( "$mode" != --simulator && "$mode" != --ipa ) ]]; then
  echo 'Use --simulator or --ipa. Configure your own signing team in Xcode for IPA.' >&2
  exit 2
fi
flutter pub get --enforce-lockfile
flutter analyze
flutter test
if [[ "$mode" == --simulator ]]; then
  flutter build ios --simulator
else
  flutter build ipa
fi
