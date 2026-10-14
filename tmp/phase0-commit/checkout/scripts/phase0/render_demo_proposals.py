"""Export existing proposal Markdown with explicit page breaks and update document hashes."""
from pathlib import Path
import hashlib
import os
import yaml
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "t00.6-portable"

def main():
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    pdfmetrics.registerFont(TTFont("DemoArial", str(fonts / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("DemoArialBold", str(fonts / "arialbd.ttf")))
    for source in sorted((CONTENT / "seed/demo/proposals").glob("PR-*.md")):
        pages = source.read_text(encoding="utf-8").split("<!-- PAGE BREAK -->")
        out = canvas.Canvas(str(source.with_suffix(".pdf")), pagesize=A4, invariant=1)
        out.setTitle(source.stem + " synthetic sales proposal")
        width, height = A4
        for index, page in enumerate(pages, 1):
            out.setStrokeColorRGB(.10, .20, .32)
            out.setLineWidth(3)
            out.line(48, height - 72, width - 48, height - 72)
            y = height - 104
            for line in (line.strip() for line in page.strip().splitlines()):
                if not line:
                    continue
                heading = line.startswith("# ")
                label = line[2:] if heading else line
                font, size = ("DemoArialBold", 15) if heading else ("DemoArial", 11)
                if pdfmetrics.stringWidth(label, font, size) > width - 96:
                    # Keep a normal body font; allow long titles to wrap.
                    words, lines, current = label.split(), [], ""
                    for word in words:
                        trial = (current + " " + word).strip()
                        if pdfmetrics.stringWidth(trial, font, size) > width - 96:
                            lines.append(current)
                            current = word
                        else:
                            current = trial
                    lines.append(current)
                else:
                    lines = [label]
                out.setFillColorRGB(.10, .20, .32)
                out.setFont(font, size)
                for label in lines:
                    out.drawString(48, y, label)
                    y -= 20
                y -= 16 if heading else 14
                if y < 85:
                    raise ValueError(f"Content exceeds explicit page: {source.name} page {index}")
            out.setFont("DemoArial", 8)
            out.drawString(48, 40, "Demo proposal | Synthetic business content")
            out.drawRightString(width - 48, 40, f"Page {index} of {len(pages)}")
            out.showPage()
        out.save()
        print(source.with_suffix(".pdf").relative_to(ROOT), len(pages), "pages")
    metadata = CONTENT / "seed/demo/documents.yaml"
    data = yaml.safe_load(metadata.read_text(encoding="utf-8"))
    for row in data["documents"]:
        blob = (CONTENT / row["source_path"]).read_bytes()
        row["sha256"] = hashlib.sha256(blob).hexdigest()
        row["size_bytes"] = len(blob)
    metadata.write_text("# T00.6 authoring metadata; T03.6 assigns storage_path and actual database identifiers.\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

if __name__ == "__main__":
    main()
