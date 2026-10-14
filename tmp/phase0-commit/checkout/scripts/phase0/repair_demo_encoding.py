"""Repair known T00.6 encoding damage; preserve numbers, terms and PDF page breaks."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "t00.6-portable"

def main():
    changed = []
    for path in sorted(CONTENT.rglob("*")):
        if path.suffix not in {".md", ".yaml"}:
            continue
        original = path.read_text(encoding="utf-8")
        # Only a damaged prefix on an Indian-grouped monetary amount.
        text = re.sub(r"\?(?=\d{1,2},\d{2,3}(?:,\d{3})?\b)", "\u20b9", original)
        if path.name in {"services.md", "faq.md", "pricing.md", "README.md", "VERIFICATION.md"}:
            text = re.sub(r"\?{1,2}(?=\d+\.\d)", "\u00a7", text)
        text = text.replace("customer?s information", "customer's information")
        text = text.replace("?Price-sensitive.", '"Price-sensitive.').replace("without me.?", 'without me."')
        text = text.replace("480000 ? 0.95", "480000 * 0.95")
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))
    print("Encoding repaired:", ", ".join(changed) or "already clean")

if __name__ == "__main__":
    main()
