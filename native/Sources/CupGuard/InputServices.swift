import AppKit
import CoreGraphics
import Foundation

enum KeyPress {
    private static let vkE: CGKeyCode = 14
    private static let vkQ: CGKeyCode = 12

    static func pressE() { press(code: vkE) }
    static func pressQ() { press(code: vkQ) }

    private static func press(code: CGKeyCode) {
        let source = CGEventSource(stateID: .hidSystemState)
        let down = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: true)
        let up = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: false)
        down?.post(tap: .cghidEventTap)
        up?.post(tap: .cghidEventTap)
    }
}

private func zeroHotkeyTapCallback(
    _ proxy: CGEventTapProxy,
    _ type: CGEventType,
    _ event: CGEvent,
    _ refcon: UnsafeMutableRawPointer?
) -> Unmanaged<CGEvent>? {
    guard type == .keyDown,
          let refcon else {
        return Unmanaged.passUnretained(event)
    }
    let listener = Unmanaged<ZeroHotkeyListener>.fromOpaque(refcon).takeUnretainedValue()
    let code = CGKeyCode(event.getIntegerValueField(.keyboardEventKeycode))
    if code == 29 || code == 82 {
        listener.handleZeroKey()
    }
    return Unmanaged.passUnretained(event)
}

final class ZeroHotkeyListener {
    private let onZero: () -> Void
    private var thread: Thread?
    private var running = false
    private var runLoop: CFRunLoop?

    init(onZero: @escaping () -> Void) {
        self.onZero = onZero
    }

    func handleZeroKey() {
        onZero()
    }

    func start() {
        guard !running else { return }
        running = true
        thread = Thread { [weak self] in self?.runLoopThread() }
        thread?.name = "zero-hotkey"
        thread?.start()
    }

    func stop() {
        running = false
        if let runLoop {
            CFRunLoopStop(runLoop)
        }
        thread = nil
    }

    private func runLoopThread() {
        let mask = (1 << CGEventType.keyDown.rawValue)
        guard let tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .listenOnly,
            eventsOfInterest: CGEventMask(mask),
            callback: zeroHotkeyTapCallback,
            userInfo: Unmanaged.passUnretained(self).toOpaque()
        ) else {
            running = false
            return
        }

        let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
        runLoop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(runLoop, source, .commonModes)
        CGEvent.tapEnable(tap: tap, enable: true)

        while running {
            let result = CFRunLoopRunInMode(.defaultMode, 0.25, false)
            if result != .timedOut { break }
        }

        CGEvent.tapEnable(tap: tap, enable: false)
        runLoop = nil
    }
}

enum SystemSettings {
    static func openScreenRecording() {
        NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture")!)
    }

    static func openInputMonitoring() {
        NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent")!)
    }

    static func openAccessibility() {
        NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!)
    }
}
