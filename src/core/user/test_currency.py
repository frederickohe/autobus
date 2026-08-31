"""Unit tests for business pricing currency helpers."""

from __future__ import annotations

import unittest

from core.user.currency import (
    currency_prompt_rule,
    format_money,
    normalize_currency_code,
)


class CurrencyTests(unittest.TestCase):
    def test_defaults_to_ghs(self):
        self.assertEqual(normalize_currency_code(None), "GHS")
        self.assertEqual(normalize_currency_code(""), "GHS")
        self.assertEqual(normalize_currency_code("usd"), "USD")
        self.assertEqual(normalize_currency_code("XXX"), "GHS")

    def test_format_money_uses_selected_currency(self):
        self.assertEqual(format_money("20", "GHS"), "GHS 20")
        self.assertEqual(format_money(15, "USD"), "USD 15")

    def test_prompt_rule_blocks_dollar_when_not_usd(self):
        rule = currency_prompt_rule("GHS")
        self.assertIn("GHS", rule)
        self.assertIn("Never use $", rule)
        self.assertNotIn("Never use $", currency_prompt_rule("USD"))


if __name__ == "__main__":
    unittest.main()
