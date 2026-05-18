"""
Hardcoded bank catalog - fallback when BankItem is empty.
Must match mirror_bot/constants/bank_data.py structure (ids).
"""
from decimal import Decimal

VCC_BANKS = [
    {"id": "vcc_chime", "name": "🤩 Chime VCC"},
    {"id": "vcc_paypal", "name": "🏦 PayPal VCC"},
    {"id": "vcc_onepay", "name": "🤩 One Pay VCC"},
    {"id": "vcc_current", "name": "🤩 Current VCC"},
    {"id": "vcc_neteller", "name": "🏦 Neteller VCC"},
    {"id": "vcc_wise", "name": "🎰 Wise Personal VCC"},
    {"id": "vcc_netspend", "name": "🤩 Netspend VCC"},
    {"id": "vcc_greenfi", "name": "🤩 GreenFi VCC"},
    {"id": "vcc_quickbooks", "name": "🏦 QuickBooks VCC"},
    {"id": "vcc_go2bank", "name": "🏛️ Go2Bank + VCC"},
    {"id": "vcc_venmo", "name": "🏛️ Venmo"},
    {"id": "vcc_kikoff", "name": "🏛️ Kikoff"},
    {"id": "vcc_shopify", "name": "🏛️ Shopify"},
    {"id": "vcc_varo", "name": "🏛️ Varo + VCC"},
]

PERSONAL_BANKS = [
    {"id": "pers_citi", "name": "🏦 Citi Personal"},
    {"id": "pers_citi_gold", "name": "🏦 Citi Gold Bank"},
    {"id": "pers_usalliance", "name": "🏦 Usalliance"},
    {"id": "pers_usbank", "name": "🏦 US Bank"},
    {"id": "pers_ally", "name": "🏦 Ally Bank"},
    {"id": "pers_regions", "name": "🏦 Regions Bank"},
    {"id": "pers_chase", "name": "🏦 Chase"},
    {"id": "pers_wells", "name": "🏦 WellsFargo"},
    {"id": "pers_schwab", "name": "🏦 Charles Schwab"},
    {"id": "pers_citizens", "name": "🏦 Citizens Bank"},
    {"id": "pers_huntington", "name": "🏦 Huntington Bank"},
    {"id": "pers_td", "name": "🏦 TD bank"},
    {"id": "pers_boa", "name": "🏦 BankOFAmerica"},
    {"id": "pers_alliant", "name": "🏦 Alliant Cu"},
    {"id": "pers_pnc", "name": "🏦 Pnc Bank"},
]

BUSINESS_BANKS = [
    {"id": "biz_quickbooks", "name": "🏢 QuickBooks (LLC/ CORP)"},
    {"id": "biz_bmo", "name": "🏢 Bmo Buisness"},
    {"id": "biz_boa", "name": "🏢 BankOFAmerica"},
    {"id": "biz_usbank", "name": "🏢 Us Buisness"},
    {"id": "biz_north_one", "name": "🏢 North One (LLC/Corp)"},
    {"id": "biz_lili", "name": "🏢 Lili Business Vcc"},
    {"id": "biz_pnc", "name": "🏢 Pnc Business"},
    {"id": "biz_capital_one", "name": "🏢 Capital One Business"},
    {"id": "biz_chase", "name": "🏢 Chase Business"},
    {"id": "biz_wells", "name": "🏢 Wells Fargo Business"},
]

CRYPTO_BANKS = [
    {"id": "crypto_cashapp", "name": "💸 Cash App + BTC"},
    {"id": "crypto_blockchain", "name": "💸 Blockchain Gold"},
    {"id": "crypto_kraken", "name": "💸 Kraken"},
    {"id": "crypto_coinbase", "name": "💸 CoinBase"},
    {"id": "crypto_crypto_com", "name": "💸 Crypto.com"},
    {"id": "crypto_binance", "name": "💸 Binance"},
]

MERCHANT_BANKS = [
    {"id": "mrch_mercury",      "name": "🔷 Mercury LLC"},
    {"id": "mrch_rho",          "name": "🔷 Rho LLC"},
    {"id": "mrch_relay",        "name": "🔷 Relay LLC Europe/USA Owner"},
    {"id": "mrch_revolut_biz",  "name": "🔷 Revolut Business LLC"},
    {"id": "mrch_bluevine",     "name": "🔷 Blue Vine LLC"},
    {"id": "mrch_novobank",     "name": "🔷 Novobank LLC"},
    {"id": "mrch_wise_biz",     "name": "🔷 Wise Business LLC"},
    {"id": "mrch_payoneer",     "name": "🔷 Payoneer LLC"},
    {"id": "mrch_revolut_pers", "name": "🔷 Revolut Personal on EMU"},
]

BANK_CATALOG = {
    "vcc": VCC_BANKS,
    "personal": PERSONAL_BANKS,
    "business": BUSINESS_BANKS,
    "crypto": CRYPTO_BANKS,
    "merchant": MERCHANT_BANKS,
}
