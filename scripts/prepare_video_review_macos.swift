import AppKit
import AVFoundation
import CoreMedia
import Foundation
import Vision

func fail(_ message: String, hint: String? = nil) -> Never {
    FileHandle.standardError.write(Data("ERROR: \(message)\n".utf8))
    if let hint {
        FileHandle.standardError.write(Data("HINT: \(hint)\n".utf8))
    }
    exit(2)
}

func timestamp(_ seconds: Double) -> String {
    let milliseconds = Int((max(0, seconds) * 1000).rounded())
    let hours = milliseconds / 3_600_000
    let minutes = (milliseconds % 3_600_000) / 60_000
    let secs = (milliseconds % 60_000) / 1000
    let millis = milliseconds % 1000
    return String(format: "%02d-%02d-%02d.%03d", hours, minutes, secs, millis)
}

func jpegData(_ image: CGImage) -> Data? {
    let representation = NSBitmapImageRep(cgImage: image)
    return representation.representation(using: .jpeg, properties: [.compressionFactor: 0.9])
}

func featurePrint(_ image: CGImage) throws -> VNFeaturePrintObservation {
    let request = VNGenerateImageFeaturePrintRequest()
    try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    guard let result = request.results?.first as? VNFeaturePrintObservation else {
        throw NSError(domain: "DailyShotVideoReview", code: 1)
    }
    return result
}

guard CommandLine.arguments.count >= 4 else {
    fail("Usage: swift prepare_video_review_macos.swift <video> <output> <max-frames>")
}

let source = URL(fileURLWithPath: CommandLine.arguments[1]).standardizedFileURL
let output = URL(fileURLWithPath: CommandLine.arguments[2]).standardizedFileURL
guard FileManager.default.fileExists(atPath: source.path) else {
    fail("Video not found: \(source.path)")
}
guard let maxFrames = Int(CommandLine.arguments[3]), maxFrames >= 2 else {
    fail("max-frames must be at least 2")
}

let asset = AVURLAsset(url: source)
let duration = CMTimeGetSeconds(asset.duration)
guard duration.isFinite && duration > 0 else {
    fail("Could not read a valid video duration.")
}

let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true
generator.requestedTimeToleranceBefore = CMTime(seconds: 0.08, preferredTimescale: 600)
generator.requestedTimeToleranceAfter = CMTime(seconds: 0.08, preferredTimescale: 600)
generator.maximumSize = CGSize(width: 1920, height: 1080)

let intervalDirectory = output.appendingPathComponent("interval", isDirectory: true)
let sceneDirectory = output.appendingPathComponent("scenes", isDirectory: true)
do {
    try FileManager.default.createDirectory(at: intervalDirectory, withIntermediateDirectories: true)
    try FileManager.default.createDirectory(at: sceneDirectory, withIntermediateDirectories: true)
} catch {
    fail("Could not create output folders: \(error.localizedDescription)")
}

let intervalCount = min(maxFrames, max(2, Int(ceil(duration / 3.0)) + 1))
var intervalFrames: [[String: Any]] = []
for index in 0..<intervalCount {
    let requested = duration * Double(index) / Double(intervalCount - 1)
    let safeTime = min(requested, max(0, duration - 0.05))
    var actual = CMTime.zero
    do {
        let image = try generator.copyCGImage(
            at: CMTime(seconds: safeTime, preferredTimescale: 600), actualTime: &actual
        )
        let actualSeconds = CMTimeGetSeconds(actual)
        let filename = String(format: "%03d_%@.jpg", index + 1, timestamp(actualSeconds))
        let destination = intervalDirectory.appendingPathComponent(filename)
        guard let data = jpegData(image) else { throw NSError(domain: "JPEG", code: 1) }
        try data.write(to: destination)
        intervalFrames.append(["time_seconds": actualSeconds, "file": destination.path])
    } catch {
        fail("Could not extract interval frame at \(safeTime)s: \(error.localizedDescription)")
    }
}

var sceneFrames: [[String: Any]] = []
var previousFeature: VNFeaturePrintObservation?
var lastSavedTime = -10.0
let sampleStep = max(0.5, duration / 300.0)
let featureThreshold: Float = 0.48
var sampleTime = 0.0
var sceneIndex = 1

while sampleTime < duration {
    var actual = CMTime.zero
    do {
        let image = try generator.copyCGImage(
            at: CMTime(seconds: sampleTime, preferredTimescale: 600), actualTime: &actual
        )
        let actualSeconds = CMTimeGetSeconds(actual)
        let currentFeature = try featurePrint(image)
        var shouldSave = previousFeature == nil
        if let previousFeature {
            var distance: Float = 0
            try currentFeature.computeDistance(&distance, to: previousFeature)
            shouldSave = distance >= featureThreshold && actualSeconds - lastSavedTime >= 0.35
        }
        if shouldSave {
            let filename = String(format: "%03d_%@.jpg", sceneIndex, timestamp(actualSeconds))
            let destination = sceneDirectory.appendingPathComponent(filename)
            if let data = jpegData(image) {
                try data.write(to: destination)
                sceneFrames.append(["time_seconds": actualSeconds, "file": destination.path])
                sceneIndex += 1
                lastSavedTime = actualSeconds
            }
        }
        previousFeature = currentFeature
    } catch {
        FileHandle.standardError.write(Data("WARNING: Scene sample failed at \(sampleTime)s\n".utf8))
    }
    sampleTime += sampleStep
}

let manifest: [String: Any] = [
    "source": source.path,
    "duration_seconds": duration,
    "interval_frames": intervalFrames,
    "scene_frames": sceneFrames,
    "audio_file": NSNull(),
    "engine": "macOS AVFoundation + Vision",
    "limitations": [
        "Interval frames summarize the timeline but do not prove motion continuity.",
        "Vision-based scene detection is approximate and can miss subtle cuts.",
        "The macOS fallback does not extract audio."
    ]
]

do {
    let data = try JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: output.appendingPathComponent("manifest.json"))
} catch {
    fail("Could not write manifest: \(error.localizedDescription)")
}

print("PREPARE VIDEO REVIEW: SUCCESS")
print("Engine: macOS AVFoundation + Vision")
print("Source: \(source.path)")
print(String(format: "Duration: %.3fs", duration))
print("Interval frames: \(intervalFrames.count)")
print("Scene frames: \(sceneFrames.count)")
print("Output: \(output.path)")
