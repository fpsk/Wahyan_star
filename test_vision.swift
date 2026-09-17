import Foundation
import Vision
import AppKit

func testFaces(path: String) {
    guard let img = NSImage(contentsOfFile: path),
          let cgImg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("Failed to load image")
        return
    }
    
    // Test 0 deg
    let req0 = VNDetectFaceRectanglesRequest()
    let h0 = VNImageRequestHandler(cgImage: cgImg, options: [:])
    try? h0.perform([req0])
    let faces0 = (req0.results as? [VNFaceObservation])?.count ?? 0
    
    // Test 180 deg
    let req180 = VNDetectFaceRectanglesRequest()
    let h180 = VNImageRequestHandler(cgImage: cgImg, orientation: .down, options: [:])
    try? h180.perform([req180])
    let faces180 = (req180.results as? [VNFaceObservation])?.count ?? 0
    
    print("\(path) -> Faces @ 0 deg: \(faces0), Faces @ 180 deg: \(faces180)")
}

testFaces(path: "okf_output/photos/1971_page_070_photo_1.png")
testFaces(path: "okf_output/photos/1971_page_070_full.png")
testFaces(path: "okf_output/photos/1971_page_071_photo_2.png")
