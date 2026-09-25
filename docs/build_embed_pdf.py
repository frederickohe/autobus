"""Render a diagram-first embedded chat guide. Text stays inside table cells."""
from pathlib import Path

from reportlab.lib.colors import Color, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = Color(0.11, 0.13, 0.12)
GREEN = Color(0.12, 0.42, 0.28)
SOFT = Color(0.94, 0.97, 0.95)
LINE = Color(0.75, 0.82, 0.78)
MUTED = Color(0.33, 0.38, 0.35)
CREAM = Color(0.98, 0.97, 0.94)

OUT = Path(__file__).with_name("embed-integration.pdf")


def styles():
    return {
        "h1": ParagraphStyle("h1", fontName="Times-Bold", fontSize=20, leading=24, textColor=INK, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName="Times-Bold", fontSize=14, leading=18, textColor=GREEN, spaceBefore=8, spaceAfter=6),
        "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=11, leading=15, textColor=INK, spaceAfter=6),
        "title": ParagraphStyle("title", fontName="Times-Bold", fontSize=12, leading=15, textColor=GREEN, alignment=TA_LEFT),
        "card": ParagraphStyle("card", fontName="Times-Roman", fontSize=10, leading=13, textColor=INK),
        "center": ParagraphStyle("center", fontName="Times-Bold", fontSize=12, leading=14, textColor=GREEN, alignment=TA_CENTER),
        "th": ParagraphStyle("th", fontName="Times-Bold", fontSize=9, leading=12, textColor=white),
        "td": ParagraphStyle("td", fontName="Times-Roman", fontSize=9, leading=12, textColor=INK),
        "code": ParagraphStyle("code", fontName="Courier", fontSize=8, leading=11, textColor=INK),
    }


def _box(flowables, width, fill=SOFT):
    table = Table([[flowables]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0.8, GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def card(title, lines, width, s, fill=SOFT):
    bits = [Paragraph(title, s["title"])]
    bits.extend(Paragraph(line, s["card"]) for line in lines)
    return _box(bits, width, fill)


def arrow(s):
    return Paragraph("↓", s["center"])


def stack(blocks, s, width):
    rows = []
    for i, block in enumerate(blocks):
        rows.append([block])
        if i < len(blocks) - 1:
            rows.append([arrow(s)])
    table = Table(rows, colWidths=[width])
    table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return table


def pair(left, right, width):
    gap = 4 * mm
    col = (width - gap) / 2
    table = Table([[left, right]], colWidths=[col, col])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def grid(headers, rows, width, s, widths):
    data = [[Paragraph(h, s["th"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(cell, s["td"]) for cell in row])
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def code_block(text, width, s):
    body = "<br/>".join(line.replace(" ", "&nbsp;") for line in text.strip().splitlines())
    return _box([Paragraph(body, s["code"])], width, CREAM)


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(GREEN)
    canvas.rect(0, A4[1] - 12 * mm, A4[0], 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Times-Bold", 9)
    canvas.drawString(16 * mm, A4[1] - 8 * mm, "Autobus  ·  Embedded chat")
    canvas.setFillColor(MUTED)
    canvas.setFont("Times-Roman", 8)
    canvas.drawRightString(A4[0] - 16 * mm, 8 * mm, str(doc.page))
    canvas.restoreState()


def build():
    s = styles()
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
        title="Autobus embedded chat", author="Autobus",
    )
    w = A4[0] - 32 * mm
    half = (w - 8 * mm) / 2
    story = []

    story.append(Paragraph("Connect your software to Autobus", s["h1"]))
    story.append(Paragraph(
        "Your product keeps the chat screen. Autobus answers the customer and can place the order. "
        "You connect from the Autobus web portal. The mobile app does not manage this integration.",
        s["body"],
    ))
    story.append(stack([
        card("1. Your software", [
            "The customer types in your app or site.",
            "You already know who they are.",
        ], w, s),
        card("2. Autobus", [
            "Your server sends that message with an API key.",
            "Autobus reads the business catalog and the business memory.",
        ], w, s),
        card("3. Back to your software", [
            "You show the reply.",
            "If an order was placed, the response includes it, and Autobus also calls your webhook.",
        ], w, s),
    ], s, w))

    story.append(Paragraph("Two kinds of answers", s["h2"]))
    story.append(Paragraph(
        "A price or a product comes from the catalog. A question about the business comes from memory you train on the web portal.",
        s["body"],
    ))
    story.append(pair(
        card("Catalog", [
            "What you sell, the price, and the stock.",
            "Enter it in the portal, or push it from your software when catalog mode is synced.",
            "The bot will not quote a price that is not in this catalog.",
        ], half, s),
        card("Business memory", [
            "Hours, location, policies, and how you work.",
            "Train this under AI Intelligence on the Autobus web portal.",
            "The embed API does not accept a dump of business facts on each message.",
        ], half, s, fill=CREAM),
    w))

    story.append(Paragraph("Where you set it up", s["h2"]))
    story.append(stack([
        card("Web portal only", [
            "Sign in at the Autobus web portal.",
            "Open Settings, then Embedded chat.",
            "Choose the catalog mode, paste your webhook URL, issue the API key, and turn messages on.",
        ], w, s),
        card("Train the business memory first", [
            "Open AI Intelligence on the same web portal.",
            "Save the business profile and any documents you want the bot to use.",
            "After that, customer questions about the business can be answered in your embedded chat.",
        ], w, s, fill=CREAM),
    ], s, w))

    story.append(CondPageBreak(70 * mm))
    story.append(Paragraph("What you send, in order", s["h2"]))
    story.append(stack([
        card("A. Issue the key", [
            "Settings → Embedded chat on the web portal.",
            "The full key is shown once. Send it as Authorization: Bearer ab_live_…",
        ], w, s),
        card("B. Optional catalog push", [
            "Skip this when products are managed in the portal.",
            "When mode is synced, PUT /api/v1/embed/catalog with your SKUs.",
        ], w, s),
        card("C. Each customer message", [
            "POST /api/v1/embed/messages",
            "One message in. One reply out. Reuse message.id if you have to retry.",
        ], w, s),
        card("D. Your webhook", [
            "Autobus POSTs order.created when an order is placed.",
            "You later POST the order number when you have taken payment or shipped.",
        ], w, s),
    ], s, w))

    story.append(Paragraph("Catalog", s["h2"]))
    story.append(Paragraph(
        "PUT /api/v1/embed/catalog only works when the portal catalog mode is synced. Managed mode returns 409. Up to 200 items per call. The same external_id overwrites the previous item.",
        s["body"],
    ))
    story.append(code_block(
        '{\n'
        '  "items": [{\n'
        '    "external_id": "SKU-RICE-5",\n'
        '    "kind": "product",\n'
        '    "name": "Rice Bag 5kg",\n'
        '    "price": {"amount": "75.00", "currency": "GHS"},\n'
        '    "stock": {"tracked": true, "quantity": 40},\n'
        '    "active": true\n'
        '  }]\n'
        '}',
        w, s,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(grid(
        ["Field", "Required", "Meaning"],
        [
            ["external_id", "yes", "Your SKU. Later upserts with this id replace the item."],
            ["kind", "no", "product, or service."],
            ["name", "yes", "The name the bot may say and sell."],
            ["price.amount", "no", "The price the bot quotes. It does not take a price from the chat."],
            ["stock.tracked", "no", "true counts stock. false is a service that can always be ordered."],
            ["stock.quantity", "when tracked", "On hand. Zero means the bot will not sell it."],
            ["active", "no", "false hides it from the bot and keeps old orders."],
        ],
        w, s, [32 * mm, 28 * mm, w - 60 * mm],
    ))

    story.append(Paragraph("A customer message", s["h2"]))
    story.append(code_block(
        'POST /api/v1/embed/messages\n'
        'Authorization: Bearer ab_live_...\n'
        '\n'
        '{ "conversation_id": "thread_441",\n'
        '  "customer": {"external_id": "cust_8841", "name": "Ama Mensah"},\n'
        '  "message": {"id": "msg_91", "text": "I want 2 bags of rice"} }',
        w, s,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(grid(
        ["Field", "Required", "Meaning"],
        [
            ["customer.external_id", "yes", "Stable id in your software. This keys the conversation."],
            ["customer.name / phone", "no", "Copied onto the order when the customer has not typed them."],
            ["message.id", "yes", "Retrying the same id returns the first response and does not place a second order."],
            ["message.text", "yes", "What the customer said."],
        ],
        w, s, [42 * mm, 22 * mm, w - 64 * mm],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "The reply has text for the customer, product cards, and an actions list. Show the text. If actions contains order.created, record the order number and each item external_id. actions is empty when the bot only answered. conversation.handoff means the customer asked for a person. Payment stays in your software. The order is created unpaid and also appears in the portal.",
        s["body"],
    ))
    story.append(code_block(
        '{ "reply": { "text": "Order placed for 2 x Rice Bag 5kg…", "products": [] },\n'
        '  "actions": [{ "type": "order.created",\n'
        '    "order": { "order_number": "ORD-…", "source": "embed",\n'
        '      "items": [{"external_id": "SKU-RICE-5", "quantity": 2}],\n'
        '      "total": "150.00", "payment_status": "pending" } }] }',
        w, s,
    ))

    story.append(Paragraph("Webhooks and order updates", s["h2"]))
    story.append(stack([
        card("Autobus calls you", [
            "POST to the webhook URL saved on the portal.",
            "Events: order.created, order.updated, conversation.handoff, catalog.sync_failed.",
            "Header X-Autobus-Signature is sha256= plus HMAC-SHA256 of the raw body, using the portal webhook secret.",
            "Check the raw bytes before you parse JSON. This version does not retry, so also trust the actions array on the chat response.",
        ], w, s),
        card("You call Autobus after you fulfill", [
            "POST /api/v1/embed/orders/{order_number}",
            "payment_status: pending, paid, partial, refunded, failed.",
            "fulfillment_status: unfulfilled, partial, fulfilled, shipped, delivered.",
            "Autobus then sends order.updated.",
        ], w, s),
    ], s, w))
    story.append(Spacer(1, 3 * mm))
    story.append(grid(
        ["HTTP", "When"],
        [
            ["401", "Missing or unknown API key, or embedded chat is off."],
            ["400", "A required chat or catalog field is missing or invalid."],
            ["404", "That order number is not on this business."],
            ["409", "Catalog push while the portal mode is still managed in Autobus."],
        ],
        w, s, [22 * mm, w - 22 * mm],
    ))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUT)


if __name__ == "__main__":
    build()
