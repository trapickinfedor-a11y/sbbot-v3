from seller_bot.handlers.cc_stock import _parse_cc_line
from shared.services.moderation_pricing_service import apply_brute_markup, apply_check_markup
from shared.services.seller_order_delivery_service import get_seller_order_policy
from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService

import io
import json
import unittest
import zipfile
from decimal import Decimal
from types import SimpleNamespace


class SellerUploadParserTests(unittest.TestCase):
    def test_parse_cc_line_fullz_payload(self) -> None:
        parsed = _parse_cc_line(
            "4111111111111111|12|2028|123|JOHN|DOE|1 MAIN ST|MIAMI|FL|33101|US",
            "with_fullz",
            "Visa Classic",
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["exp_mm"], 12)
        self.assertEqual(parsed["exp_yyyy"], 2028)
        self.assertEqual(parsed["card_brand"], "Visa")
        self.assertTrue(parsed["has_fullz"])
        self.assertEqual(parsed["zip"], "33101")

    def test_parse_cc_line_rejects_invalid_expiry(self) -> None:
        parsed = _parse_cc_line(
            "4111111111111111|13|2028|123|JOHN|DOE|1 MAIN ST|MIAMI|FL|33101|US",
            "standard",
            "Visa Classic",
        )

        self.assertIsNone(parsed)

    def test_parse_cc_line_accepts_compact_expiry(self) -> None:
        parsed = _parse_cc_line(
            "4111111111111111|12/28|123|JOHN|DOE|1 MAIN ST|MIAMI|FL|33101|US",
            "standard",
            "Visa Classic",
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["exp_mm"], 12)
        self.assertEqual(parsed["exp_yyyy"], 2028)
        self.assertEqual(parsed["card_brand"], "Visa")

    def test_parse_log_details_extracts_accounts_and_flags(self) -> None:
        details = SellerUploadPipelineService.parse_log_details(
            "Checking: $1,250.55\n"
            "Savings: $45.00\n"
            "BT+\n"
            "Zelle Enroll\n"
            "SafePass +🔓"
        )

        self.assertIsNotNone(details)
        assert details is not None
        self.assertGreaterEqual(len(details["accounts"]), 2)
        self.assertTrue(details["flags"]["bt_available"])
        self.assertTrue(details["flags"]["zelle_enroll"])
        self.assertTrue(details["flags"]["safepass_unlocked"])

    def test_parse_brute_bulk_text_supports_no_no_variant(self) -> None:
        items, errors = SellerUploadPipelineService.parse_brute_bulk_text(
            "Chase|no|no|123456789|021000021|1500.00|NY|John Doe|1 Main St",
            "75",
        )

        self.assertEqual(errors, [])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["credentials"]["login"], "no")
        self.assertEqual(items[0]["credentials"]["password"], "no")
        self.assertEqual(items[0]["routing_number"], "021000021")
        self.assertEqual(items[0]["price"], "75.00")

    def test_parse_logs_bulk_text_extracts_routing_and_name(self) -> None:
        rows, errors = SellerUploadPipelineService.parse_logs_bulk_text(
            "GTE|seller_login|seller_pass|cookie_blob|3200|FL|021000021|John Doe"
        )

        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["site"], "GTE")
        self.assertEqual(rows[0]["routing_number"], "021000021")
        self.assertEqual(rows[0]["holder_name"], "John Doe")

    def test_parse_selfreg_ba_bulk_text_extracts_account_fields(self) -> None:
        rows, errors = SellerUploadPipelineService.parse_selfreg_ba_bulk_text(
            "Chase|seller_login|seller_pass|123456789|021000021|2500|TX|John Doe|1 Main St|75001"
        )

        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bank_name"], "Chase")
        self.assertEqual(rows[0]["account_number"], "123456789")
        self.assertEqual(rows[0]["zip"], "75001")

    def test_inspect_nfc_archive_validates_required_files(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("wallet.apk", b"apk-bytes")
            archive.writestr(
                "instruction.txt",
                "bank_name: Chase\ncountry: US\nstate: FL\nzip: 33101\nnfc_type: ap\n",
            )

        info = SellerUploadPipelineService.inspect_nfc_archive(buffer.getvalue())
        self.assertEqual(info["bank_name"], "Chase")
        self.assertEqual(info["country"], "US")
        self.assertEqual(info["nfc_type"], "ap")

    def test_inspect_check_archive_reads_json_payload(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                "check_data.json",
                json.dumps({
                    "check_type": "personal",
                    "amount": "1200",
                    "has_holder_name": True,
                    "bank_name": "Chase",
                    "state": "NY",
                }),
            )
            archive.writestr("scan.jpg", b"image-bytes")

        info = SellerUploadPipelineService.inspect_check_archive(buffer.getvalue())
        self.assertEqual(info["check_type"], "personal")
        self.assertEqual(info["amount"], "1200.00")
        self.assertTrue(info["has_holder_name"])
        self.assertEqual(info["bank_name"], "Chase")

    def test_apply_markup_sets_base_and_buyer_prices(self) -> None:
        brute_item = SimpleNamespace(base_price=None, price=Decimal("100.00"))
        brute_rule = apply_brute_markup(brute_item)
        self.assertEqual(brute_rule.code, "brute")
        self.assertEqual(brute_item.base_price, Decimal("100.00"))
        self.assertEqual(brute_item.buyer_price, Decimal("115"))
        self.assertEqual(brute_item.price, Decimal("100.00"))

        check_item = SimpleNamespace(base_price=None, seller_price=Decimal("80.00"))
        check_rule = apply_check_markup(check_item)
        self.assertEqual(check_rule.code, "checks")
        self.assertEqual(check_item.base_price, Decimal("80.00"))
        self.assertEqual(check_item.buyer_price, Decimal("92"))

    def test_order_policy_uses_spec_windows(self) -> None:
        log_order = SimpleNamespace(product_type="bank", product_subtype="log")
        log_bank = SimpleNamespace(bank_name="Chase Log", product_type="bank", product_subtype="log", has_chat=True)
        self.assertEqual(get_seller_order_policy(log_order, log_bank).check_window_minutes, 360)

        check_order = SimpleNamespace(product_type="bank", product_subtype="checks")
        check_bank = SimpleNamespace(bank_name="Cashier Check", product_type="bank", product_subtype="checks", has_chat=True)
        self.assertEqual(get_seller_order_policy(check_order, check_bank).check_window_minutes, 60)

        enroll_order = SimpleNamespace(product_type="enrol", product_subtype="selfreg")
        enroll_bank = SimpleNamespace(bank_name="Selfreg BA", product_type="enrol", product_subtype="selfreg", has_chat=True)
        self.assertEqual(get_seller_order_policy(enroll_order, enroll_bank).check_window_minutes, 1440)


if __name__ == "__main__":
    unittest.main()
