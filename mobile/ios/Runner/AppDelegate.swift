import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    guard let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "PetSensePrivacy") else { return }
    let channel = FlutterMethodChannel(name: "com.petsense/privacy", binaryMessenger: registrar.messenger())
    channel.setMethodCallHandler { call, result in
      guard call.method == "protectDirectory", let path = call.arguments as? String else {
        result(FlutterMethodNotImplemented)
        return
      }
      do {
        let support = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        var directory = URL(fileURLWithPath: path).standardizedFileURL.resolvingSymlinksInPath()
        let expected = support.appendingPathComponent("PetSensePrivate").standardizedFileURL.resolvingSymlinksInPath()
        guard directory == expected else {
          result(FlutterError(code: "invalid_directory", message: "Private directory mismatch", details: nil))
          return
        }
        var resources = URLResourceValues()
        resources.isExcludedFromBackup = true
        try directory.setResourceValues(resources)
        try FileManager.default.setAttributes([.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication], ofItemAtPath: directory.path)
        result(nil)
      } catch {
        result(FlutterError(code: "privacy_unavailable", message: "Private storage unavailable", details: nil))
      }
    }
  }
}
