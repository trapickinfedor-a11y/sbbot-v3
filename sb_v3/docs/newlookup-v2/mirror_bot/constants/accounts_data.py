from typing import List, Dict, Optional
from mirror_bot.constants.prices import ServicePrices


class AccountsData:

    BG_ACCOUNTS = [
        {"id": "bg_beenverified", "name": "🔍 BeenVerified", "price": ServicePrices.ACC_BG_BEENVERIFIED},
        {"id": "bg_truthfinder", "name": "🔍 TruthFinder", "price": ServicePrices.ACC_BG_TRUTHFINDER},
        {"id": "bg_instantcheck", "name": "🔍 InstantCheckmate", "price": ServicePrices.ACC_BG_INSTANTCHECK},
        {"id": "bg_intelius", "name": "🔍 Intelius", "price": ServicePrices.ACC_BG_INTELIUS},
        {"id": "bg_whitepages", "name": "🔍 WhitePages", "price": ServicePrices.ACC_BG_WHITEPAGES},
        {"id": "bg_mylife", "name": "🔍 MyLife", "price": ServicePrices.ACC_BG_MYLIFE},
        {"id": "bg_intelius_30", "name": "🔍 Intelius - 30 days", "price": ServicePrices.ACC_BG_INTELIUS_30},
        {"id": "bg_truthfinder_30", "name": "🔍 Truthfinder - 30 days", "price": ServicePrices.ACC_BG_TRUTHFINDER_30},
        {"id": "bg_instantcheck_30", "name": "🔍 InstantCheckmate - 30 days", "price": ServicePrices.ACC_BG_INSTANTCHECK_30},
        {"id": "bg_whitepages_30", "name": "🔍 Whitepages - 30 days", "price": ServicePrices.ACC_BG_WHITEPAGES_30},
    ]

    LOOKUP_ACCOUNTS = [
        {"id": "lookup_monarch", "name": "💰 Monarch Money", "price": ServicePrices.ACC_LOOKUP_MONARCH},
        {"id": "lookup_yodlee", "name": "💰 Yodlee", "price": ServicePrices.ACC_LOOKUP_YODLEE},
        {"id": "lookup_empower", "name": "💰 Empower", "price": ServicePrices.ACC_LOOKUP_EMPOWER},
        {"id": "lookup_pocketguard", "name": "💰 PocketGuard", "price": ServicePrices.ACC_LOOKUP_POCKETGUARD},
        {"id": "lookup_everydollar", "name": "💰 EveryDollar", "price": ServicePrices.ACC_LOOKUP_EVERYDOLLAR},
    ]

    EMAIL_ACCOUNTS = [
        {"id": "email_gmail", "name": "📧 Gmail", "price": ServicePrices.ACC_EMAIL_GMAIL},
        {"id": "email_outlook", "name": "📧 Outlook / Hotmail", "price": ServicePrices.ACC_EMAIL_OUTLOOK},
        {"id": "email_yahoo", "name": "📧 Yahoo Mail", "price": ServicePrices.ACC_EMAIL_YAHOO},
        {"id": "email_icloud", "name": "📧 iCloud", "price": ServicePrices.ACC_EMAIL_ICLOUD},
        {"id": "email_protonmail", "name": "📧 ProtonMail", "price": ServicePrices.ACC_EMAIL_PROTONMAIL},
        {"id": "email_aol", "name": "📧 AOL Mail", "price": ServicePrices.ACC_EMAIL_AOL},
    ]

    AI_ACCOUNTS = [
        {"id": "ai_chatgpt", "name": "🤖 ChatGPT Plus", "price": ServicePrices.ACC_AI_CHATGPT},
        {"id": "ai_midjourney", "name": "🎨 Midjourney", "price": ServicePrices.ACC_AI_MIDJOURNEY},
        {"id": "ai_claude", "name": "🤖 Claude Pro", "price": ServicePrices.ACC_AI_CLAUDE},
        {"id": "ai_copilot", "name": "🤖 GitHub Copilot", "price": ServicePrices.ACC_AI_COPILOT},
        {"id": "ai_gemini", "name": "🤖 Gemini Advanced", "price": ServicePrices.ACC_AI_GEMINI},
    ]

    PROXY_ACCOUNTS = [
        {"id": "proxy_nordvpn", "name": "🔐 NordVPN", "price": ServicePrices.ACC_PROXY_NORDVPN},
        {"id": "proxy_expressvpn", "name": "🔐 ExpressVPN", "price": ServicePrices.ACC_PROXY_EXPRESSVPN},
        {"id": "proxy_surfshark", "name": "🔐 Surfshark", "price": ServicePrices.ACC_PROXY_SURFSHARK},
        {"id": "proxy_ipvanish", "name": "🔐 IPVanish", "price": ServicePrices.ACC_PROXY_IPVANISH},
        {"id": "proxy_911s5", "name": "🔐 911 S5 Proxy", "price": ServicePrices.ACC_PROXY_911S5},
    ]

    CATEGORIES = {
        "bg": {"name": "🔍 Background Accounts", "items": BG_ACCOUNTS},
        "lookup": {"name": "💰 Lookup BA", "items": LOOKUP_ACCOUNTS},
        "email": {"name": "📧 Email Accounts", "items": EMAIL_ACCOUNTS},
        "ai": {"name": "🤖 AI Accounts", "items": AI_ACCOUNTS},
        "proxy": {"name": "🔐 Proxy / VPN", "items": PROXY_ACCOUNTS},
    }

    @classmethod
    def get_account_by_id(cls, account_id: str) -> Optional[Dict]:
        for cat_data in cls.CATEGORIES.values():
            for item in cat_data["items"]:
                if item["id"] == account_id:
                    return item
        return None

    @classmethod
    def get_category_items(cls, category: str) -> List[Dict]:
        return cls.CATEGORIES.get(category, {}).get("items", [])

    @classmethod
    def get_account_category(cls, account_id: str) -> Optional[str]:
        for category_key, category_data in cls.CATEGORIES.items():
            for account in category_data["items"]:
                if account["id"] == account_id:
                    return category_key
        return None

