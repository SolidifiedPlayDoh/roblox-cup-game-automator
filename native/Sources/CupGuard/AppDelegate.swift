import AppKit
import Foundation

enum StartupLog {
    private static var logURL: URL {
        let dir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/CupGuard", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("native.log")
    }

    static func write(_ message: String) {
        let line = "[\(ISO8601DateFormatter().string(from: Date()))] \(message)\n"
        guard let data = line.data(using: .utf8) else { return }
        if FileManager.default.fileExists(atPath: logURL.path) {
            if let handle = try? FileHandle(forWritingTo: logURL) {
                handle.seekToEndOfFile()
                handle.write(data)
                try? handle.close()
            }
        } else {
            try? data.write(to: logURL)
        }
    }
}

@main
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var windowController: OverlayWindowController?

    func applicationDidFinishLaunching(_ notification: Notification) {
        StartupLog.write("applicationDidFinishLaunching")
        NSApp.setActivationPolicy(.regular)

        do {
            windowController = OverlayWindowController()
            windowController?.showWindow()
            NSApp.activate(ignoringOtherApps: true)
            StartupLog.write("window shown")
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        windowController?.shutdown()
        return true
    }
}
