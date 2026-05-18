from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


PRICE_SCALE = Decimal("0.01")
WHOLE_DOLLAR = Decimal("1")


@dataclass(frozen=True)
class ModerationMarkupRule:
    code: str
    label: str
    kind: str
    value: Decimal


MARKUP_RULES = {
    "cc_zip_fullz": ModerationMarkupRule("cc_zip_fullz", "CC with ZIP/Fullz", "flat", Decimal("20")),
    "non_vbv_cc": ModerationMarkupRule("non_vbv_cc", "NON-VBV CC", "flat", Decimal("25")),
    "nfc": ModerationMarkupRule("nfc", "NFC", "percent", Decimal("20")),
    "otp": ModerationMarkupRule("otp", "OTP", "percent", Decimal("25")),
    "enroll": ModerationMarkupRule("enroll", "Enroll", "flat", Decimal("20")),
    "selfreg_ba": ModerationMarkupRule("selfreg_ba", "Selfreg BA", "percent", Decimal("20")),
    "selfregs_cc": ModerationMarkupRule("selfregs_cc", "Selfregs CC", "percent", Decimal("15")),
    "checks": ModerationMarkupRule("checks", "Checks", "percent", Decimal("15")),
    "logs": ModerationMarkupRule("logs", "Logs", "percent", Decimal("15")),
    "brute": ModerationMarkupRule("brute", "Brute", "percent", Decimal("15")),
    "document": ModerationMarkupRule("document", "Document", "percent", Decimal("20")),
    "fullz_personal": ModerationMarkupRule("fullz_personal", "Fullz Personal", "percent", Decimal("20")),
    "fullz_business": ModerationMarkupRule("fullz_business", "Fullz Business", "percent", Decimal("25")),
}


def normalize_base_price(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(PRICE_SCALE, rounding=ROUND_HALF_UP)


def _contains_any(*values: str | None, needles: tuple[str, ...]) -> bool:
    haystack = " ".join((value or "").lower() for value in values)
    return any(needle in haystack for needle in needles)


def suggest_markup_for_bank(bank) -> ModerationMarkupRule:
    if (getattr(bank, "product_type", "") or "").lower() == "enrol":
        return MARKUP_RULES["enroll"]
    if _contains_any(
        getattr(bank, "bank_name", None),
        getattr(bank, "bank_code", None),
        getattr(bank, "category", None),
        getattr(bank, "description", None),
        needles=("check", "cheque"),
    ):
        return MARKUP_RULES["checks"]
    if (getattr(bank, "product_subtype", "") or "").lower() == "selfreg":
        return MARKUP_RULES["selfreg_ba"]
    return MARKUP_RULES["logs"]


def suggest_markup_for_cc(item) -> ModerationMarkupRule:
    if _contains_any(
        getattr(item, "item_name", None),
        getattr(item, "cc_code", None),
        getattr(item, "category_code", None),
        getattr(item, "description", None),
        needles=("otp",),
    ):
        return MARKUP_RULES["otp"]
    if _contains_any(
        getattr(item, "item_name", None),
        getattr(item, "cc_code", None),
        getattr(item, "category_code", None),
        getattr(item, "description", None),
        needles=("non-vbv", "non vbv", "non_vbv"),
    ):
        return MARKUP_RULES["non_vbv_cc"]
    if _contains_any(
        getattr(item, "item_name", None),
        getattr(item, "cc_code", None),
        getattr(item, "category_code", None),
        needles=("selfreg", "self_reg"),
    ):
        return MARKUP_RULES["selfregs_cc"]
    if _contains_any(
        getattr(item, "item_name", None),
        getattr(item, "cc_code", None),
        getattr(item, "category_code", None),
        needles=("check", "cheque"),
    ):
        return MARKUP_RULES["checks"]
    return MARKUP_RULES["cc_zip_fullz"]


def suggest_markup_for_brute(item) -> ModerationMarkupRule:
    return MARKUP_RULES["brute"]


def suggest_markup_for_nfc(item) -> ModerationMarkupRule:
    return MARKUP_RULES["nfc"]


def suggest_markup_for_otp(item) -> ModerationMarkupRule:
    return MARKUP_RULES["otp"]


def suggest_markup_for_selfreg_cc(item) -> ModerationMarkupRule:
    return MARKUP_RULES["selfregs_cc"]


def suggest_markup_for_check(item) -> ModerationMarkupRule:
    return MARKUP_RULES["checks"]


def suggest_markup_for_enroll(item) -> ModerationMarkupRule:
    return MARKUP_RULES["enroll"]


def suggest_markup_for_selfreg_ba(item) -> ModerationMarkupRule:
    return MARKUP_RULES["selfreg_ba"]


def suggest_markup_for_document(item) -> ModerationMarkupRule:
    return MARKUP_RULES["document"]


def suggest_markup_for_fullz(item) -> ModerationMarkupRule:
    if (getattr(item, "fullz_type", "") or "").lower() == "business":
        return MARKUP_RULES["fullz_business"]
    return MARKUP_RULES["fullz_personal"]


def suggest_markup_for_logs(item) -> ModerationMarkupRule:
    return MARKUP_RULES["logs"]


def compute_final_price(base_price: Decimal | int | float | str, rule: ModerationMarkupRule) -> Decimal:
    base = normalize_base_price(base_price)
    if rule.kind == "percent":
        final_price = base * (Decimal("1") + (rule.value / Decimal("100")))
    else:
        final_price = base + rule.value
    return final_price.quantize(WHOLE_DOLLAR, rounding=ROUND_HALF_UP)


def get_markup_rule(rule_code: str) -> ModerationMarkupRule:
    rule = MARKUP_RULES.get(rule_code)
    if rule is None:
        raise KeyError(f"Unknown markup rule: {rule_code}")
    return rule


def _apply_rule(item, rule: ModerationMarkupRule, *, base_price: Decimal | int | float | str | None = None):
    base = normalize_base_price(
        base_price
        if base_price is not None
        else getattr(item, "base_price", None) or getattr(item, "seller_price", 0)
    )
    final_price = compute_final_price(base, rule)
    item.base_price = base
    item.final_price = final_price
    item.markup_percent = float(rule.value) if rule.kind == "percent" else None
    item.markup_fixed = rule.value.quantize(PRICE_SCALE, rounding=ROUND_HALF_UP) if rule.kind == "flat" else None
    item.markup_code = rule.code
    item.markup_kind = rule.kind
    item.markup_value = rule.value.quantize(PRICE_SCALE, rounding=ROUND_HALF_UP)
    setattr(item, "buyer_price", final_price)
    return rule


def _clear_markup_fields(item) -> None:
    item.markup_percent = None
    item.markup_fixed = None
    item.markup_code = None
    item.markup_kind = None
    item.markup_value = None


def apply_base_price(item, *, base_price: Decimal | int | float | str | None = None):
    base = normalize_base_price(
        base_price
        if base_price is not None
        else getattr(item, "base_price", None) or getattr(item, "seller_price", None) or getattr(item, "price", 0)
    )
    final_price = base.quantize(WHOLE_DOLLAR, rounding=ROUND_HALF_UP)
    item.base_price = base
    item.final_price = final_price
    setattr(item, "buyer_price", final_price)
    _clear_markup_fields(item)
    if hasattr(item, "price"):
        item.price = float(base)
    return None


def apply_bank_markup(bank, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    if not rule_code:
        return apply_base_price(bank, base_price=base_price)
    rule = get_markup_rule(rule_code)
    base = normalize_base_price(base_price if base_price is not None else getattr(bank, "base_price", None) or getattr(bank, "seller_price", 0))
    return _apply_rule(bank, rule, base_price=base)


def apply_cc_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    if not rule_code:
        return apply_base_price(item, base_price=base_price)
    rule = get_markup_rule(rule_code)
    base = normalize_base_price(base_price if base_price is not None else getattr(item, "base_price", None) or getattr(item, "seller_price", 0))
    return _apply_rule(item, rule, base_price=base)


def apply_brute_markup(item, *, base_price: Decimal | int | float | str | None = None):
    base = normalize_base_price(base_price if base_price is not None else getattr(item, "base_price", None) or getattr(item, "price", 0))
    rule = suggest_markup_for_brute(item)
    _apply_rule(item, rule, base_price=base)
    item.price = base
    return rule


def _apply_standard_markup(item, rule: ModerationMarkupRule, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    selected_rule = get_markup_rule(rule_code) if rule_code else rule
    base = normalize_base_price(base_price if base_price is not None else getattr(item, "base_price", None) or getattr(item, "seller_price", 0))
    return _apply_rule(item, selected_rule, base_price=base)


def apply_nfc_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    return _apply_standard_markup(item, suggest_markup_for_nfc(item), base_price=base_price, rule_code=rule_code)


def apply_otp_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    return _apply_standard_markup(item, suggest_markup_for_otp(item), base_price=base_price, rule_code=rule_code)


def apply_selfreg_cc_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    return _apply_standard_markup(item, suggest_markup_for_selfreg_cc(item), base_price=base_price, rule_code=rule_code)


def apply_check_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    return _apply_standard_markup(item, suggest_markup_for_check(item), base_price=base_price, rule_code=rule_code)


def apply_document_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    return _apply_standard_markup(item, suggest_markup_for_document(item), base_price=base_price, rule_code=rule_code)


def apply_fullz_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    return _apply_standard_markup(item, suggest_markup_for_fullz(item), base_price=base_price, rule_code=rule_code)


def _apply_legacy_price_markup(item, default_rule: ModerationMarkupRule, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    selected_rule = get_markup_rule(rule_code) if rule_code else default_rule
    base = normalize_base_price(base_price if base_price is not None else getattr(item, "base_price", None) or getattr(item, "seller_price", None) or getattr(item, "price", 0))
    _apply_rule(item, selected_rule, base_price=base)
    item.price = float(base)
    return selected_rule


def apply_enroll_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    return _apply_legacy_price_markup(item, suggest_markup_for_enroll(item), base_price=base_price, rule_code=rule_code)


def apply_selfreg_ba_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    return _apply_legacy_price_markup(item, suggest_markup_for_selfreg_ba(item), base_price=base_price, rule_code=rule_code)


def apply_logs_markup(item, *, base_price: Decimal | int | float | str | None = None, rule_code: str | None = None):
    return _apply_legacy_price_markup(item, suggest_markup_for_logs(item), base_price=base_price, rule_code=rule_code)
