import unittest

from core.nlu.service.customer_shop import (
    CatalogItem,
    classify_customer_shop_intent,
    extract_product_query_name,
    extract_quantity,
    resolve_catalog_query,
)


def _item(name: str, product_id: str = "p1", price: str = "10") -> CatalogItem:
    return CatalogItem(product_id=product_id, name=name, price=price, stock=12)


class CustomerShopOrderParsingTests(unittest.TestCase):
    def test_extracts_mango_juice_and_quantity_from_instagram_phrasing(self):
        text = "I want mango juice 20pcs"
        self.assertEqual(extract_product_query_name(text), "mango juice")
        self.assertEqual(extract_quantity(text), 20)

    def test_matches_listed_mango_juice_and_places_order_slots(self):
        catalog = [_item("Mango Juice", "mj")]
        intent, slots, _ = classify_customer_shop_intent(
            "I want mango juice 20pcs", catalog=catalog
        )
        self.assertEqual(intent, "create_order")
        self.assertEqual(slots.get("item_name"), "Mango Juice")
        self.assertEqual(slots.get("quantity"), "20")
        self.assertEqual(slots.get("product_id"), "mj")
        self.assertNotIn("I want", slots.get("item_name", ""))

    def test_matches_product_with_extra_catalog_words(self):
        catalog = [_item("Fresh Mango Juice 500ml", "fmj")]
        intent, slots, _ = classify_customer_shop_intent(
            "I want mango juice 20pcs", catalog=catalog
        )
        self.assertEqual(intent, "create_order")
        self.assertEqual(slots.get("item_name"), "Fresh Mango Juice 500ml")
        self.assertEqual(slots.get("quantity"), "20")

    def test_token_match_when_catalog_words_are_not_contiguous(self):
        catalog = [_item("Mango Fruit Juice", "mfj"), _item("Apple Juice", "aj")]
        matches = resolve_catalog_query("mango juice", catalog)
        self.assertEqual([item.name for item in matches], ["Mango Fruit Juice"])

    def test_does_not_quote_full_sentence_when_product_is_unknown(self):
        intent, slots, _ = classify_customer_shop_intent(
            "I want mango juice 20pcs", catalog=[]
        )
        self.assertEqual(intent, "create_order")
        self.assertEqual(slots.get("item_name"), "mango juice")
        self.assertEqual(slots.get("quantity"), "20")

    def test_existing_i_want_to_order_phrasing_still_works(self):
        catalog = [_item("Mango Juice", "mj")]
        intent, slots, _ = classify_customer_shop_intent(
            "I want to order mango juice", catalog=catalog
        )
        self.assertEqual(intent, "create_order")
        self.assertEqual(slots.get("item_name"), "Mango Juice")

    def test_catalog_browse_is_unchanged(self):
        intent, slots, _ = classify_customer_shop_intent(
            "what products do you have", catalog=[_item("Mango Juice")]
        )
        self.assertEqual(intent, "view_products")
        self.assertEqual(slots, {})

    def test_product_query_still_views_named_item(self):
        catalog = [_item("Mango Juice", "mj")]
        intent, slots, _ = classify_customer_shop_intent(
            "do you have mango juice", catalog=catalog
        )
        self.assertEqual(intent, "view_product")
        self.assertEqual(slots.get("product_name"), "Mango Juice")


if __name__ == "__main__":
    unittest.main()
