import AppKit
import CoreGraphics
import Foundation

struct PatchMetrics {
    let redFrac: Double
    let redExcess: Double
    let meanR: Double
}

enum CupDetection {
    static func samplePoint(cursorX: Double, cursorY: Double) -> (Double, Double) {
        (cursorX, cursorY + CupConstants.cursorOffsetY)
    }

    static func screenScale() -> Double {
        Double(NSScreen.main?.backingScaleFactor ?? 1.0)
    }

    static func toCaptureCoords(x: Double, y: Double, scale: Double) -> (Int, Int) {
        (Int((x * scale).rounded()), Int((y * scale).rounded()))
    }

    static func monitorRegion(config: Config) -> CGRect {
        let (x, y) = toCaptureCoords(x: config.x, y: config.y, scale: config.scale)
        let halfW = config.width / 2
        let halfH = config.height / 2
        return CGRect(
            x: x - halfW,
            y: y - halfH,
            width: config.width,
            height: config.height
        )
    }

    static func previewRegion(config: Config) -> CGRect {
        let (x, y) = toCaptureCoords(x: config.x, y: config.y, scale: config.scale)
        return CGRect(
            x: x - CupConstants.previewWidth / 2,
            y: y - CupConstants.previewHeight / 2,
            width: CupConstants.previewWidth,
            height: CupConstants.previewHeight
        )
    }

    static func analyzePatch(_ pixels: [UInt8], width: Int, height: Int) -> PatchMetrics {
        let count = width * height
        guard count > 0 else { return PatchMetrics(redFrac: 0, redExcess: 0, meanR: 0) }

        var redCount = 0
        var excessSum = 0.0
        var rSum = 0.0

        for i in 0..<count {
            let base = i * 4
            let r = Double(pixels[base])
            let g = Double(pixels[base + 1])
            let b = Double(pixels[base + 2])
            rSum += r
            excessSum += r - max(g, b)
            let brightRed = r > 110 && r > g + 12 && r > b + 12
            let darkRed = r > 80 && r > g + 8 && r > b + 8 && r >= g && r >= b
            if brightRed || darkRed { redCount += 1 }
        }

        let n = Double(count)
        return PatchMetrics(
            redFrac: Double(redCount) / n,
            redExcess: excessSum / n,
            meanR: rSum / n
        )
    }

    static func calibrationIsValid(_ metrics: PatchMetrics) -> Bool {
        if metrics.redFrac >= 0.08 { return true }
        return metrics.meanR >= 120 && metrics.redExcess >= 25
    }

    static func cupIsPresent(redFrac: Double, baseline: Baseline, sensitivity: Double) -> Bool {
        redFrac >= baseline.redFrac * sensitivity
    }

    static func cupIsGone(redFrac: Double, baseline: Baseline, sensitivity: Double, goneBoost: Double) -> Bool {
        redFrac < baseline.redFrac * (sensitivity + goneBoost)
    }

    static func captureIsBlocked(_ pixels: [UInt8]) -> Bool {
        guard !pixels.isEmpty else { return true }
        let pixelCount = pixels.count / 4
        var whiteCount = 0
        var values: [Double] = []
        values.reserveCapacity(pixelCount * 3)

        for i in 0..<pixelCount {
            let base = i * 4
            let r = pixels[base]
            let g = pixels[base + 1]
            let b = pixels[base + 2]
            if r > 250 && g > 250 && b > 250 { whiteCount += 1 }
            values.append(Double(r))
            values.append(Double(g))
            values.append(Double(b))
        }

        if Double(whiteCount) / Double(pixelCount) > 0.85 { return true }

        let mean = values.reduce(0, +) / Double(values.count)
        let variance = values.reduce(0) { $0 + ($1 - mean) * ($1 - mean) } / Double(values.count)
        return variance.squareRoot() < 2.0
    }

    static func detectCaptureScale(logicalX: Double, logicalY: Double) -> Double {
        let retina = screenScale()
        var candidates = [1.0]
        if !candidates.contains(retina) { candidates.append(retina) }

        var bestScale = 1.0
        var bestVariance = -1.0

        for scale in candidates {
            let (capX, capY) = toCaptureCoords(x: logicalX, y: logicalY, scale: scale)
            let region = CGRect(x: capX - 20, y: capY - 20, width: 40, height: 40)
            guard let capture = ScreenCapture.grab(region: region),
                  !captureIsBlocked(capture.pixels) else { continue }

            let floats = capture.pixels.map(Double.init)
            let mean = floats.reduce(0, +) / Double(floats.count)
            let variance = floats.reduce(0) { $0 + ($1 - mean) * ($1 - mean) } / Double(floats.count)
            if variance > bestVariance {
                bestVariance = variance
                bestScale = scale
            }
        }
        return bestScale
    }

    static func calibrateFromCursor(sensitivity: Double) -> Config? {
        let loc = CGEvent(source: nil)?.location ?? .zero
        let cursorX = Double(loc.x)
        let cursorY = Double(loc.y)
        let (sampleX, sampleY) = samplePoint(cursorX: cursorX, cursorY: cursorY)
        let scale = detectCaptureScale(logicalX: sampleX, logicalY: sampleY)

        var config = Config(x: sampleX, y: sampleY, scale: scale, sensitivity: sensitivity)
        let region = monitorRegion(config: config)
        guard let capture = ScreenCapture.grab(region: region),
              !captureIsBlocked(capture.pixels) else { return nil }

        let metrics = analyzePatch(capture.pixels, width: capture.width, height: capture.height)
        guard calibrationIsValid(metrics) else { return nil }

        config.baseline = Baseline(
            redFrac: metrics.redFrac,
            redExcess: metrics.redExcess,
            meanR: metrics.meanR
        )
        config.save()
        return config
    }
}
