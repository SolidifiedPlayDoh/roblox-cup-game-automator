import ApplicationServices
import CoreGraphics
import Foundation

enum Permissions {
    static var hasAccessibility: Bool {
        AXIsProcessTrusted()
    }

    static var hasInputMonitoring: Bool {
        if #available(macOS 10.15, *) {
            return CGPreflightListenEventAccess()
        }
        return hasAccessibility
    }

    static var hasScreenRecording: Bool {
        CGPreflightScreenCaptureAccess()
    }

    static var isReady: Bool {
        hasScreenRecording && hasInputMonitoring && hasAccessibility
    }

    @discardableResult
    static func requestAccessibility(prompt: Bool = true) -> Bool {
        guard prompt else { return AXIsProcessTrusted() }
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue(): true] as CFDictionary
        return AXIsProcessTrustedWithOptions(options)
    }

    @discardableResult
    static func requestInputMonitoring() -> Bool {
        if #available(macOS 10.15, *) {
            return CGRequestListenEventAccess()
        }
        return requestAccessibility(prompt: true)
    }

    @discardableResult
    static func requestScreenRecording() -> Bool {
        CGRequestScreenCaptureAccess()
    }

    static func requestAll() {
        _ = requestScreenRecording()
        _ = requestInputMonitoring()
        _ = requestAccessibility(prompt: true)
        _ = ScreenCapture.probeAccess()
    }
}
