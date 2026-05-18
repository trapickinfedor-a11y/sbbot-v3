from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class MirrorBotConfig:
    referral_percent: float = 4.0
    min_topup: int = 10
    max_topup: int = 5000
    max_bulk_items: int = 20
    min_bulk_items: int = 2
    
    support_chat_id: int = 0
    
    # Main Bot username для реферальных ссылок
    main_bot_username: str = os.getenv("MAIN_BOT_USERNAME", "YourMainBot")
    
    # Crypto Pay (CryptoBot) API settings
    crypto_pay_token: str = os.getenv("CRYPTO_PAY_TOKEN", "")
    crypto_pay_testnet: bool = os.getenv("CRYPTO_PAY_TESTNET", "false").lower() == "true"
    crypto_pay_webhook_path: str = os.getenv("CRYPTO_PAY_WEBHOOK_PATH", "/crypto-pay-webhook")
    
    # Cryptomus API settings
    cryptomus_merchant_id: str = os.getenv("CRYPTOMUS_MERCHANT_ID", "")
    cryptomus_payment_key: str = os.getenv("CRYPTOMUS_PAYMENT_KEY", "")
    cryptomus_payout_key: str = os.getenv("CRYPTOMUS_PAYOUT_KEY", "")
    cryptomus_webhook_path: str = os.getenv("CRYPTOMUS_WEBHOOK_PATH", "/cryptomus-webhook")
    
    # Payment settings
    payment_fee_percent: float = 3.0  # 3% комиссия платформы (для CryptoPay)
    cryptomus_fee_percent: float = 2.0  # 2% комиссия для Cryptomus
    default_payment_method: str = os.getenv("DEFAULT_PAYMENT_METHOD", "cryptopay")  # "cryptopay" или "cryptomus"


mirror_bot_config = MirrorBotConfig()
