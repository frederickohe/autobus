import unittest

from core.intelligence.service.owner_agent_protocol import (
    WRITE_TOOLS,
    compose_user_content,
    confirm_summary,
    confirm_title,
    parse_control_payload,
)


class OwnerAgentProtocolTest(unittest.TestCase):
    def test_write_tools_require_confirmation(self):
        self.assertIn("create_product", WRITE_TOOLS)
        self.assertIn("send_customer_sms", WRITE_TOOLS)
        self.assertNotIn("list_products", WRITE_TOOLS)
        self.assertNotIn("ask_user", WRITE_TOOLS)

    def test_confirm_copy_for_product(self):
        title = confirm_title("create_product")
        summary = confirm_summary(
            "create_product",
            {"name": "Shea butter", "price": 40, "photos": ["https://cdn/x.jpg"]},
        )
        self.assertIn("product", title.lower())
        self.assertIn("Shea butter", summary)
        self.assertIn("40", summary)

    def test_parse_ask_and_confirm_json(self):
        ask = parse_control_payload(
            '{"type":"ask_input","message":"Send a photo","kind":"image","prompt":"Product photo"}'
        )
        self.assertIsNotNone(ask)
        self.assertEqual(ask["type"], "ask_input")
        self.assertEqual(ask["kind"], "image")

        confirm = parse_control_payload(
            'Here you go\n```json\n{"type":"confirm","tool":"create_customer","args":{"name":"Ama"}}\n```'
        )
        self.assertIsNotNone(confirm)
        self.assertEqual(confirm["tool"], "create_customer")
        self.assertIsNone(parse_control_payload("Just a normal reply"))

    def test_compose_user_content_includes_attachments(self):
        text = compose_user_content(
            "Add this",
            [{"kind": "image", "url": "https://cdn/p.jpg", "name": "p.jpg"}],
        )
        self.assertIn("Add this", text)
        self.assertIn("https://cdn/p.jpg", text)
        self.assertIn("image", text)


if __name__ == "__main__":
    unittest.main()
