import Foundation
import Vision
import AppKit

struct OCRLine: Codable {
    let text: String
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

func runOCR(imagePath: String) {
    guard let image = NSImage(contentsOfFile: imagePath),
          let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("[]")
        return
    }

    let requestHandler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    var lines: [OCRLine] = []

    let request = VNRecognizeTextRequest { (request, error) in
        if let error = error {
            return
        }
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            guard let topCandidate = obs.topCandidates(1).first else { continue }
            let bbox = obs.boundingBox
            // bbox.origin.y is normalized 0..1 from bottom-left in Vision
            lines.append(OCRLine(
                text: topCandidate.string,
                x: Double(bbox.origin.x),
                y: Double(bbox.origin.y),
                width: Double(bbox.size.width),
                height: Double(bbox.size.height)
            ))
        }
    }

    request.recognitionLanguages = ["zh-Hant", "en-US"]
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true

    do {
        try requestHandler.perform([request])
    } catch {
        print("[]")
        return
    }

    let encoder = JSONEncoder()
    if let jsonData = try? encoder.encode(lines), let jsonStr = String(data: jsonData, encoding: .utf8) {
        print(jsonStr)
    } else {
        print("[]")
    }
}

let args = CommandLine.arguments
if args.count > 1 {
    runOCR(imagePath: args[1])
} else {
    print("[]")
}
