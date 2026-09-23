"""Offline executive briefs: Python 3.10+, reportlab, pypdf; no downloads.

CLI: python -B executive_brief.py INPUT.json --output-dir EXISTING_DIR
         --filename brief.pdf [--font-dir LOCAL_FONT_DIRECTORY]
API: render(dict, output_dir, filename, font_dir=None) -> manifest dict.
The PDF is the only file ever written; the manifest is returned and printed.

Schema 1.1: all fields below required unless marked optional; unknown/duplicate
keys and non-finite JSON are rejected. See the invented synthetic_example.json.
Root: schema_version="1.1", customer, program, confirmed_date=YYYY-MM-DD or null,
classification, classification_evidence, single_customer_confirmed=true,
sources, executive_summary, findings, risks_opportunities, proposed_actions,
service_matches. Optional: locale (tr default, or en), internal_notes,
excluded_customer_names (0..10). A null date displays Belirtilmedi/Not specified;
an absent date is invalid. No current date is inferred.
Classification: exactly synthetic/public/general. classification_evidence:
{basis: synthetic_declaration/public_release/general_release respectively,
reference: nonempty string}. Other or missing classifications fail closed.
sources (1..6): {id: S1..S99, title, section, kind: context/service,
classification, classification_evidence, evidence: nonempty declaration};
optional uri/internal_notes are opaque excluded metadata.
executive_summary (1..2), findings (1..4): {text, source_ids}.
risks_opportunities (0..3): {kind: risk/opportunity, text, source_ids}.
proposed_actions (1..5): {action, priority: P1/P2/P3, success_criterion, source_ids};
optional owner/timeframe. Priority, ownership and timing are proposals.
service_matches (0..4): {name, rationale, source_ids, verification_source_ids,
verified: true, relevant: true}. References must exist; services need context
AND service sources. Verification IDs must be service sources in source_ids.
Empty arrays must be explicit. Limits: labels/service names 80, source title 90,
section 50, text 350, action/rationale/success_criterion 220, owner/timeframe 60,
metadata 2000,
classification reference 240 characters; JSON <=64 KiB; PDF <=2 A4 pages.

Visible strings conservatively reject URLs/domains, backslashes, path-like or
unflanked slashes, embedded percent-encoded octets, token-like values,
controls/bidi and words >48 chars; markup is escaped. A single slash between
alphanumerics and a leading percent sign in prose are permitted.
Only used source title/section locators print, never raw metadata. Source IDs are
validated links, not printed marks: no [S1] style citation key appears anywhere in
the customer PDF, so the claim-to-source mapping belongs in the internal note.
Excluded names
and internal-note lines must not occur in rendered content (literal checks).
Use friendly titles such as "Pilot observations", not "observations.pdf":
filename-like domains remain forbidden. Put raw paths/URLs only in source.uri.
Static labels default to Turkish; locale never translates caller-supplied prose.
Every page says TASLAK (also DRAFT in en); any synthetic root/source automatically
adds DEMO / SENTETIK VERI. These workflow markers are not sensitivity labels.
Local DejaVu Sans or Arial regular/bold fonts, including matplotlib's bundled
fonts, are required; --font-dir chooses a local directory. Glyph coverage,
extracted text and embedded fonts are checked before output. Identical input and
renderer/dependency/font stack yield identical PDF bytes.

Output directory must exist and honor O_CREAT|O_EXCL, file identities and fsync;
hard links are NOT required. Verified in-memory bytes are written to an
exclusively reserved name, then read back. No overwrite fallback. The file is
visible during writing; publication is not crash-atomic. Register/use only after
render returns. Rollback checks identities and only removes this invocation's
file. Do not concurrently replace the trusted directory or its ancestors.
The output directory receives exactly one artifact, the PDF: no manifest or any
other sidecar file is written, because hosts attach whatever the directory
contains and a JSON sidecar is not a customer deliverable. Manifest:
filename, page_count, byte_size, sha256, renderer_version; NEVER artifact URLs.
It is returned by render() and printed as one JSON line by the CLI, so the
caller verifies from that value and must not look for a manifest file.
Host registration/download is the caller's job.

Caller must establish truthful classifications, verification, relevance and
single-customer scope. Declarations/literal checks are NOT independent evidence
verification, semantic DLP, sensitivity labels or MIP label application.
Caller must represent every service claim in verified service_matches, not
hide unverified claims in prose; arbitrary prose semantics remain caller-owned.
"""

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from contextlib import ExitStack
from datetime import date
from xml.sax.saxutils import escape


VERSION = "1.1.1"
MAX_JSON_BYTES = 65536
MARGIN_MM = 18
BODY_PT = 10.5
TABLE_PT = 9.4
ALLOWED = {"synthetic": "synthetic_declaration", "public": "public_release",
           "general": "general_release"}
TURKISH = "ÇĞİÖŞÜçğıöşü"
LABELS = {
    "title": ("Yönetici karar özeti", "Executive decision brief"),
    "program": ("Program", "Program"),
    "date": ("Rapor tarihi", "Report date"),
    "unspecified": ("Belirtilmedi", "Not specified"),
    "executive_summary": ("Yönetici özeti", "Executive summary"),
    "findings": ("Bulgular", "Findings"),
    "risks_opportunities": ("Riskler ve fırsatlar", "Risks and opportunities"),
    "risk": ("Risk", "Risk"), "opportunity": ("Fırsat", "Opportunity"),
    "none": ("Bilgi sunulmadı.", "None supplied."),
    "proposed_actions": ("Önerilen aksiyonlar", "Proposed actions"),
    "priority": ("Öncelik önerisi", "Proposed priority"),
    "action": ("Önerilen aksiyon", "Proposed action"),
    "success": ("Başarı ölçütü", "Success criterion"),
    "assignment": ("Sorumlu ve zaman önerisi", "Proposed owner and timing"),
    "owner": ("Sorumlu", "Owner"), "timeframe": ("Zaman", "Timing"),
    "service_matches": ("Doğrulanmış ilgili hizmet eşleşmeleri", "Verified relevant service matches"),
    "service": ("Hizmet", "Service"),
    "relevance": ("Kanıta dayalı uygunluk", "Evidence-backed relevance"),
    "no_services": ("Hizmet eşleşmesi sunulmadı.", "No service matches supplied."),
    "references": ("Kaynaklar", "References"), "page": ("Sayfa", "Page"),
}
UNSAFE = re.compile(
    r"\\|(?<![^\W_])/|/(?![^\W_])|[^\s/]*/[^\s/]*/"
    r"|(?:https?|ftp|file|mailto|data|javascript):|www\."
    r"|(?:[\w-]+\.)+[a-z]{2,63}\b"
    r"|\b(?:sig|signature|token|access_token|sas|authorization|sv|se|sp|skoid)\s*[=:]"
    r"|\bbearer\s+\S+|\beyJ[\w-]*\.[\w-]+\."
    r"|(?<=[^\W_])%[0-9a-f]{2}|[A-Za-z0-9_+=-]{40,}", re.I)


class BriefError(ValueError):
    """Invalid or disallowed input; no artifact should be used."""


class ContentTooLong(BriefError):
    """Revise the structured content; never shrink below minimum font sizes."""


def _keys(value, required, optional=()):
    if not isinstance(value, dict):
        raise BriefError("Expected a schema object.")
    missing = set(required) - value.keys()
    if missing:
        raise BriefError("Missing required fields: " + ", ".join(sorted(missing)))
    if value.keys() - set(required) - set(optional):
        raise BriefError("Unknown fields are not permitted.")


def _text(value, limit, visible=True):
    if not isinstance(value, str) or not value.strip():
        raise BriefError("Text must be a nonempty string.")
    if len(value) > limit:
        raise ContentTooLong(f"Text exceeds its {limit}-character schema limit.")
    if visible and (any(unicodedata.category(c).startswith("C") for c in value)
                    or UNSAFE.search(unicodedata.normalize("NFKC", value))
                    or any(len(w) > 48 for w in value.split())):
        raise BriefError("Customer text contains a URL, path, token, control, or oversized word.")
    return value


def _array(value, low, high):
    if not isinstance(value, list) or len(value) < low:
        raise BriefError("Missing required list entries or expected an array.")
    if len(value) > high:
        raise ContentTooLong(f"List exceeds its {high}-row schema limit.")
    return value


def _classification(obj):
    c = obj["classification"]
    if not isinstance(c, str) or c not in ALLOWED:
        raise BriefError("Classification gate: only explicit synthetic/public/general is permitted.")
    proof = obj["classification_evidence"]
    _keys(proof, ("basis", "reference"))
    if proof["basis"] != ALLOWED[c]:
        raise BriefError("Classification gate: missing or incompatible classification evidence.")
    _text(proof["reference"], 240, False)


def _compact(text):
    return "".join(unicodedata.normalize("NFC", text).split())


def _excluded(data):
    values = list(data.get("excluded_customer_names", []))
    for obj in [data] + data["sources"]:
        values.extend(line.strip() for line in obj.get("internal_notes", "").splitlines()
                      if line.strip())
    return values


def validate(data):
    """Validate all declarations and bounds without opening/writing any files."""
    _keys(data, ("schema_version", "customer", "program", "confirmed_date",
                 "classification", "classification_evidence", "single_customer_confirmed",
                 "sources", "executive_summary", "findings", "risks_opportunities",
                 "proposed_actions", "service_matches"),
          ("locale", "internal_notes", "excluded_customer_names"))
    if data["schema_version"] != "1.1":
        raise BriefError("Unsupported schema_version.")
    if data.get("locale", "tr") not in ("tr", "en"):
        raise BriefError("locale must be tr or en.")
    _classification(data)
    if data["single_customer_confirmed"] is not True:
        raise BriefError("Single-customer scope must be explicitly confirmed.")
    for key in ("customer", "program"):
        _text(data[key], 80)
    d = data["confirmed_date"]
    if d is not None:
        _text(d, 10)
        try:
            if date.fromisoformat(d).isoformat() != d:
                raise ValueError()
        except ValueError:
            raise BriefError("confirmed_date must be YYYY-MM-DD or explicit null.") from None
    if "internal_notes" in data:
        _text(data["internal_notes"], 2000, False)
    for name in _array(data.get("excluded_customer_names", []), 0, 10):
        _text(name, 80)
    sources = {}
    visible = [data["customer"], data["program"]] + ([d] if d is not None else [])
    for source in _array(data["sources"], 1, 6):
        _keys(source, ("id", "title", "section", "kind", "classification",
                       "classification_evidence", "evidence"), ("uri", "internal_notes"))
        _classification(source)
        sid = source["id"]
        if not isinstance(sid, str) or not re.fullmatch(r"S[1-9][0-9]?", sid) or sid in sources:
            raise BriefError("Source IDs must be unique S1..S99 identifiers.")
        if source["kind"] not in ("context", "service"):
            raise BriefError("Source kind must be context or service.")
        for key, bound in (("title", 90), ("section", 50)):
            visible.append(_text(source[key], bound))
        _text(source["evidence"], 2000, False)
        for key in ("uri", "internal_notes"):
            if key in source:
                _text(source[key], 2000, False)
        sources[sid] = source

    def refs(ids):
        _array(ids, 1, 6)
        if any(not isinstance(sid, str) or sid not in sources for sid in ids):
            raise BriefError("Missing or unknown source reference.")
        if len(set(ids)) != len(ids):
            raise BriefError("Duplicate source references.")
        return set(ids)

    for section, low, high in (("executive_summary", 1, 2), ("findings", 1, 4),
                               ("risks_opportunities", 0, 3)):
        for item in _array(data[section], low, high):
            required = ("text", "source_ids", "kind") if section == "risks_opportunities" else (
                "text", "source_ids")
            _keys(item, required)
            if section == "risks_opportunities" and item["kind"] not in ("risk", "opportunity"):
                raise BriefError("Risk/opportunity kind must be explicit.")
            visible.append(_text(item["text"], 350))
            refs(item["source_ids"])
    for action in _array(data["proposed_actions"], 1, 5):
        _keys(action, ("action", "priority", "success_criterion", "source_ids"), ("owner", "timeframe"))
        if action["priority"] not in ("P1", "P2", "P3"):
            raise BriefError("Proposed priority must be P1, P2 or P3.")
        visible.extend((action["priority"], _text(action["action"], 220),
                        _text(action["success_criterion"], 220)))
        refs(action["source_ids"])
        for key in ("owner", "timeframe"):
            if key in action:
                visible.append(_text(action[key], 60))
    for service in _array(data["service_matches"], 0, 4):
        _keys(service, ("name", "rationale", "source_ids", "verification_source_ids",
                        "verified", "relevant"))
        if service["verified"] is not True or service["relevant"] is not True:
            raise BriefError("Unverified or unconfirmed relevant service claims are prohibited.")
        visible.extend((_text(service["name"], 80), _text(service["rationale"], 220)))
        ids = refs(service["source_ids"])
        proof = refs(service["verification_source_ids"])
        if (not proof <= ids or any(sources[s]["kind"] != "service" for s in proof)
                or not any(sources[s]["kind"] == "context" for s in ids)):
            raise BriefError("Service needs declared service-verification and customer-context evidence.")
    joined = _compact(" ".join(visible)).casefold()
    if any(_compact(value).casefold() in joined for value in _excluded(data)):
        raise BriefError("Excluded customer or internal-note text occurs in customer content.")
    return visible


def load_input(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise BriefError("Duplicate JSON object key.")
            result[key] = value
        return result

    def bad_constant(_):
        raise BriefError("Non-finite JSON values are prohibited.")

    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ContentTooLong("Input exceeds 64 KiB.")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise BriefError("Input must be bounded valid UTF-8 JSON.") from None
    validate(data)
    return data


def _fonts(visible, font_dir):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont, TTFError

    if font_dir is not None:
        roots = [Path(font_dir)]
    else:
        roots = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"]
        for prefix in (Path(os.sep) / "usr" / "share" / "fonts",
                       Path(os.sep) / "usr" / "local" / "share" / "fonts"):
            roots.extend((prefix / "truetype" / "dejavu", prefix / "dejavu", prefix))
        spec = importlib.util.find_spec("matplotlib")
        if spec and spec.origin:
            roots.append(Path(spec.origin).parent / "mpl-data" / "fonts" / "ttf")
    chars = set("".join(visible) + TURKISH + "—[]:/|.,0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "abcdefghijklmnopqrstuvwxyz ")
    for root in roots:
        for regular, bold in (("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
                              ("arial.ttf", "arialbd.ttf")):
            paths = [root / regular, root / bold]
            if not all(p.is_file() for p in paths):
                continue
            names = []
            try:
                for p in paths:
                    name = "Brief_" + hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                    font = TTFont(name, str(p))
                    if any(not font.face.charToGlyph.get(ord(c)) for c in chars):
                        raise ValueError("Missing glyph")
                    pdfmetrics.registerFont(font)
                    names.append(name)
                return names
            except (ValueError, OSError, TTFError):
                continue
    raise BriefError("No suitable local DejaVu Sans or Arial regular/bold pair covers the text and Turkish.")


def _pdf(data, visible, font_dir):
    from pypdf import PdfReader
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                   TableStyle, LayoutError, KeepTogether)

    english = data.get("locale", "tr") == "en"
    labels = {key: pair[int(english)] for key, pair in LABELS.items()}
    status = "TASLAK / DRAFT" if english else "TASLAK"
    if any(obj["classification"] == "synthetic" for obj in [data] + data["sources"]):
        status += " | DEMO / SENTETIK VERI"
    regular, bold = _fonts(visible + list(labels.values()) + [status], font_dir)
    styles = {
        "body": ParagraphStyle("body", fontName=regular, fontSize=BODY_PT, leading=14,
                               spaceAfter=5, alignment=TA_LEFT, splitLongWords=True),
        "title": ParagraphStyle("title", fontName=bold, fontSize=17, leading=21, spaceAfter=7),
        "heading": ParagraphStyle("heading", fontName=bold, fontSize=11.5, leading=15,
                                  spaceBefore=9, spaceAfter=5, keepWithNext=True),
        "cell": ParagraphStyle("cell", fontName=regular, fontSize=TABLE_PT, leading=12,
                               splitLongWords=True),
        "th": ParagraphStyle("th", fontName=bold, fontSize=TABLE_PT, leading=12),
    }
    expected = []

    def para(text, style="body"):
        expected.append(text)
        return Paragraph(escape(text), styles[style])

    width = A4[0] - 2 * MARGIN_MM * mm - 12  # ReportLab frame padding.

    def table(headers, rows, ratios):
        cells = [[para(h, "th") for h in headers]]
        cells.extend([[([para(t, "cell") for t in c] if isinstance(c, list) else para(c, "cell"))
                       for c in row] for row in rows])
        t = Table(cells, colWidths=[width * r for r in ratios], splitByRow=0, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EFF5")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#8899AA")),
            ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#CDD6DF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    confirmed = data["confirmed_date"] if data["confirmed_date"] is not None else labels["unspecified"]
    story = [para(status, "heading"), para(data["customer"], "title"),
             para(labels["program"] + ": " + data["program"] + " | " + labels["date"] + ": " + confirmed)]
    for key in ("executive_summary", "findings", "risks_opportunities"):
        story.append(para(labels[key], "heading"))
        for item in data[key]:
            prefix = (labels[item["kind"]] + ": ") if "kind" in item else ""
            story.append(para(prefix + item["text"]))
        if not data[key]:
            story.append(para(labels["none"]))
    story.append(para(labels["proposed_actions"], "heading"))
    rows = [[a["priority"], a["action"], a["success_criterion"],
             [labels[k] + ": " + a.get(k, labels["unspecified"]) for k in ("owner", "timeframe")]]
            for a in data["proposed_actions"]]
    story.append(table([labels[k] for k in ("priority", "action", "success", "assignment")],
                       rows, (0.11, 0.33, 0.33, 0.23)))
    story.append(para(labels["service_matches"], "heading"))
    if data["service_matches"]:
        rows = [[s["name"], s["rationale"]] for s in data["service_matches"]]
        story.append(table([labels["service"], labels["relevance"]], rows, (0.31, 0.69)))
    else:
        story.append(para(labels["no_services"]))
    references = [para(labels["references"], "heading")]
    used = {sid for key in ("executive_summary", "findings", "risks_opportunities",
                            "proposed_actions", "service_matches")
            for item in data[key] for sid in item["source_ids"]}
    for source in data["sources"]:
        if source["id"] in used:
            references.append(para(source["title"] + " — " + source["section"]))
    # Kept whole so a single reference never orphans onto an otherwise blank page.
    story.append(KeepTogether(references))
    story.append(Spacer(1, 1))
    output = io.BytesIO()

    class BoundedDocument(SimpleDocTemplate):
        def handle_pageBegin(self):
            if self.page >= 2:
                raise ContentTooLong("Content exceeds two A4 pages; revise the input.")
            super().handle_pageBegin()

    def canvas_factory(*args, **kwargs):
        kwargs.update(invariant=1, pageCompression=1)
        canvas = Canvas(*args, **kwargs)
        canvas.setTitle(labels["title"])
        canvas.setAuthor("")
        canvas.setCreator("Executive brief renderer " + VERSION)
        return canvas

    def footer_text(page):
        return status + " | " + labels["page"] + " " + str(page)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular, BODY_PT)
        canvas.drawString(MARGIN_MM * mm, MARGIN_MM * mm, footer_text(doc.page))
        canvas.restoreState()

    doc = BoundedDocument(output, pagesize=A4, leftMargin=MARGIN_MM * mm,
                          rightMargin=MARGIN_MM * mm, topMargin=MARGIN_MM * mm,
                          bottomMargin=(MARGIN_MM + 7) * mm)
    try:
        doc.build(story, onFirstPage=footer, onLaterPages=footer, canvasmaker=canvas_factory)
    except LayoutError:
        raise ContentTooLong("Content or a table cannot fit within two A4 pages; revise the input.") from None
    pdf = output.getvalue()
    reader = PdfReader(io.BytesIO(pdf), strict=True)
    if not 1 <= len(reader.pages) <= 2:
        raise ContentTooLong("Actual PDF page count violates the two-page limit.")
    actual = []
    embedded = set()
    for index, page in enumerate(reader.pages, 1):
        if any(abs(float(page.mediabox[i]) - v) > 0.1
               for i, v in ((0, 0), (1, 0), (2, A4[0]), (3, A4[1]))):
            raise BriefError("PDF page dimensions failed verification.")
        text = _compact(page.extract_text() or "")
        marker = _compact(footer_text(index))
        if not text.startswith(marker):
            raise BriefError("PDF footer extraction failed verification.")
        actual.append(text[len(marker):])
        for font in page["/Resources"].get("/Font", {}).get_object().values():
            descriptor = font.get_object().get("/FontDescriptor")
            if descriptor and "/FontFile2" in descriptor.get_object():
                embedded.add(str(font.get_object().get("/BaseFont")))
        if page.get("/Annots"):
            raise BriefError("Unexpected PDF annotation or link.")
    content = "".join(actual)
    if content != "".join(_compact(s) for s in expected) or len(embedded) < 2:
        raise BriefError("PDF text, Turkish glyph extraction, or embedded fonts failed verification.")
    if any(_compact(v).casefold() in content.casefold() for v in _excluded(data)):
        raise BriefError("Excluded customer or internal note detected in PDF.")
    return pdf, len(reader.pages)


def render(data, output_dir, filename, font_dir=None):
    """Return verified metadata after exclusive PDF publication.

    Only the PDF reaches output_dir. The manifest is returned to the caller and
    never written as a sidecar file, so hosts that attach every file in the
    directory cannot surface internal JSON next to the customer deliverable.
    """
    visible = validate(data)  # Mandatory gate precedes all output-file operations.
    if (not isinstance(filename, str) or
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,55}\.pdf", filename) or
            re.fullmatch(r"(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", filename[:-4], re.I)):
        raise BriefError("Filename must be a safe non-reserved ASCII basename ending in .pdf.")
    if not isinstance(output_dir, (str, os.PathLike)) or not str(output_dir).strip():
        raise BriefError("An explicit output directory is required.")
    out = Path(output_dir)
    if out.is_symlink() or not out.is_dir():
        raise BriefError("An explicit existing non-symlink output directory is required.")
    out = out.resolve(strict=True)
    targets = [out / filename]
    if any(p.exists() or p.is_symlink() for p in targets):
        raise BriefError("Output already exists; nothing will be overwritten.")
    pdf, pages = _pdf(data, visible, font_dir)
    manifest = {"filename": filename, "page_count": pages, "byte_size": len(pdf),
                "sha256": hashlib.sha256(pdf).hexdigest(), "renderer_version": VERSION}
    created = {}

    def remove_owned(path):
        try:
            stat = path.lstat()
            if (stat.st_dev, stat.st_ino) == created[path]:
                path.unlink()
        except FileNotFoundError:
            pass

    try:
        with ExitStack() as stack:
            files = []
            for p, payload in zip(targets, (pdf,)):
                fd = os.open(p, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
                try:
                    stat = os.fstat(fd)
                    created[p] = (stat.st_dev, stat.st_ino)
                    handle = os.fdopen(fd, "w+b")
                except BaseException:
                    os.close(fd)
                    raise
                stack.enter_context(handle)
                files.append((p, handle, payload))
            for p, handle, payload in files:
                if handle.write(payload) != len(payload):
                    raise BriefError("Incomplete artifact write.")
                handle.flush()
                os.fsync(handle.fileno())
            for p, handle, payload in files:
                handle.seek(0)
                stat = p.lstat()
                if (stat.st_dev, stat.st_ino) != created[p] or handle.read() != payload:
                    raise BriefError("Published artifact identity or byte verification failed.")
    except BaseException:
        for p in reversed(created):
            try:
                remove_owned(p)
            except OSError:
                pass  # Continue cleaning other owned files if the filesystem denies one.
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--filename", required=True)
    parser.add_argument("--font-dir", type=Path)
    args = parser.parse_args()
    try:
        manifest = render(load_input(args.input), args.output_dir, args.filename, args.font_dir)
    except (BriefError, OSError, ImportError) as error:
        # No rejected content, raw paths, URIs, or third-party exception text in diagnostics.
        message = str(error) if isinstance(error, BriefError) else (
            "Dependency or filesystem failure; check local packages, fonts and output permissions.")
        print(json.dumps({"error": type(error).__name__, "message": message}), file=sys.stderr)
        return 2
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
