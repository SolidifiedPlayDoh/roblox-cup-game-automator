import Foundation

struct Baseline: Codable, Equatable {
    var redFrac: Double
    var redExcess: Double
    var meanR: Double

    enum CodingKeys: String, CodingKey {
        case redFrac = "red_frac"
        case redExcess = "red_excess"
        case meanR = "mean_r"
    }
}

struct Config: Codable, Equatable {
    var x: Double
    var y: Double
    var width: Int = 90
    var height: Int = 16
    var scale: Double = 1.0
    var baseline: Baseline?
    var sensitivity: Double = 0.52
    var goneBoost: Double = 0.07
    var confirmFrames: Int = 1
    var cooldownS: Double = 0.12

    enum CodingKeys: String, CodingKey {
        case x, y, width, height, scale, baseline, sensitivity
        case goneBoost = "gone_boost"
        case confirmFrames = "confirm_frames"
        case cooldownS = "cooldown_s"
    }

    static var appSupportDir: URL {
        let base = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/CupGuard", isDirectory: true)
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        return base
    }

    static var configURL: URL { appSupportDir.appendingPathComponent("config.json") }

    static func load() -> Config? {
        guard let data = try? Data(contentsOf: configURL) else { return nil }
        return try? JSONDecoder().decode(Config.self, from: data)
    }

    func save() {
        guard let data = try? JSONEncoder().encode(self) else { return }
        try? data.write(to: Self.configURL, options: .atomic)
    }
}

enum CupConstants {
    static let regionWidth = 90
    static let regionHeight = 16
    static let previewWidth = 160
    static let previewHeight = 96
    static let cursorOffsetY: Double = -12
    static let grabQMinDelay: TimeInterval = 2.5
    static let grabQMaxDelay: TimeInterval = 4.0
}
