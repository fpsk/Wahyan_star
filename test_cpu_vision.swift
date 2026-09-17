import Foundation
import Vision
import AppKit

guard let img = NSImage(contentsOfFile: "okf_output/photos/1971_page_070_full.png"),
      let cgImg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("Failed to load")
    exit(1)
}

let req = VNRecognizeTextRequest { (request, error) in
    guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
    print("Found lines:", observations.count)
    if let first = observations.first?.topCandidates(1).first {
        print("First line:", first.string)
    }
}
req.usesCPUOnly = true
req.recognitionLevel = .fast

let handler = VNImageRequestHandler(cgImage: cgImg, options: [:])
try? handler.perform([req])
