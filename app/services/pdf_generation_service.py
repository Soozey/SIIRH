from hashlib import sha256
from io import BytesIO
from typing import Any
import re

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from ..config.config import settings


def _verification_payload(document_type: str, identifier: str) -> str:
    raw = f"{document_type}:{identifier}:{settings.DOCUMENT_VERIFY_SECRET}"
    return sha256(raw.encode("utf-8")).hexdigest()


def _draw_watermark(pdf: canvas.Canvas, text: str):
    pdf.saveState()
    pdf.setFillGray(0.85, 0.18)
    pdf.translate(280, 420)
    pdf.rotate(35)
    pdf.setFont("Helvetica-Bold", 42)
    pdf.drawCentredString(0, 0, text)
    pdf.restoreState()


def _draw_qr(pdf: canvas.Canvas, verification_code: str, x: int = 450, y: int = 720):
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(verification_code)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    pdf.drawImage(ImageReader(buffer), x, y, width=90, height=90)


def _draw_lines(pdf: canvas.Canvas, lines: list[str], start_y: int = 700):
    y = start_y
    pdf.setFont("Helvetica", 10)
    for line in lines:
        if y < 60:
            pdf.showPage()
            y = 780
            pdf.setFont("Helvetica", 10)
        pdf.drawString(40, y, line[:110])
        y -= 14


def build_payslip_pdf(preview_data: dict[str, Any], worker_name: str, period: str) -> bytes:
    verification_code = _verification_payload("payslip", f"{worker_name}:{period}")
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle(f"Bulletin_{worker_name}_{period}")
    _draw_watermark(pdf, "SIIRH VERIFIED")
    _draw_qr(pdf, verification_code)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, 800, f"Bulletin de paie - {period}")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, 780, f"Salarie: {worker_name}")
    pdf.drawString(40, 764, f"Verification: {verification_code[:20]}...")

    lines = []
    for line in preview_data.get("lines", []):
        label = line.get("label", "")
        montant = line.get("montant_sal", 0)
        lines.append(f"{label} : {montant}")

    totals = preview_data.get("totaux", {})
    lines.extend([
        "",
        f"Total brut : {totals.get('brut', 0)}",
        f"Charges salariales : {totals.get('cotisations_salariales', 0)}",
        f"Charges patronales : {totals.get('cotisations_patronales', 0)}",
        f"IRSA : {totals.get('irsa', 0)}",
        f"Net a payer : {totals.get('net', 0)}",
    ])
    _draw_lines(pdf, lines)
    pdf.save()
    return output.getvalue()


def build_contract_pdf(contract_title: str, content: str, employee_name: str) -> bytes:
    verification_code = _verification_payload("contract", f"{contract_title}:{employee_name}")
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle(contract_title)
    _draw_watermark(pdf, "SIIRH CONTRACT")
    _draw_qr(pdf, verification_code)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, 800, contract_title)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, 780, f"Salarie: {employee_name}")
    pdf.drawString(40, 764, f"Verification: {verification_code[:20]}...")

    plain_text = re.sub(r"<[^>]+>", " ", content or "")
    plain_text = re.sub(r"\s+", " ", plain_text).strip()
    chunks = [plain_text[i:i + 105] for i in range(0, len(plain_text), 105)] or [""]
    _draw_lines(pdf, chunks, start_y=730)
    pdf.save()
    return output.getvalue()


def build_report_pdf(
    title: str,
    subtitle: str,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> bytes:
    verification_code = _verification_payload("report", f"{title}:{subtitle}:{len(rows)}")
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle(title)
    _draw_watermark(pdf, "SIIRH REPORT")
    _draw_qr(pdf, verification_code)

    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(40, 800, title[:70])
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, 784, subtitle[:90])
    pdf.drawString(40, 768, f"Verification: {verification_code[:20]}...")

    table_lines = [" | ".join(columns[:6])]
    for row in rows:
        values = []
        for column in columns[:6]:
            value = row.get(column, "")
            values.append(str(value if value is not None else ""))
        table_lines.append(" | ".join(values))

    if len(columns) > 6:
        table_lines.extend([
            "",
            "Colonnes supplementaires incluses:",
            ", ".join(columns[6:])[:105],
        ])

    _draw_lines(pdf, table_lines, start_y=730)
    pdf.save()
    return output.getvalue()


def build_recruitment_announcement_pdf(
    title: str,
    subtitle: str,
    body: str,
) -> bytes:
    verification_code = _verification_payload("recruitment_announcement", f"{title}:{subtitle}")
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle(title)
    _draw_watermark(pdf, "SIIRH RECRUITMENT")
    _draw_qr(pdf, verification_code)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, 800, title[:70])
    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, 782, subtitle[:90])
    pdf.drawString(40, 766, f"Verification: {verification_code[:20]}...")

    plain_text = re.sub(r"<[^>]+>", " ", body or "")
    plain_text = plain_text.replace("\r", "\n")
    lines = []
    for raw_line in plain_text.split("\n"):
        clean_line = re.sub(r"\s+", " ", raw_line).strip()
        if not clean_line:
            lines.append("")
            continue
        chunks = [clean_line[i:i + 105] for i in range(0, len(clean_line), 105)]
        lines.extend(chunks)

    _draw_lines(pdf, lines or [""], start_y=730)
    pdf.save()
    return output.getvalue()
