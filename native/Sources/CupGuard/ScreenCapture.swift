import CoreGraphics
import Foundation

struct CapturedPatch {
    let pixels: [UInt8]
    let width: Int
    let height: Int
}

enum ScreenCapture {
    @discardableResult
    static func probeAccess() -> Bool {
        _ = grab(region: CGRect(x: 0, y: 0, width: 8, height: 8))
        return CGPreflightScreenCaptureAccess()
    }

    static func grabIsBlocked(region: CGRect) -> Bool {
        guard let capture = grab(region: region) else { return true }
        return CupDetection.captureIsBlocked(capture.pixels)
    }

    static func grab(region: CGRect) -> CapturedPatch? {
        guard let image = CGWindowListCreateImage(
            region,
            .optionOnScreenOnly,
            kCGNullWindowID,
            [.bestResolution]
        ) else { return nil }

        return rgbaBytes(from: image)
    }

    static func previewImage(config: Config) -> CGImage? {
        let region = CupDetection.previewRegion(config: config)
        guard let image = CGWindowListCreateImage(
            region,
            .optionOnScreenOnly,
            kCGNullWindowID,
            [.bestResolution]
        ) else { return nil }

        let monitor = CupDetection.monitorRegion(config: config)
        let box = CGRect(
            x: monitor.origin.x - region.origin.x,
            y: monitor.origin.y - region.origin.y,
            width: monitor.width,
            height: monitor.height
        )
        return drawGreenBox(on: image, box: box)
    }

    private static func rgbaBytes(from image: CGImage) -> CapturedPatch? {
        let width = image.width
        let height = image.height
        let bytesPerRow = width * 4
        var pixels = [UInt8](repeating: 0, count: width * height * 4)

        guard let context = CGContext(
            data: &pixels,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: bytesPerRow,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }

        context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        return CapturedPatch(pixels: pixels, width: width, height: height)
    }

    private static func drawGreenBox(on image: CGImage, box: CGRect) -> CGImage? {
        let width = image.width
        let height = image.height
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return image }

        context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        context.setStrokeColor(CGColor(red: 0, green: 1, blue: 0.31, alpha: 1))
        context.setLineWidth(2)
        context.stroke(box)
        return context.makeImage()
    }
}
