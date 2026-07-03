import AppKit
import CoreGraphics

@MainActor
final class OverlayWindowController: NSWindowController {
    private let engine = MonitorEngine()
    private var refreshTimer: Timer?

    private let statusLabel = NSTextField(labelWithString: "WAITING")
    private let messageLabel = NSTextField(wrappingLabelWithString: "Starting…")
    private let previewView = NSImageView()
    private let redLabel = NSTextField(labelWithString: "red_frac: —")
    private let excessLabel = NSTextField(labelWithString: "red_excess: —")
    private let meanLabel = NSTextField(labelWithString: "mean R: —")
    private let countLabel = NSTextField(labelWithString: "E: 0   Q: 0")
    private let screenPermLabel = NSTextField(labelWithString: "Screen Recording")
    private let inputPermLabel = NSTextField(labelWithString: "Input Monitoring")
    private let accessPermLabel = NSTextField(labelWithString: "Accessibility")
    private let monitorSwitch = NSSwitch()
    private let autoESwitch = NSSwitch()
    private let autoQSwitch = NSSwitch()
    private let sensitivitySlider = NSSlider(value: 0.52, minValue: 0.35, maxValue: 0.75, target: nil, action: nil)
    private let sensitivityValueLabel = NSTextField(labelWithString: "0.52")

    func showWindow() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 300, height: 580),
            styleMask: [.titled, .closable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.title = "Cup Guard"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.isMovableByWindowBackground = true
        window.level = .floating
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        window.contentView = buildContent()
        placeTopRight(window)
        self.window = window
        window.makeKeyAndOrderFront(nil)

        wireActions()
        engine.refreshPermissions()
        engine.startPermissionPolling()
        refreshUI()

        refreshTimer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refreshUI() }
        }

        // Never touch TCC APIs during launch — wait until the window is up.
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { [weak self] in
            self?.engine.startHotkeys()
        }
    }

    func shutdown() {
        refreshTimer?.invalidate()
        engine.shutdown()
    }

    private func buildContent() -> NSView {
        let root = NSView(frame: NSRect(x: 0, y: 0, width: 300, height: 580))

        let title = NSTextField(labelWithString: "Cup Guard")
        title.font = .boldSystemFont(ofSize: 18)
        statusLabel.font = .boldSystemFont(ofSize: 11)
        messageLabel.font = .systemFont(ofSize: 11)
        messageLabel.textColor = .secondaryLabelColor
        messageLabel.maximumNumberOfLines = 0

        previewView.imageScaling = .scaleProportionallyUpOrDown
        previewView.wantsLayer = true
        previewView.layer?.backgroundColor = NSColor(white: 0.1, alpha: 1).cgColor
        previewView.layer?.cornerRadius = 8

        let permBox = NSBox()
        permBox.title = "Permissions"
        permBox.boxType = .primary
        let permStack = NSStackView(views: [
            permRow(label: screenPermLabel, tag: 1),
            permRow(label: inputPermLabel, tag: 2),
            permRow(label: accessPermLabel, tag: 3),
            makeButton("Request all permissions", action: #selector(requestAllPermissions)),
        ])
        permStack.orientation = .vertical
        permStack.alignment = .leading
        permStack.spacing = 6
        permBox.contentView = permStack

        let sensLabel = NSTextField(labelWithString: "Sensitivity")
        sensitivitySlider.numberOfTickMarks = 41
        sensitivitySlider.allowsTickMarkValuesOnly = false

        monitorSwitch.state = .off
        autoESwitch.state = .on
        autoQSwitch.state = .on

        let stack = NSStackView(views: [
            row(title, statusLabel),
            permBox,
            previewView,
            redLabel, excessLabel, meanLabel, countLabel,
            switchRow("Monitoring", monitorSwitch),
            switchRow("Auto-press E", autoESwitch),
            switchRow("Auto-press Q after E", autoQSwitch),
            sensLabel,
            sensitivitySlider,
            sensitivityValueLabel,
            makeButton("Arm (0)", action: #selector(arm)),
            buttonsRow(
                makeButton("E", action: #selector(pressE)),
                makeButton("Q", action: #selector(pressQ))
            ),
            makeButton("Need help?", action: #selector(showHelp)),
            messageLabel,
        ])
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 8
        stack.translatesAutoresizingMaskIntoConstraints = false
        root.addSubview(stack)

        previewView.heightAnchor.constraint(equalToConstant: 140).isActive = true
        previewView.widthAnchor.constraint(equalToConstant: 268).isActive = true
        sensitivitySlider.widthAnchor.constraint(equalToConstant: 268).isActive = true
        permBox.widthAnchor.constraint(equalToConstant: 268).isActive = true
        messageLabel.widthAnchor.constraint(lessThanOrEqualToConstant: 268).isActive = true

        NSLayoutConstraint.activate([
            stack.topAnchor.constraint(equalTo: root.topAnchor, constant: 14),
            stack.leadingAnchor.constraint(equalTo: root.leadingAnchor, constant: 14),
            stack.trailingAnchor.constraint(equalTo: root.trailingAnchor, constant: -14),
        ])
        return root
    }

    private func wireActions() {
        monitorSwitch.target = self
        monitorSwitch.action = #selector(monitorChanged)
        autoESwitch.target = self
        autoESwitch.action = #selector(autoEChanged)
        autoQSwitch.target = self
        autoQSwitch.action = #selector(autoQChanged)
        sensitivitySlider.target = self
        sensitivitySlider.action = #selector(sensitivityChanged)
    }

    private func refreshUI() {
        updateStatusPill()
        redLabel.stringValue = String(format: "red_frac: %.2f", engine.redFrac)
        excessLabel.stringValue = String(format: "red_excess: %.1f", engine.redExcess)
        meanLabel.stringValue = String(format: "mean R: %.0f", engine.meanR)
        countLabel.stringValue = "E: \(engine.ePresses)   Q: \(engine.qPresses)"
        messageLabel.stringValue = engine.message
        sensitivityValueLabel.stringValue = String(format: "%.2f", engine.sensitivity)
        monitorSwitch.state = engine.monitoring ? .on : .off
        autoESwitch.state = engine.autoE ? .on : .off
        autoQSwitch.state = engine.autoQ ? .on : .off
        if abs(sensitivitySlider.doubleValue - engine.sensitivity) > 0.01 {
            sensitivitySlider.doubleValue = engine.sensitivity
        }

        updatePermLabel(screenPermLabel, title: "Screen Recording", ok: engine.hasScreenRecording)
        updatePermLabel(inputPermLabel, title: "Input Monitoring", ok: engine.hasInputMonitoring)
        updatePermLabel(accessPermLabel, title: "Accessibility", ok: engine.hasAccessibility)

        if let cgImage = engine.previewImage {
            previewView.image = NSImage(cgImage: cgImage, size: NSSize(width: cgImage.width, height: cgImage.height))
        } else {
            previewView.image = nil
        }
    }

    private func updateStatusPill() {
        let text: String
        if engine.blocked { text = "BLOCKED" }
        else if !engine.armed { text = "WAITING" }
        else if engine.cupOnTable { text = "CUP ON" }
        else { text = "CUP GONE" }
        statusLabel.stringValue = text
    }

    private func updatePermLabel(_ label: NSTextField, title: String, ok: Bool) {
        label.stringValue = "\(ok ? "✓" : "✗") \(title)"
    }

    private func placeTopRight(_ window: NSWindow) {
        guard let screen = NSScreen.main else { return }
        let frame = screen.visibleFrame
        let size = window.frame.size
        window.setFrameOrigin(NSPoint(x: frame.maxX - size.width - 16, y: frame.maxY - size.height - 16))
    }

    @objc private func arm() {
        if engine.calibrateNow() { engine.setMonitoring(true) }
    }

    @objc private func pressE() { engine.manualPressE() }
    @objc private func pressQ() { engine.manualPressQ() }

    @objc private func monitorChanged() {
        engine.setMonitoring(monitorSwitch.state == .on)
    }

    @objc private func autoEChanged() {
        engine.autoE = autoESwitch.state == .on
    }

    @objc private func autoQChanged() {
        engine.autoQ = autoQSwitch.state == .on
    }

    @objc private func sensitivityChanged() {
        engine.sensitivity = sensitivitySlider.doubleValue
    }

    @objc private func requestAllPermissions() {
        engine.requestPermissions()
    }

    @objc private func showHelp() {
        let alert = NSAlert()
        alert.messageText = "How to calibrate"
        alert.informativeText = """
        Put your mouse on the bottom rim of the red cup and press 0.

        Enable Screen Recording, Input Monitoring, and Accessibility for Cup Guard in System Settings.

        If Screen Time is on, a parent may need to allow Cup Guard under Screen Time → Content & Privacy Restrictions.
        """
        alert.runModal()
    }

    @objc private func allowPermission(_ sender: NSButton) {
        switch sender.tag {
        case 1:
            Permissions.requestScreenRecording()
            SystemSettings.openScreenRecording()
        case 2:
            Permissions.requestInputMonitoring()
            SystemSettings.openInputMonitoring()
        case 3:
            Permissions.requestAccessibility()
            SystemSettings.openAccessibility()
        default: break
        }
        engine.refreshPermissions()
    }

    private func makeButton(_ title: String, action: Selector) -> NSButton {
        let button = NSButton(title: title, target: self, action: action)
        button.bezelStyle = .rounded
        return button
    }

    private func row(_ left: NSView, _ right: NSView) -> NSStackView {
        let stack = NSStackView(views: [left, right])
        stack.orientation = .horizontal
        stack.distribution = .fillEqually
        return stack
    }

    private func switchRow(_ title: String, _ toggle: NSSwitch) -> NSStackView {
        NSStackView(views: [NSTextField(labelWithString: title), toggle])
    }

    private func buttonsRow(_ buttons: NSButton...) -> NSStackView {
        NSStackView(views: buttons)
    }

    private func permRow(label: NSTextField, tag: Int) -> NSStackView {
        let allow = NSButton(title: "Allow", target: self, action: #selector(allowPermission(_:)))
        allow.tag = tag
        allow.bezelStyle = .inline
        let stack = NSStackView(views: [label, allow])
        stack.orientation = .horizontal
        stack.distribution = .fillEqually
        return stack
    }
}
