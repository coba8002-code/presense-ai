"""Package the built mobile APK and portable Android/iOS source; exclude local data and keys."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.gradle', '.dart_tool', '.idea', '.kotlin', 'pods', 'build',
            'ephemeral', '.symlinks', '.swiftpm', '.pub-cache', '.pub', 'coverage', '__pycache__'}
NAMES = {'local.properties', 'key.properties', 'generated.xcconfig', 'flutter_export_environment.sh',
         '.flutter-plugins-dependencies', '.last_build_id', 'generatedpluginregistrant.h',
         'generatedpluginregistrant.m', 'generatedpluginregistrant.java'}


def allowed(path):
    path = Path(path)
    return (not any(part.lower() in EXCLUDED for part in path.parts)
            and path.name.lower() not in NAMES
            and path.suffix.lower() not in {'.iml', '.log', '.tmp', '.jks', '.keystore', '.p12',
                                            '.pem', '.key', '.pfx', '.mobileprovision', '.apk', '.ipa',
                                            '.wav', '.mp3', '.m4a', '.mp4', '.db', '.sqlite3', '.xcuserstate'}
            and '.env' not in path.name.lower())


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def package(apk, output):
    apk, output = Path(apk).resolve(), Path(output).resolve()
    if not zipfile.is_zipfile(apk):
        raise ValueError('A real built APK is required')
    with zipfile.ZipFile(apk) as archive:
        if not {'AndroidManifest.xml', 'classes.dex'} <= set(archive.namelist()):
            raise ValueError('APK application entries missing')
    output.mkdir(parents=True, exist_ok=True)
    installed = output/'PetSense-Android-0.1.0-beta.apk'
    installed.write_bytes(apk.read_bytes())
    source = output/'PetSense-Mobile-Source-0.1.0.zip'
    manifest = []
    candidates = list((ROOT/'mobile').rglob('*')) + list((ROOT/'specs/006-mobile-app').rglob('*'))
    candidates += list((ROOT/'.specify').rglob('*'))
    candidates += [ROOT/'AGENTS.md', ROOT/'CONSTRAINTS.md', ROOT/'scripts/build_mobile.ps1', ROOT/'scripts/package_mobile.py']
    with zipfile.ZipFile(source, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(candidates):
            if not path.is_file() or path.is_symlink() or not allowed(path.relative_to(ROOT)):
                continue
            if any(parent.is_symlink() for parent in path.parents if parent != ROOT):
                continue
            name, data = path.relative_to(ROOT).as_posix(), path.read_bytes()
            archive.writestr(name, data)
            manifest.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)})
        archive.writestr('source-manifest.json', json.dumps({'files': manifest}, indent=2))
    readme = output/'모바일-설치안내.txt'
    readme.write_text('PetSense 모바일 베타 0.1.0\n\n'
        'Android: PetSense-Android-0.1.0-beta.apk를 휴대폰에 내려받아 실행합니다.\n'
        'Android 7.0 이상. 테스트 키로 서명한 개발 베타이며 Google Play 배포판이 아닙니다.\n'
        '설정에서 반려견 이름을 등록한 뒤 네트워크 없이 관찰 노트를 저장할 수 있습니다.\n'
        '소리 분석은 별도로 준비한 HTTPS 서버·임시 인증·전송 동의가 있어야 합니다.\n'
        '실제 행동 정확도·감정 번역·수의 진단을 제공하지 않습니다.\n\n'
        'iPhone: 공통 소스와 iOS 프로젝트가 Source ZIP에 있습니다. 설치용 IPA는 포함하지 않습니다.\n'
        'Mac/Xcode와 본인 개발 팀의 서명 준비 후 mobile/README.md 순서로 빌드합니다.\n'
        '실제 기기·iOS 빌드 검증 범위는 소스ZIP의 specs/006-mobile-app/verification.md를 확인하세요.\n', encoding='utf-8')
    sums = output/'SHA256SUMS-mobile.txt'
    sums.write_text(''.join(f'{digest(p)}  {p.name}\n' for p in (installed, source, readme)), encoding='utf-8')
    bundle = output/'PetSense-Mobile-0.1.0-beta.zip'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in (installed, source, readme, sums):
            archive.write(path, path.name)
    report = {'apk': str(installed), 'apk_bytes': installed.stat().st_size,
              'apk_sha256': digest(installed), 'source_files': len(manifest),
              'source_sha256': digest(source), 'bundle_sha256': digest(bundle),
              'signing': 'development_test_key', 'ios_ipa_created': False}
    (output/'mobile-build-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, default=ROOT/'mobile/build/app/outputs/flutter-apk/app-release.apk')
    parser.add_argument('--output', type=Path, default=ROOT/'releases')
    args = parser.parse_args()
    package(args.apk, args.output)
