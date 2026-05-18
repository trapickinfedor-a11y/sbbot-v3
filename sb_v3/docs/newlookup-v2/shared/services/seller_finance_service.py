from __future__ import annotations

from decimal import Decimal

from shared.database.models import Seller


def _money(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class SellerFinanceService:
    @staticmethod
    def pending_balance(seller: Seller) -> Decimal:
        return _money(getattr(seller, "pending_balance", 0))

    @staticmethod
    def withdrawable_balance(seller: Seller) -> Decimal:
        return _money(getattr(seller, "withdrawable_balance", 0))

    @staticmethod
    def credit_pending(seller: Seller, amount: Decimal) -> None:
        seller.pending_balance = SellerFinanceService.pending_balance(seller) + _money(amount)

    @staticmethod
    def reverse_pending(seller: Seller, amount: Decimal) -> None:
        seller.pending_balance = max(
            Decimal("0"),
            SellerFinanceService.pending_balance(seller) - _money(amount),
        )

    @staticmethod
    def settle_pending(seller: Seller, amount: Decimal) -> None:
        settled_amount = _money(amount)
        SellerFinanceService.reverse_pending(seller, settled_amount)
        seller.withdrawable_balance = SellerFinanceService.withdrawable_balance(seller) + settled_amount
        seller.total_earned = _money(getattr(seller, "total_earned", 0)) + settled_amount

    @staticmethod
    def can_withdraw(seller: Seller, amount: Decimal) -> bool:
        return SellerFinanceService.withdrawable_balance(seller) >= _money(amount)

    @staticmethod
    def apply_withdrawal(seller: Seller, amount: Decimal) -> bool:
        withdrawal_amount = _money(amount)
        if not SellerFinanceService.can_withdraw(seller, withdrawal_amount):
            return False
        seller.withdrawable_balance = SellerFinanceService.withdrawable_balance(seller) - withdrawal_amount
        return True
