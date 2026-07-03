import AppKit
import CoreGraphics
import Foundation

final class MonitorEngine {
    var armed = false
    var monitoring = false
    var blocked = false
    var cupOnTable = false
    var cupGone = false
    var redFrac = 0.0
    var redExcess = 0.0
    var meanR = 0.0
    var ePresses = 0
    var qPresses = 0
    var message = "Hover over the bottom rim of the cup and press 0"
    var previewImage: CGImage?
    var autoE = true
    var autoQ = true
    var sensitivity = 0.52
    var hasScreenRecording = false
    var hasInputMonitoring = false
    var hasAccessibility = false

    private var config: Config?
    private var monitorTimer: Timer?
    private var permissionTimer: Timer?
    private var hotkeyListener: ZeroHotkeyListener?
    private var grabTimer: Timer?

    private var cupPresent = true
    private var missingFrames = 0
    private var lastPress: TimeInterval = 0
    private var presses = 0

    func requestPermissions() {
        Permissions.requestAll()
        refreshPermissions()
    }

    func refreshPermissions() {
        hasScreenRecording = Permissions.hasScreenRecording
        hasInputMonitoring = Permissions.hasInputMonitoring
        hasAccessibility = Permissions.hasAccessibility

        if !hasScreenRecording {
            message = "Allow Screen Recording for Cup Guard in System Settings"
        } else if !hasInputMonitoring {
            message = "Allow Input Monitoring for Cup Guard (needed for 0 hotkey)"
        } else if !hasAccessibility {
            message = "Allow Accessibility for Cup Guard (needed for E/Q keys)"
        } else if !armed {
            message = "Hover over the bottom rim of the cup and press 0"
        }
    }

    func startPermissionPolling() {
        refreshPermissions()
        permissionTimer?.invalidate()
        permissionTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.refreshPermissions()
        }
    }

    func stopPermissionPolling() {
        permissionTimer?.invalidate()
        permissionTimer = nil
    }

    func startHotkeys() {
        guard hotkeyListener == nil else { return }
        hotkeyListener = ZeroHotkeyListener { [weak self] in
            DispatchQueue.main.async { self?.calibrateNow() }
        }
        hotkeyListener?.start()
    }

    func shutdown() {
        stopMonitoring()
        stopPermissionPolling()
        hotkeyListener?.stop()
        hotkeyListener = nil
        cancelPendingGrab()
    }

    func setMonitoring(_ enabled: Bool) {
        if enabled {
            guard config?.baseline != nil else {
                message = "Hover over the bottom rim of the cup and press 0"
                return
            }
            startMonitorLoop()
        } else {
            stopMonitoring()
            message = "Monitoring paused — press 0 to reposition"
        }
    }

    @discardableResult
    func calibrateNow() -> Bool {
        stopMonitoring()
        cancelPendingGrab()

        if !Permissions.hasScreenRecording {
            _ = Permissions.requestScreenRecording()
            refreshPermissions()
            message = "Allow Screen Recording, then press 0 again"
            SystemSettings.openScreenRecording()
            return false
        }

        guard let newConfig = CupDetection.calibrateFromCursor(sensitivity: sensitivity) else {
            armed = false
            monitoring = false
            previewImage = nil
            message = "No red detected — hover cup rim and press 0"
            return false
        }

        config = newConfig
        armed = true
        monitoring = true
        blocked = false
        cupOnTable = false
        cupGone = false
        sensitivity = newConfig.sensitivity
        message = "Calibrated — press 0 anytime to reposition"
        cupPresent = true
        missingFrames = 0
        startMonitorLoop()
        return true
    }

    func manualPressE() {
        KeyPress.pressE()
        ePresses += 1
        message = "Manual E (#\(ePresses))"
    }

    func manualPressQ() {
        KeyPress.pressQ()
        qPresses += 1
        message = "Manual Q (#\(qPresses))"
    }

    private func startMonitorLoop() {
        monitoring = true
        monitorTimer?.invalidate()
        monitorTimer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            self?.tick()
        }
    }

    private func stopMonitoring() {
        monitoring = false
        monitorTimer?.invalidate()
        monitorTimer = nil
    }

    private func cancelPendingGrab() {
        grabTimer?.invalidate()
        grabTimer = nil
    }

    private func scheduleRandomGrab() {
        guard autoQ else { return }
        cancelPendingGrab()
        let delay = Double.random(in: CupConstants.grabQMinDelay...CupConstants.grabQMaxDelay)
        grabTimer = Timer.scheduledTimer(withTimeInterval: delay, repeats: false) { [weak self] _ in
            guard let self else { return }
            KeyPress.pressQ()
            self.qPresses += 1
            self.message = "Q in \(String(format: "%.1f", delay))s → pressed (#\(self.qPresses))"
        }
        message = "Q in \(String(format: "%.1f", delay))s…"
    }

    private func tick() {
        guard var config, let baseline = config.baseline else { return }
        config.sensitivity = sensitivity
        self.config = config

        let region = CupDetection.monitorRegion(config: config)
        guard let capture = ScreenCapture.grab(region: region) else {
            blocked = true
            message = "Screen capture failed — check Screen Recording permission"
            return
        }

        if CupDetection.captureIsBlocked(capture.pixels) {
            blocked = true
            cupOnTable = false
            cupGone = false
            previewImage = ScreenCapture.previewImage(config: config)
            message = "Screen capture blocked — check permissions"
            return
        }

        let metrics = CupDetection.analyzePatch(
            capture.pixels,
            width: capture.width,
            height: capture.height
        )
        redFrac = metrics.redFrac
        redExcess = metrics.redExcess
        meanR = metrics.meanR
        previewImage = ScreenCapture.previewImage(config: config)
        blocked = false

        let present = CupDetection.cupIsPresent(
            redFrac: metrics.redFrac,
            baseline: baseline,
            sensitivity: config.sensitivity
        )
        let gone = CupDetection.cupIsGone(
            redFrac: metrics.redFrac,
            baseline: baseline,
            sensitivity: config.sensitivity,
            goneBoost: config.goneBoost
        )

        if present && !gone {
            cupPresent = true
            missingFrames = 0
            cupOnTable = true
            cupGone = false
            return
        }

        missingFrames += 1

        if autoE && cupPresent && gone && missingFrames >= config.confirmFrames {
            let now = ProcessInfo.processInfo.systemUptime
            if now - lastPress >= config.cooldownS {
                KeyPress.pressE()
                scheduleRandomGrab()
                lastPress = now
                presses += 1
                ePresses = presses
                message = "E pressed (#\(presses))"
            }
            cupPresent = false
            cupOnTable = false
            cupGone = true
            return
        }

        if gone && missingFrames >= config.confirmFrames {
            cupPresent = false
            cupOnTable = false
            cupGone = true
            return
        }

        cupOnTable = present && !gone
        cupGone = gone
    }
}
