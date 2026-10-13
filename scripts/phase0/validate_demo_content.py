"""Read-only source-content checks; does not import or execute application code."""
from decimal import Decimal
from pathlib import Path
import hashlib
import re
import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "t00.6-portable"

def require(condition, message):
    if not condition:
        raise ValueError(message)

def main():
    data = {}
    files = sorted((CONTENT / "seed/demo").glob("*.yaml"))
    require(len(files) == 10, "Expected ten existing demo YAML files")
    for path in files:
        data.update(yaml.safe_load(path.read_text(encoding="utf-8")))
    indices = {group: {row["ref"]: row for row in data[group]} for group in
               ("companies", "contacts", "deals", "sales_proposals", "documents", "email_threads", "email_messages")}
    for group, index in indices.items():
        require(len(index) == len(data[group]), f"Duplicate refs: {group}")
    for contact in data["contacts"]:
        require(contact["company_ref"] in indices["companies"], "Contact company absent")
    for email in data["contact_emails"]:
        require(email["contact_ref"] in indices["contacts"], "Mailbox contact absent")
    for term in data["deal_terms"]:
        require(term["sales_proposal_ref"] in indices["sales_proposals"], "Term proposal absent")
        require(term["deal_ref"] == indices["sales_proposals"][term["sales_proposal_ref"]]["deal_ref"], "Term linked to wrong deal")
    term_keys = [(r["sales_proposal_ref"], r["term_key"], r["ordinal"]) for r in data["deal_terms"]]
    require(len(set(term_keys)) == len(term_keys), "Duplicate term ordinals")
    for group, count in (("companies", 6), ("contacts", 6), ("deals", 6), ("sales_proposals", 5)):
        require(len(indices[group]) == count == len(data[group]), f"Bad inventory or duplicate refs: {group}")
    for deal in data["deals"]:
        require(deal["company_ref"] in indices["companies"], "Unknown company")
        require(deal["primary_contact_ref"] in indices["contacts"], "Unknown contact")
        require(indices["contacts"][deal["primary_contact_ref"]]["company_ref"] == deal["company_ref"], "Cross-company primary")
        require(any(r["deal_ref"] == deal["ref"] and r["contact_ref"] == deal["primary_contact_ref"] and r["role"] == "primary" for r in data["deal_contacts"]), "Missing primary membership")
        require(deal["value_minor"] is None or type(deal["value_minor"]) is int, "Money must be integer paise")
    for proposal in data["sales_proposals"]:
        require(proposal["deal_ref"] in indices["deals"], "Proposal deal absent")
        require(proposal["document_ref"] is None or proposal["document_ref"] in indices["documents"], "Document absent")
        require(proposal["email_thread_ref"] is None or proposal["email_thread_ref"] in indices["email_threads"], "Thread absent")
    expected = {"D-1": 48000000, "D-2": 24000000, "D-3": 32000000, "D-4": 18000000, "D-5": 21000000}
    for deal_ref, amount in expected.items():
        require(indices["deals"][deal_ref]["value_minor"] == amount, "Wrong deal price")
        terms = [r for r in data["deal_terms"] if r["deal_ref"] == deal_ref and r["term_key"] in ("setup_fee", "total_price")]
        require(len(terms) == 1 and Decimal(terms[0]["value_numeric"]) * 100 == amount, "Wrong major/minor unit conversion")
    catalog = {r["sku"]: r for r in data["catalog_items"]}
    for sku, amount, allowed in (("SUP-ANNUAL", 6000000, True), ("TRAIN-2H", 1200000, True), ("CUSTOM-INT", 7500000, False)):
        require(catalog[sku]["price_minor"] == amount and catalog[sku]["allowed_as_add_on"] is allowed, "Catalog mismatch")
    conflict = [r for r in data["deal_terms"] if r["term_key"] == "timeline_weeks"]
    require([(r["value_numeric"], r["source_page"], r["status"]) for r in conflict] == [("6", 2, "conflict"), ("8", 4, "conflict")], "Timeline conflict lost")
    require(all(r["verified_at"] is None for r in conflict), "Conflict falsely verified")
    for row in data["documents"]:
        blob = (CONTENT / row["source_path"]).read_bytes()
        require(hashlib.sha256(blob).hexdigest() == row["sha256"] and len(blob) == row["size_bytes"], "Document hash/size drift")
    for number, price, pages in ((1, "4,80,000", 4), (2, "2,40,000", 1), (3, "3,20,000", 1)):
        reader = PdfReader(CONTENT / f"seed/demo/proposals/PR-{number}.pdf")
        require(len(reader.pages) == pages, "Wrong PDF page count")
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        require("\u20b9" + price in text and "?" + price not in text, "Damaged/wrong PDF money")
        if number == 1:
            require("6 weeks" in reader.pages[1].extract_text() and "8 weeks" in reader.pages[3].extract_text(), "Wrong conflict pages")
            require("\u20b915,000/month" in text and "50/50" in text and "30 days" in text, "Missing D-1 terms")
    require(indices["sales_proposals"]["PR-1"]["email_thread_ref"] is None, "D-1 must start without thread")
    for msg in data["email_messages"]:
        require(msg["thread_ref"] in indices["email_threads"], "Unknown message thread")
        require(msg["gmail_message_id"].startswith("seed-"), "Non-synthetic Gmail id")
    ooo = [r for r in data["email_messages"] if r["classification"] == "auto_reply"]
    require(len(ooo) == 1 and ooo[0]["processing_status"] == "ignored" and ooo[0]["headers"]["Auto-Submitted"] == "auto-replied", "OOO not ignored")
    require(indices["deals"]["D-3"]["last_customer_activity_at"] is None, "OOO updated human activity")
    quiet = []
    for deal in data["deals"]:
        outbound = deal["last_outbound_at"]
        if deal["stage"] == "proposal_sent" and outbound and int(outbound[1:-1]) >= 3 and deal["last_customer_activity_at"] is None:
            quiet.append(deal["ref"])
    require(quiet == ["D-1", "D-3", "D-4"], "Content quiet selection mismatch")
    require(indices["contacts"]["CT-4"]["autonomy_mode"] == "approval_required", "D-4 trust ramp lost")
    slot = data["calendar_plan"]["expected_first_afternoon_slot"]
    require(slot == {"day": "next:thu", "start": "15:00", "end": "15:30"}, "Wrong target slot")
    for block in data["calendar_plan"]["blocks"]:
        require(re.fullmatch(r"anchor_date|next:thu|target_day[+-]\d+d", block["day"]), "Unknown calendar relative date")
        require(all(re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", block[k]) for k in ("start", "end")), "Invalid wall-clock time")
        require(block["start"] < block["end"], "Invalid busy interval")
    for group in ("deals", "sales_proposals", "email_threads", "email_messages"):
        for row in data[group]:
            for key, value in row.items():
                if key.endswith("_at") or key in {"internal_date", "valid_until"}:
                    require(value is None or isinstance(value, str) and re.fullmatch(r"anchor|-\d+d|sent_at\+30d", value), f"Unknown authored relative time: {group}.{key}")
    for path in CONTENT.rglob("*"):
        if path.suffix in {".yaml", ".md"}:
            text = path.read_text(encoding="utf-8")
            require(not re.search(r"\?\d{1,2},\d", text), "Damaged money prefix")
            addresses = re.findall(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text)
            require(all(a.endswith("@seed.invalid") for a in addresses), "Non-fixture address in demo content")
            for token in re.findall(r"\$\{([^}]+)\}", text):
                require(token in {"DEMO_FOUNDER_EMAIL", "DEMO_EMAIL_RAJU", "DEMO_EMAIL_PRIYA", "DEMO_EMAIL_ARJUN"}, "Unknown demo mailbox placeholder")
    require(48000000 * 95 // 100 == 45600000, "Wrong 5% counter")
    print("PASS: 10 YAML; inventories/references; INR units; catalog; PDF prices/pages; hashes; OOO; quiet content; trust ramp; slot; fixture addresses.")
    print("Content checks only. Human review, importer/reset and live integration remain pending.")

if __name__ == "__main__":
    main()
