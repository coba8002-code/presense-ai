import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from scripts.package_mobile import allowed, package


class MobilePackageTests(unittest.TestCase):
    def test_machine_state_credentials_and_binaries_excluded(self):
        for name in ('mobile/.dart_tool/cache', 'mobile/android/.gradle/file.lock',
                     'mobile/android/local.properties', 'mobile/key.properties', 'mobile/secrets.jks',
                     'mobile/signing.p12', 'mobile/.env', 'mobile/ios/Flutter/Generated.xcconfig',
                     'mobile/build/app.apk', 'mobile/ios/Pods/code', 'mobile/.idea/workspace.xml'):
            self.assertFalse(allowed(name), name)
        for name in ('mobile/lib/main.dart', 'mobile/pubspec.lock', 'mobile/android/gradlew.bat',
                     'mobile/ios/Runner/AppDelegate.swift', 'mobile/test/app_test.dart'):
            self.assertTrue(allowed(name), name)

    def test_portable_source_and_distribution_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            apk = root/'fixture.apk'
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('AndroidManifest.xml', 'fixture')
                archive.writestr('classes.dex', 'fixture')
            with contextlib.redirect_stdout(io.StringIO()):
                package(apk, root/'output')
            with zipfile.ZipFile(root/'output/PetSense-Mobile-Source-0.1.0.zip') as archive:
                names = set(archive.namelist())
                self.assertIn('mobile/lib/main.dart', names)
                self.assertIn('mobile/ios/Runner.xcodeproj/project.pbxproj', names)
                self.assertIn('mobile/android/gradle/wrapper/gradle-wrapper.jar', names)
                for entry in json.loads(archive.read('source-manifest.json'))['files']:
                    self.assertTrue(allowed(entry['path']))
                    data = archive.read(entry['path'])
                    self.assertEqual(len(data), entry['size'])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), entry['sha256'])
            with zipfile.ZipFile(root/'output/PetSense-Mobile-0.1.0-beta.zip') as archive:
                for line in archive.read('SHA256SUMS-mobile.txt').decode().splitlines():
                    digest, name = line.split('  ', 1)
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)

    def test_non_apk_input_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = root/'invalid.apk'
            invalid.write_bytes(b'not an apk')
            with self.assertRaises(ValueError): package(invalid, root/'output')
