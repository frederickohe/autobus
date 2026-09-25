"""Render docs/embed-integration.pdf from the embedded-chat guide."""
from pathlib import Path

from reportlab.lib.colors import Color, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = Color(0.10, 0.12, 0.11)
GREEN = Color(0.12, 0.45, 0.30)
GREEN_SOFT = Color(0.93, 0.96, 0.94)
LINE = Color(0.78, 0.83, 0.80)
MUTED = Color(0.35, 0.38, 0.36)
CODE_BG = Color(0.96, 0.97, 0.96)

OUT = Path(__file__).with_name("embed-integration.pdf")


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Times-Bold", fontSize=22,
            textColor=INK, spaceAfter=6, leading=26,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Times-Bold", fontSize=14,
            textColor=GREEN, spaceBefore=12, spaceAfter=6, leading=18,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Times-Roman", fontSize=11,
            textColor=INK, leading=15, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontName="Times-Roman", fontSize=9,
            textColor=MUTED, leading=12,
        ),
        "th": ParagraphStyle(
            "th", fontName="Times-Bold", fontSize=9, textColor=white, leading=12,
        ),
        "td": ParagraphStyle(
            "td", fontName="Times-Roman", fontSize=9, textColor=INK, leading=12,
        ),
        "code": ParagraphStyle(
            "code", fontName="Courier", fontSize=8, leading=10, textColor=INK,
        ),
        "li": ParagraphStyle(
            "li", fontName="Times-Roman", fontSize=11, leading=14, textColor=INK,
        ),
    }
    styles["h1"].alignment = TA_LEFT
    return styles


class ArrowFlow(Flowable):
    """Horizontal boxes joined by arrows."""

    def __init__(self, steps, width):
        super().__init__()
        self.steps = steps
        self.box_w = width
        self.box_h = 22 * mm
        self.width = width
        self.height = self.box_h

    def draw(self):
        c = self.canv
        n = len(self.steps)
        gap = 8 * mm
        box = (self.box_w - gap * (n - 1)) / n
        for i, (title, subtitle) in enumerate(self.steps):
            x = i * (box + gap)
            c.setFillColor(GREEN_SOFT)
            c.setStrokeColor(GREEN)
            c.roundRect(x, 0, box, self.box_h, 4, fill=1, stroke=1)
            c.setFillColor(GREEN)
            c.setFont("Times-Bold", 9)
            c.drawCentredString(x + box / 2, 12 * mm, title)
            c.setFillColor(INK)
            c.setFont("Times-Roman", 8)
            c.drawCentredString(x + box / 2, 6 * mm, subtitle)
            if i < n - 1:
                ax = x + box + 1.2 * mm
                c.setStrokeColor(GREEN)
                c.setFillColor(GREEN)
                c.line(ax, self.box_h / 2, ax + gap - 2.4 * mm, self.box_h / 2)
                c.drawString(ax + gap - 3.2 * mm, self.box_h / 2 - 1.2 * mm, ">")


class SequenceChart(Flowable):
    def __init__(self, width):
        super().__init__()
        self.width = width
        self.height = 92 * mm
        self.actors = ["Customer", "Your software", "Autobus", "Your webhook"]

    def draw(self):
        c = self.canv
        n = len(self.actors)
        col = self.width / n
        top = self.height - 8 * mm
        c.setFillColor(GREEN)
        c.rect(0, self.height - 14 * mm, self.width, 14 * mm, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Times-Bold", 9)
        xs = []
        for i, name in enumerate(self.actors):
            x = col * i + col / 2
            xs.append(x)
            c.drawCentredString(x, self.height - 9 * mm, name)
        c.setStrokeColor(LINE)
        c.setDash(1, 2)
        for x in xs:
            c.line(x, 2 * mm, x, top)
        c.setDash()
        messages = [
            (0, 1, "Says what they want", False),
            (1, 2, "POST /messages", False),
            (2, 2, "Match catalog, place order", False),
            (2, 1, "Reply, cards, actions", True),
            (1, 0, "Shows the reply", True),
            (2, 3, "order.created", False),
        ]
        y = top - 8 * mm
        for src, dst, label, dashed in messages:
            if dashed:
                c.setDash(2, 2)
            c.setStrokeColor(GREEN if not dashed else MUTED)
            c.setFillColor(INK)
            y1 = y
            if src == dst:
                c.line(xs[src], y, xs[src] + 16 * mm, y)
                c.line(xs[src] + 16 * mm, y, xs[src] + 16 * mm, y - 5 * mm)
                c.line(xs[src] + 16 * mm, y - 5 * mm, xs[src], y - 5 * mm)
                c.setFont("Times-Italic", 8)
                c.drawString(xs[src] + 2 * mm, y + 1.5 * mm, label)
                y -= 12 * mm
                c.setDash()
                continue
            x1, x2 = xs[src], xs[dst]
            c.line(x1, y1, x2, y1)
            c.setFont("Times-Roman", 8)
            c.drawCentredString((x1 + x2) / 2, y1 + 1.6 * mm, label)
            c.setDash()
            y -= 11 * mm


class LaneChart(Flowable):
    def __init__(self, width):
        super().__init__()
        self.width = width
        self.height = 38 * mm

    def draw(self):
        c = self.canv
        lanes = [
            ("Chat", "Your app calls Autobus", "One message in, one reply out"),
            ("Catalog", "Your app pushes items", "Only when mode is synced"),
            ("Webhook", "Autobus calls your URL", "Order, handoff, sync failure"),
        ]
        gap = 4 * mm
        box = (self.width - gap * 2) / 3
        for i, (title, who, detail) in enumerate(lanes):
            x = i * (box + gap)
            c.setFillColor(GREEN_SOFT)
            c.setStrokeColor(GREEN)
            c.roundRect(x, 0, box, self.height, 4, fill=1, stroke=1)
            c.setFillColor(GREEN)
            c.setFont("Times-Bold", 11)
            c.drawCentredString(x + box / 2, 26 * mm, title)
            c.setFillColor(INK)
            c.setFont("Times-Roman", 9)
            c.drawCentredString(x + box / 2, 16 * mm, who)
            c.setFillColor(MUTED)
            c.setFont("Times-Roman", 8)
            c.drawCentredString(x + box / 2, 8 * mm, detail)


def _table(headers, rows, styles, widths):
    s = styles
    data = [[Paragraph(h, s["th"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(cell), s["td"]) for cell in row])
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("BACKGROUND", (0, 1), (-1, -1), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, GREEN_SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _code(text, styles, width):
    block = Preformatted(text.strip("\n"), styles["code"])
    table = Table([[block]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _bullets(items, styles):
    return ListFlowable(
        [ListItem(Paragraph(item, styles["li"]), leftIndent=8) for item in items],
        bulletType="1",
        start="1",
        leftIndent=16,
        bulletFontName="Times-Roman",
        bulletFontSize=11,
    )


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(GREEN)
    canvas.rect(0, A4[1] - 12 * mm, A4[0], 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Times-Bold", 9)
    canvas.drawString(18 * mm, A4[1] - 8 * mm, "Autobus  ·  Embedded chat")
    canvas.setFont("Times-Roman", 8)
    canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
    canvas.restoreState()


def build():
    styles = _styles()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="Autobus embedded chat",
        author="Autobus",
    )
    width = A4[0] - 32 * mm
    story = []
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Embedded chat", styles["h1"]))
    story.append(Paragraph(
        "Autobus answers your customers and places orders. Your software owns the screen. "
        "You send each message to Autobus and show the reply. When an order is placed, "
        "Autobus also calls a webhook on your server so you can fulfill it.",
        styles["body"],
    ))
    story.append(Paragraph("Base URL: https://&lt;your-autobus-host&gt;/api/v1/embed", styles["body"]))

    story.append(Paragraph("How a turn works", styles["h2"]))
    story.append(Paragraph(
        "The customer talks to your product. Your product asks Autobus. Autobus answers from the catalog and, when the customer confirms, creates the order.",
        styles["body"],
    ))
    story.append(SequenceChart(width))
    story.append(Spacer(1, 4 * mm))
    story.append(LaneChart(width))
    story.append(Spacer(1, 4 * mm))
    story.append(_table(
        ["Direction", "Who starts it", "What it is for"],
        [
            ["Chat", "Your software", "One customer message in, one reply out"],
            ["Catalog sync", "Your software", "Push inventory Autobus is allowed to sell"],
            ["Webhook", "Autobus", "Order placed, order updated, or a person was requested"],
        ],
        styles,
        [32 * mm, 38 * mm, width - 70 * mm],
    ))

    story.append(Paragraph("1. Turn it on in the portal", styles["h2"]))
    story.append(Paragraph("In the Autobus app, open Settings, then Embedded chat.", styles["body"]))
    story.append(ArrowFlow([
        ("1. Catalog", "Managed or synced"),
        ("2. Webhook", "Your HTTPS URL"),
        ("3. API key", "Shown once"),
        ("4. Enable", "Accept messages"),
    ], width))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Managed in Autobus means products are entered in the portal, so you skip catalog sync. "
        "Synced from your software means your system is the source of truth and you push items with PUT /catalog.",
        styles["body"],
    ))
    story.append(Paragraph(
        "The full API key is shown once. Store it as a secret. The portal keeps only a hash. "
        "Copy the webhook signing secret from the same screen and use it to verify that a webhook came from Autobus. "
        "The key is scoped to that business.",
        styles["body"],
    ))
    story.append(_code(
        "Authorization: Bearer ab_live_...\n"
        "X-Api-Key: ab_live_...    (also accepted)",
        styles, width,
    ))

    story.append(Paragraph("2. Catalog", styles["h2"]))
    story.append(Paragraph(
        "Push this only when catalog mode is synced. A managed catalog returns HTTP 409. "
        "The bot sells only these rows. Do not attach a product list to the chat message.",
        styles["body"],
    ))
    story.append(Paragraph("PUT /api/v1/embed/catalog", styles["body"]))
    story.append(_code(
        '{\n'
        '  "items": [{\n'
        '    "external_id": "SKU-RICE-5",\n'
        '    "kind": "product",\n'
        '    "name": "Rice Bag 5kg",\n'
        '    "description": "Local perfumed rice",\n'
        '    "price": { "amount": "75.00", "currency": "GHS" },\n'
        '    "stock": { "tracked": true, "quantity": 40 },\n'
        '    "category": "Grocery",\n'
        '    "active": true\n'
        '  }, {\n'
        '    "external_id": "SVC-DELIVERY",\n'
        '    "kind": "service",\n'
        '    "name": "Same-day delivery",\n'
        '    "price": { "amount": "20.00", "currency": "GHS" },\n'
        '    "stock": { "tracked": false },\n'
        '    "active": true\n'
        '  }]\n'
        '}',
        styles, width,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_table(
        ["Field", "Required", "Meaning"],
        [
            ["external_id", "yes", "Your SKU. Later upserts with the same id overwrite the item."],
            ["kind", "no", "product (default) or service."],
            ["name", "yes", "Name the bot is allowed to say and sell."],
            ["price.amount", "no", "Decimal string. Defaults to 0. The bot quotes this price."],
            ["price.currency", "no", "Display hint. Orders use the business currency in Autobus."],
            ["stock.tracked", "no", "true for a counted product. false for a service that can always be ordered."],
            ["stock.quantity", "when tracked", "Integer on hand. 0 means the bot will not sell it."],
            ["active", "no", "false hides the item from the bot and keeps order history."],
        ],
        styles,
        [32 * mm, 28 * mm, width - 60 * mm],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Send changes as they happen, and a full snapshot at least once a day. Up to 200 items per request. "
        "GET /api/v1/embed/catalog returns the items Autobus currently has for this key.",
        styles["body"],
    ))

    story.append(Paragraph("3. Send a message", styles["h2"]))
    story.append(Paragraph("POST /api/v1/embed/messages", styles["body"]))
    story.append(_code(
        '{\n'
        '  "conversation_id": "thread_441",\n'
        '  "customer": {\n'
        '    "external_id": "cust_8841",\n'
        '    "name": "Ama Mensah",\n'
        '    "phone": "+233201234567"\n'
        '  },\n'
        '  "message": { "id": "msg_91", "text": "I want 2 bags of rice" }\n'
        '}',
        styles, width,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_table(
        ["Field", "Required", "Meaning"],
        [
            ["customer.external_id", "yes", "Stable id in your software. Combined with the business, this is the conversation key."],
            ["customer.name", "no", "Pre-filled onto the order when the customer has not typed a name."],
            ["customer.phone", "no", "Pre-filled onto the order. The bot asks when a phone is still needed."],
            ["conversation_id", "no", "Your thread id. Copied onto the order and the webhook."],
            ["message.id", "yes", "Your id for this turn. The same id returns the original response and does not place a second order."],
            ["message.text", "yes", "What the customer said."],
        ],
        styles,
        [40 * mm, 22 * mm, width - 62 * mm],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Response", styles["body"]))
    story.append(_code(
        '{\n'
        '  "conversation_id": "thread_441",\n'
        '  "reply": {\n'
        '    "text": "Order placed for 2 x Rice Bag 5kg ...",\n'
        '    "products": [{ "external_id": "SKU-RICE-5", "name": "Rice Bag 5kg", "price": "75.00", "currency": "GHS", "stock": 38 }]\n'
        '  },\n'
        '  "actions": [{\n'
        '    "type": "order.created",\n'
        '    "order": {\n'
        '      "order_number": "ORD-20260925-10421",\n'
        '      "source": "embed",\n'
        '      "external_customer_id": "cust_8841",\n'
        '      "items": [{ "external_id": "SKU-RICE-5", "name": "Rice Bag 5kg", "quantity": 2, "unit_price": "75.00" }],\n'
        '      "total": "150.00",\n'
        '      "currency": "GHS",\n'
        '      "status": "pending",\n'
        '      "payment_status": "pending"\n'
        '    }\n'
        '  }]\n'
        '}',
        styles, width,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Show reply.text to the customer. Render reply.products as cards when you want. Treat actions as the machine result. "
        "actions is empty when the bot only answered. conversation.handoff is added when the customer asks for a person and handoff is enabled. "
        "Payment stays in your software. The order is created unpaid and also appears in the Autobus portal.",
        styles["body"],
    ))

    story.append(Paragraph("4. Receive webhooks", styles["h2"]))
    story.append(Paragraph("Autobus POSTs JSON to the URL you saved.", styles["body"]))
    story.append(_code(
        '{\n'
        '  "id": "evt_...",\n'
        '  "type": "order.created",\n'
        '  "created_at": "2026-09-25T00:40:00Z",\n'
        '  "data": { }\n'
        '}',
        styles, width,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_table(
        ["Header", "Meaning"],
        [
            ["X-Autobus-Event", "order.created, order.updated, conversation.handoff, or catalog.sync_failed"],
            ["X-Autobus-Signature", "sha256= plus HMAC-SHA256 of the raw body, using your webhook secret"],
        ],
        styles,
        [42 * mm, width - 42 * mm],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Verify the signature against the raw bytes before you parse JSON. Reject anything that does not match. "
        "order.created and order.updated put the order object in data. catalog.sync_failed puts failed items and an upserted count in data. "
        "Respond with HTTP 2xx. Autobus does not retry a failed delivery in this version, so act on the synchronous actions array immediately and use the webhook as the copy your backend stores.",
        styles["body"],
    ))

    story.append(Paragraph("5. Update an order", styles["h2"]))
    story.append(ArrowFlow([
        ("Order placed", "pending, unpaid"),
        ("You take payment", "your software"),
        ("POST update", "paid / fulfilled"),
        ("Webhook", "order.updated"),
    ], width))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("POST /api/v1/embed/orders/{order_number}", styles["body"]))
    story.append(_code(
        '{\n'
        '  "payment_status": "paid",\n'
        '  "fulfillment_status": "fulfilled",\n'
        '  "payment_reference": "TXN-12345"\n'
        '}',
        styles, width,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "payment_status: pending, paid, partial, refunded, failed. "
        "fulfillment_status: unfulfilled, partial, fulfilled, shipped, delivered. "
        "order_status: pending, processing, confirmed, cancelled, completed.",
        styles["body"],
    ))

    story.append(Paragraph("Errors", styles["h2"]))
    story.append(_table(
        ["HTTP", "When"],
        [
            ["401", "Missing or unknown API key, or embedded chat is off"],
            ["400", "A required chat or catalog field is missing or invalid"],
            ["404", "Order number is not on this business"],
            ["409", "Catalog push while mode is still managed in the portal"],
        ],
        styles,
        [22 * mm, width - 22 * mm],
    ))

    story.append(Paragraph("Minimal loop", styles["h2"]))
    story.append(_bullets([
        "Store message.id, then POST /messages with the API key.",
        "If actions contains order.created, record order_number and each item external_id, then fulfill.",
        "When payment completes, POST the order update.",
        "If catalog mode is synced, PUT /catalog when inventory changes.",
    ], styles))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    print(OUT)


if __name__ == "__main__":
    build()
