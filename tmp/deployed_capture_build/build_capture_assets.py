from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(r"Q:\Programs\GradeSense")
SUBMISSION = ROOT / "Submission"
SHOTS = SUBMISSION / "deployed_screenshots"
BUILD = ROOT / "tmp" / "deployed_capture_build"
BUILD.mkdir(parents=True, exist_ok=True)

NAMES = ["Home", "Prediction", "Recommendation", "Alerts", "Analytics", "History", "Settings"]
URLS = {
    "Home": "/dashboard",
    "Prediction": "/prediction",
    "Recommendation": "/recommendations",
    "Alerts": "/dashboard · Live alerts",
    "Analytics": "/analytics",
    "History": "/history/predictions",
    "Settings": "/admin/config",
}


def font(size: int, bold: bool = False):
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def contain(im: Image.Image, box: tuple[int, int], bg=(244, 246, 248)):
    canvas_im = Image.new("RGB", box, bg)
    copy = im.convert("RGB")
    copy.thumbnail(box, Image.Resampling.LANCZOS)
    x = (box[0] - copy.width) // 2
    y = (box[1] - copy.height) // 2
    canvas_im.paste(copy, (x, y))
    return canvas_im


def build_montage():
    width, height = 1920, 1080
    out = Image.new("RGB", (width, height), "#F4F6F8")
    draw = ImageDraw.Draw(out)
    draw.rectangle((0, 0, width, 116), fill="#0B1F33")
    draw.rectangle((0, 108, width, 116), fill="#E31B23")
    draw.text((54, 28), "GradeSense · Deployed Application", font=font(40, True), fill="white")
    draw.text((54, 76), "Production capture · gradesense-4weh.onrender.com", font=font(20), fill="#C7D4E0")
    margin, gap = 42, 22
    card_w = (width - 2 * margin - 3 * gap) // 4
    card_h = 420
    for idx, name in enumerate(NAMES):
        row = idx // 4
        col = idx % 4
        x = margin + col * (card_w + gap)
        y = 150 + row * (card_h + 28)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=16, fill="white", outline="#D8DEE5", width=2)
        draw.text((x + 18, y + 15), name, font=font(23, True), fill="#0B1F33")
        draw.text((x + 18, y + 47), URLS[name], font=font(14), fill="#607080")
        shot = Image.open(SHOTS / f"{name}.png")
        thumb = contain(shot, (card_w - 28, card_h - 88))
        out.paste(thumb, (x + 14, y + 76))
    montage_path = SHOTS / "Deployed_Screenshots_Montage.png"
    out.save(montage_path, quality=94)
    return montage_path


def build_slide_strip():
    width, height = 1960, 290
    out = Image.new("RGB", (width, height), "#F4F6F8")
    draw = ImageDraw.Draw(out)
    gap, margin = 12, 10
    card_w = (width - 2 * margin - 6 * gap) // 7
    for idx, name in enumerate(NAMES):
        x = margin + idx * (card_w + gap)
        draw.rounded_rectangle((x, 8, x + card_w, height - 8), radius=10, fill="white", outline="#CAD3DC", width=2)
        draw.rectangle((x, 8, x + card_w, 48), fill="#0B1F33")
        draw.text((x + 10, 17), name, font=font(17, True), fill="white")
        shot = Image.open(SHOTS / f"{name}.png")
        thumb = contain(shot, (card_w - 16, height - 70), bg=(247, 248, 250))
        out.paste(thumb, (x + 8, 58))
    strip_path = SHOTS / "Presentation_Screenshot_Strip.png"
    out.save(strip_path, quality=94)
    return strip_path


def draw_header(c: canvas.Canvas, title: str, subtitle: str):
    w, h = landscape(A4)
    c.setFillColor(HexColor("#0B1F33"))
    c.rect(0, h - 72, w, 72, fill=1, stroke=0)
    c.setFillColor(HexColor("#E31B23"))
    c.rect(0, h - 76, w, 4, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(36, h - 43, title)
    c.setFillColor(HexColor("#C7D4E0"))
    c.setFont("Helvetica", 9.5)
    c.drawRightString(w - 36, h - 43, subtitle)


def build_appendix():
    appendix = BUILD / "deployed_screenshots_appendix.pdf"
    w, h = landscape(A4)
    c = canvas.Canvas(str(appendix), pagesize=(w, h))
    c.setTitle("GradeSense Technical Documentation · Deployed Application Screenshots")
    c.setAuthor("GradeSense Team")
    for idx, name in enumerate(NAMES, start=1):
        draw_header(c, f"Dashboard · {name}", f"Production capture {idx:02d}/07")
        c.setFillColor(HexColor("#4D5D6C"))
        c.setFont("Helvetica", 10)
        c.drawString(36, h - 98, f"Route: {URLS[name]}  ·  Source: https://gradesense-4weh.onrender.com")
        image = Image.open(SHOTS / f"{name}.png")
        max_w, max_h = w - 72, h - 146
        scale = min(max_w / image.width, max_h / image.height)
        iw, ih = image.width * scale, image.height * scale
        x, y = (w - iw) / 2, 26 + (max_h - ih) / 2
        c.setFillColor(HexColor("#FFFFFF"))
        c.roundRect(x - 5, y - 5, iw + 10, ih + 10, 7, fill=1, stroke=0)
        c.drawImage(ImageReader(image), x, y, width=iw, height=ih, preserveAspectRatio=True, mask="auto")
        c.showPage()
    c.save()
    return appendix


def merge_document(appendix: Path):
    target = SUBMISSION / "GradeSense_Technical_Documentation.pdf"
    merged = BUILD / "GradeSense_Technical_Documentation.updated.pdf"
    writer = PdfWriter()
    existing_pages = PdfReader(str(target)).pages
    # The original generated technical document is seven pages. Rebuild from
    # that stable core so rerunning this helper never duplicates the appendix.
    for page in existing_pages[:7]:
        writer.add_page(page)
    for page in PdfReader(str(appendix)).pages:
        writer.add_page(page)
    with merged.open("wb") as fh:
        writer.write(fh)
    merged.replace(target)
    return target


if __name__ == "__main__":
    montage = build_montage()
    build_slide_strip()
    appendix_pdf = build_appendix()
    documentation = merge_document(appendix_pdf)
    print(montage)
    print(documentation)
