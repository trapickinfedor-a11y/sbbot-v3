from __future__ import annotations

BANK_PRODUCT_TYPE_BANK = "bank"
BANK_PRODUCT_TYPE_ENROL = "enrol"

BANK_SUBTYPE_LOG = "log"
BANK_SUBTYPE_SELFREG = "selfreg"
BANK_SUBTYPE_BRUTE = "brute"

CC_SUBTYPE_CC = "cc"
CC_SUBTYPE_NON_VBV = "non_vbv"
# legacy (kept for DB compatibility)
CC_SUBTYPE_WITH_ZIP = "with_zip"
CC_SUBTYPE_WITH_FULLZ = "with_fullz"
CC_SUBTYPE_STANDARD = "standard"


def bank_type_label(product_type: str | None) -> str:
    mapping = {
        BANK_PRODUCT_TYPE_BANK: "Bank",
        BANK_PRODUCT_TYPE_ENROL: "Enrol",
    }
    return mapping.get((product_type or "").lower(), (product_type or "Bank").title())


def bank_subtype_label(product_subtype: str | None) -> str:
    mapping = {
        BANK_SUBTYPE_LOG: "Log",
        BANK_SUBTYPE_SELFREG: "Selfreg",
        BANK_SUBTYPE_BRUTE: "Brute",
    }
    return mapping.get((product_subtype or "").lower(), (product_subtype or "-").replace("_", " ").title())


def cc_subtype_label(product_subtype: str | None) -> str:
    mapping = {
        CC_SUBTYPE_CC: "CC",
        CC_SUBTYPE_NON_VBV: "NON-VBV",
        CC_SUBTYPE_STANDARD: "Standard",
        CC_SUBTYPE_WITH_ZIP: "With ZIP",
        CC_SUBTYPE_WITH_FULLZ: "With Fullz",
    }
    return mapping.get((product_subtype or "").lower(), (product_subtype or "-").replace("_", " ").title())


def bank_item_badge(product_type: str | None, product_subtype: str | None) -> str:
    return f"{bank_type_label(product_type)} / {bank_subtype_label(product_subtype)}"


def cc_item_badge(product_subtype: str | None) -> str:
    return f"CC / {cc_subtype_label(product_subtype)}"
