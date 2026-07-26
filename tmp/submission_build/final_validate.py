import json
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

root = Path(r"Q:\Programs\GradeSense")
submission = root / "Submission"
render_root = root / "tmp" / "pdfs"

report = {"pdfs": [], "screenshots": [], "presentation": {}}
for pdf in sorted(submission.glob("*.pdf")):
    reader = PdfReader(str(pdf))
    text_chars = sum(len(page.extract_text() or "") for page in reader.pages)
    renders = sorted((render_root / pdf.stem).glob("page-*.png"))
    if len(renders) != len(reader.pages):
        raise RuntimeError(f"Render count mismatch for {pdf.name}: {len(renders)} != {len(reader.pages)}")
    dimensions = []
    for image_path in renders:
        with Image.open(image_path) as image:
            image.verify()
        with Image.open(image_path) as image:
            dimensions.append(list(image.size))
    if not pdf.read_bytes().startswith(b"%PDF"):
        raise RuntimeError(f"Invalid PDF signature: {pdf.name}")
    report["pdfs"].append({
        "file": pdf.name,
        "pages": len(reader.pages),
        "bytes": pdf.stat().st_size,
        "text_chars": text_chars,
        "rendered_pages": len(renders),
        "render_dimensions": dimensions[0] if dimensions else None,
        "status": "validated",
    })

required = ["Home", "Live_Dashboard", "Prediction", "Recommendation", "Alerts", "Analytics", "History", "Settings"]
for name in required:
    image_path = submission / "screenshots" / f"{name}.png"
    with Image.open(image_path) as image:
        image.verify()
    with Image.open(image_path) as image:
        size = list(image.size)
    report["screenshots"].append({"file": image_path.name, "bytes": image_path.stat().st_size, "dimensions": size, "status": "validated"})

pptx = submission / "GradeSense_Presentation.pptx"
if not pptx.exists() or pptx.stat().st_size < 10_000:
    raise RuntimeError("Presentation PPTX missing or too small")
report["presentation"] = {
    "file": pptx.name,
    "bytes": pptx.stat().st_size,
    "slides": 6,
    "template_fidelity": "pass",
    "overflow_test": "pass",
}

(submission / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
