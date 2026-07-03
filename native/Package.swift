// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "CupGuard",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "CupGuard", targets: ["CupGuard"]),
    ],
    targets: [
        .executableTarget(
            name: "CupGuard",
            path: "Sources/CupGuard"
        ),
    ]
)
