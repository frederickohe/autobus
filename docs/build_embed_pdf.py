"""Render a diagram-first embedded chat guide. Text stays inside table cells."""
from pathlib import Path

from reportlab.lib.colors import Color, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = Color(0.08, 0.14, 0.12)
GREEN = Color(0.10, 0.52, 0.36)
DEEP = Color(0.06, 0.22, 0.16)
SOFT = Color(0.91, 0.96, 0.93)
LINE = Color(0.82, 0.88, 0.85)
MUTED = Color(0.36, 0.44, 0.40)
CREAM = Color(0.97, 0.96, 0.93)
GOLD = Color(0.72, 0.55, 0.22)
PAPER = Color(0.985, 0.988, 0.984)

OUT = Path(__file__).with_name("embed-integration.pdf")


def styles():
    return {
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=DEEP, spaceAfter=3),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=DEEP, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14, textColor=INK, spaceAfter=6),
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=DEEP, alignment=TA_LEFT),
        "card": ParagraphStyle("card", fontName="Helvetica", fontSize=9, leading=12, textColor=MUTED),
        "center": ParagraphStyle("center", fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=GREEN, alignment=TA_CENTER),
        "th": ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=white),
        "td": ParagraphStyle("td", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK),
        "code": ParagraphStyle("code", fontName="Courier", fontSize=7.5, leading=10, textColor=DEEP),
    }


class SequenceChart(Flowable):
    """Opening turn diagram: customer, your software, Autobus, your webhook."""

    def __init__(self, width):
        super().__init__()
        self.width = width
        self.height = 108 * mm
        self.actors = ["Customer", "Your software", "Autobus", "Your webhook"]

    def _head(self, c, x1, y, x2, color):
        c.setStrokeColor(color)
        c.setFillColor(color)
        c.setLineWidth(1.15)
        c.setLineCap(1)
        c.line(x1, y, x2, y)
        direction = 1 if x2 >= x1 else -1
        path = c.beginPath()
        tip = x2
        path.moveTo(tip, y)
        path.lineTo(tip - direction * 2.4 * mm, y + 1.15 * mm)
        path.lineTo(tip - direction * 2.4 * mm, y - 1.15 * mm)
        path.close()
        c.drawPath(path, fill=1, stroke=0)

    def _pill(self, c, x, y, label, fill, text=DEEP):
        c.setFont("Helvetica", 7)
        pad = 2.2 * mm
        tw = c.stringWidth(label, "Helvetica", 7)
        w = tw + pad * 2
        h = 4.6 * mm
        c.setFillColor(fill)
        c.roundRect(x - w / 2, y - h / 2, w, h, 2, fill=1, stroke=0)
        c.setFillColor(text)
        c.drawCentredString(x, y - 1.1 * mm, label)

    def draw(self):
        c = self.canv
        c.setFillColor(PAPER)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=1)
        n = len(self.actors)
        col = self.width / n
        top = self.height - 16 * mm
        xs = []
        for i, name in enumerate(self.actors):
            x = col * i + col / 2
            xs.append(x)
            c.setFillColor(DEEP if i == 2 else GREEN)
            c.roundRect(x - 16 * mm, self.height - 12 * mm, 32 * mm, 7 * mm, 3.5 * mm, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x, self.height - 9.4 * mm, name)
        c.setStrokeColor(LINE)
        c.setDash(1, 2)
        c.setLineWidth(0.7)
        for x in xs:
            c.line(x, 4 * mm, x, top)
        c.setDash()
        messages = [
            (0, 1, "Says what they want", False),
            (1, 2, "POST /messages", False),
            (2, 2, "Match catalog, place order", False),
            (2, 1, "Reply, cards, actions", True),
            (1, 0, "Shows the reply", True),
            (2, 3, "order.created", False),
        ]
        y = top - 7 * mm
        for src, dst, label, reply in messages:
            color = GOLD if reply else GREEN
            if src == dst:
                c.setStrokeColor(color)
                c.setLineWidth(1.15)
                c.line(xs[src], y, xs[src] + 12 * mm, y)
                c.line(xs[src] + 12 * mm, y, xs[src] + 12 * mm, y - 5 * mm)
                self._head(c, xs[src] + 12 * mm, y - 5 * mm, xs[src], color)
                self._pill(c, xs[src], y + 3.4 * mm, label, white)
                y -= 13 * mm
                continue
            x1, x2 = xs[src], xs[dst]
            end = x2 - (2.2 * mm if x2 > x1 else -2.2 * mm)
            self._head(c, x1, y, end, color)
            self._pill(c, (x1 + x2) / 2, y + 3.6 * mm, label, white)
            y -= 11.5 * mm


def _box(flowables, width, fill=SOFT):
    table = Table([[flowables]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("LINEBEFORE", (0, 0), (0, 0), 3, GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
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
        ("BACKGROUND", (0, 0), (-1, 0), DEEP),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.25, LINE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
    canvas.setFillColor(DEEP)
    canvas.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(GREEN)
    canvas.circle(22 * mm, A4[1] - 7 * mm, 2.2 * mm, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(28 * mm, A4[1] - 8.2 * mm, "Autobus")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(Color(0.78, 0.88, 0.82))
    canvas.drawString(48 * mm, A4[1] - 8.2 * mm, "Embedded chat")
    canvas.setFillColor(GREEN)
    canvas.circle(A4[0] - 22 * mm, 10 * mm, 4 * mm, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(A4[0] - 22 * mm, 8.6 * mm, str(doc.page))
    canvas.restoreState()


def build():
    s = styles()
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
        title="Autobus embedded chat", author="Autobus",
    )
    w = A4[0] - 32 * mm
    half = (w - 8 * mm) / 2
    story = []

    story.append(Paragraph("Connect your software to Autobus", s["h1"]))
    story.append(Paragraph(
        "The customer talks to your product. Your product asks Autobus. Autobus answers from the catalog and, when the customer confirms, creates the order.",
        s["body"],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(SequenceChart(w))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "You connect from the Autobus web portal. The mobile app does not manage this integration.",
        s["body"],
    ))
    story.append(Paragraph("Many stores under one business", s["h2"]))
    story.append(Paragraph(
        "A platform such as Shopify keeps one API key. Each call names the store. Autobus answers from that store only, and sends the same store id back.",
        s["body"],
    ))
    story.append(stack([
        card("Your platform", [
            "One API key for the parent business.",
            "You already know which store the customer is in.",
        ], w, s),
        card("Mark the store", [
            "Send sub_business.external_id, for example store_12, with the catalog and with each message.",
        ], w, s),
        card("Reply for that store", [
            "The response, the order, and the webhook all include the same sub_business.",
            "Route that payload back to store_12. Another store never sees this catalog or this chat.",
        ], w, s, fill=CREAM),
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
            "Open Business Manager, then Embedded chat.",
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
            "Business Manager → Embedded chat on the web portal.",
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
