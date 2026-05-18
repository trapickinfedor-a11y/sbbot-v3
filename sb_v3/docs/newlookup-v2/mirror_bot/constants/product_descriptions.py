from typing import Dict
# ServiceDescriptions интегрированы в основные файлы переводов

class ProductDescriptions:
    """
    Описания товаров с ценами, временем доставки и ссылками на инструкции
    """
    
    # VCC БАНКИ
    VCC_DESCRIPTIONS = {
        "vcc_chime": {
            "category": "VCC",
            "delivery": "20-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/28",
            "description": "Virtual card with cash functionality"
        },
        "vcc_paypal": {
            "category": "VCC", 
            "delivery": "20-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/29",
            "description": "PayPal + VCC + Crypto functionality"
        },
        "vcc_current": {
            "category": "VCC",
            "delivery": "40-180 min", 
            "tutorial": "https://t.me/ONE_TUTORIAL/30",
            "description": "Current bank virtual card"
        },
        "vcc_wise": {
            "category": "VCC",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/31", 
            "description": "Wise personal virtual card"
        },
        "vcc_onepay": {
            "category": "VCC",
            "delivery": "20-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/32",
            "description": "One Pay virtual card"
        },
        "vcc_go2bank": {
            "category": "VCC",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/33",
            "description": "Go2Bank virtual card"
        },
        "vcc_venmo": {
            "category": "VCC", 
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/35",
            "description": "Venmo virtual card"
        },
        "vcc_kikoff": {
            "category": "VCC",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/36", 
            "description": "Kikoff virtual card"
        },
        "vcc_shopify": {
            "category": "VCC",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/37",
            "description": "Shopify virtual card"
        },
        "vcc_neteller": {
            "category": "VCC",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/neteller",  # Нужна правильная ссылка
            "description": "Neteller virtual card"
        },
        "vcc_netspend": {
            "category": "VCC",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/netspend",  # Нужна правильная ссылка
            "description": "Netspend virtual card"
        },
        "vcc_greenfi": {
            "category": "VCC",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/greenfi",  # Нужна правильная ссылка
            "description": "GreenFi virtual card"
        },
        "vcc_quickbooks": {
            "category": "VCC",
            "delivery": "20-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/quickbooks",  # Нужна правильная ссылка
            "description": "QuickBooks virtual card"
        },
        "vcc_varo": {
            "category": "VCC",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/34",
            "description": "Varo virtual card"
        }
    }
    
    # ПЕРСОНАЛЬНЫЕ БАНКИ
    PERSONAL_DESCRIPTIONS = {
        "pers_citi": {
            "category": "PERSONAL BANKS",
            "delivery": "20-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/38",
            "description": "Citi personal banking account"
        },
        "pers_citi_gold": {
            "category": "PERSONAL BANKS", 
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/44",
            "description": "Citi Gold premium banking account"
        },
        "pers_usalliance": {
            "category": "PERSONAL BANKS",
            "delivery": "20-180 min", 
            "tutorial": "https://t.me/ONE_TUTORIAL/46",
            "description": "US Alliance personal account"
        },
        "pers_usbank": {
            "category": "PERSONAL BANKS",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/39",
            "description": "US Bank personal account"
        },
        "pers_chase": {
            "category": "PERSONAL BANKS",
            "delivery": "20-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/40",
            "description": "Chase personal banking"
        },
        "pers_wells": {
            "category": "PERSONAL BANKS",
            "delivery": "40-180 min", 
            "tutorial": "https://t.me/ONE_TUTORIAL/41",
            "description": "Wells Fargo personal account"
        },
        "pers_td": {
            "category": "PERSONAL BANKS",
            "delivery": "20-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/42",
            "description": "TD Bank personal account"
        },
        "pers_huntington": {
            "category": "PERSONAL BANKS",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/43",
            "description": "Huntington Bank personal account"
        },
        "pers_citizens": {
            "category": "PERSONAL BANKS",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/45",
            "description": "Citizens Bank personal account"
        },
        "pers_boa": {
            "category": "PERSONAL BANKS",
            "delivery": "20-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/47",
            "description": "Bank of America personal account"
        },
        "pers_ally": {
            "category": "PERSONAL BANKS",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/48",
            "description": "Ally Bank personal account"
        },
        "pers_alliant": {
            "category": "PERSONAL BANKS",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/49",
            "description": "Alliant Credit Union account"
        },
        "pers_pnc": {
            "category": "PERSONAL BANKS",
            "delivery": "20-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/50",
            "description": "PNC Bank personal account"
        },
        "pers_regions": {
            "category": "PERSONAL BANKS",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/regions",  # Нужна правильная ссылка
            "description": "Regions Bank personal account"
        },
        "pers_schwab": {
            "category": "PERSONAL BANKS",
            "delivery": "40-180 min",
            "tutorial": "https://t.me/ONE_TUTORIAL/schwab",  # Нужна правильная ссылка
            "description": "Charles Schwab personal account"
        }
    }
    
    # АККАУНТЫ
    ACCOUNT_DESCRIPTIONS = {
        "bg_intelius_30": {
            "category": "AGGREGATORS",
            "delivery": "1-5 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/76",
            "description": "Intelius 30-day premium access"
        },
        "bg_truthfinder_30": {
            "category": "AGGREGATORS",
            "delivery": "1-5 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/77",
            "description": "Truthfinder 30-day premium access"
        },
        "bg_instantcheck_30": {
            "category": "AGGREGATORS",
            "delivery": "1-5 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/78",  # Исправлено: было 78, должно быть 78
            "description": "InstantCheckmate 30-day premium access"
        },
        "bg_whitepages_30": {
            "category": "AGGREGATORS",
            "delivery": "1-5 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/79",  # Исправлено: было 79, должно быть 79
            "description": "Whitepages 30-day premium access"
        },
        "bg_beenverified": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/71",
            "description": "BeenVerified 7-day access"
        },
        "bg_truthfinder": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/72",
            "description": "Truthfinder 5-day access"
        },
        "bg_instantcheck": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/73",
            "description": "InstantCheckmate 5-day access"
        },
        "bg_intelius": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/74",
            "description": "Intelius 5-day access"
        },
        "bg_whitepages": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/75",
            "description": "Whitepages 5-day access"
        },
        "bg_mylife": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/mylife",
            "description": "MyLife background check access"
        },
        "lookup_monarch": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/66",
            "description": "Monarchmoney 10-day access"
        },
        "lookup_yodlee": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/67",
            "description": "Yodlee 14-day access"
        },
        "lookup_empower": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/68",
            "description": "Empower financial access"
        },
        "lookup_pocketguard": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/69",
            "description": "Pocketguard 7-day access"
        },
        "lookup_everydollar": {
            "category": "AGGREGATORS",
            "delivery": "1-3 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/70",
            "description": "Everydollar 14-day access"
        },
        # BUSINESS BANKS
        "biz_quickbooks": {
            "category": "BUSINESS BANKS",
            "delivery": "1-12 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/51",
            "description": "QuickBooks LLC/CORP business account"
        },
        "biz_bmo": {
            "category": "BUSINESS BANKS",
            "delivery": "1-12 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/52",
            "description": "BMO business banking account"
        },
        "biz_boa": {
            "category": "BUSINESS BANKS",
            "delivery": "1-12 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/53",
            "description": "Bank of America business account"
        },
        "biz_usbank": {
            "category": "BUSINESS BANKS",
            "delivery": "1-12 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/55",
            "description": "US Bank business account"
        },
        "biz_north_one": {
            "category": "BUSINESS BANKS",
            "delivery": "1-12 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/56",
            "description": "North One LLC/Corp account"
        },
        "biz_lili": {
            "category": "BUSINESS BANKS",
            "delivery": "1-12 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/58",
            "description": "Lili Business VCC account"
        },
        "biz_pnc": {
            "category": "BUSINESS BANKS",
            "delivery": "1-6 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/59",
            "description": "PNC Business account"
        },
        # ДОПОЛНИТЕЛЬНЫЕ BUSINESS BANKS (НЕ В ШАБЛОНЕ)
        "biz_capital_one": {
            "category": "BUSINESS BANKS",
            "delivery": "1-12 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/54",  # Предполагаемая ссылка
            "description": "Capital One Business account"
        },
        "biz_chase": {
            "category": "BUSINESS BANKS", 
            "delivery": "1-12 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/57",  # Предполагаемая ссылка
            "description": "Chase Business account"
        },
        "biz_wells": {
            "category": "BUSINESS BANKS",
            "delivery": "1-12 hours", 
            "tutorial": "https://t.me/ONE_TUTORIAL/wells_biz",  # Предполагаемая ссылка
            "description": "Wells Fargo Business account"
        },
        # CRYPTO BANKS
        "crypto_cashapp": {
            "category": "CRYPTO",
            "delivery": "1-6 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/60",
            "description": "Cash App + BTC crypto wallet"
        },
        "crypto_blockchain": {
            "category": "CRYPTO",
            "delivery": "1-6 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/61",
            "description": "Blockchain Gold exchange account"
        },
        "crypto_kraken": {
            "category": "CRYPTO",
            "delivery": "1-6 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/62",
            "description": "Kraken exchange account"
        },
        "crypto_coinbase": {
            "category": "CRYPTO",
            "delivery": "1-6 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/63",
            "description": "CoinBase exchange account"
        },
        "crypto_crypto_com": {
            "category": "CRYPTO",
            "delivery": "1-6 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/64",
            "description": "Crypto.com exchange account"
        },
        "crypto_binance": {
            "category": "CRYPTO",
            "delivery": "1-6 hours",
            "tutorial": "https://t.me/ONE_TUTORIAL/65",
            "description": "Binance exchange account"
        }
    }
    
    @classmethod
    def get_description(cls, product_id: str) -> Dict:
        """Получить описание товара по ID"""
        all_descriptions = {
            **cls.VCC_DESCRIPTIONS,
            **cls.PERSONAL_DESCRIPTIONS, 
            **cls.ACCOUNT_DESCRIPTIONS
        }
        return all_descriptions.get(product_id, {})
    
    @classmethod
    def format_product_text(cls, product_name: str, price: str, product_id: str, language: str = "en") -> str:
        """Форматировать текст описания товара"""
        desc = cls.get_description(product_id)
        
        # Попробуем получить детальное описание из ServiceDescriptions
        detailed_desc = ServiceDescriptions.get_service_description("bank_services", product_id, language)
        
        if not desc:
            # Базовое описание для товаров без детального описания
            description_text = detailed_desc if detailed_desc else "Premium service"
            return f"""🏛️ {product_name}
📦 Category: Product
💵 Price: ${price}
🕒 Delivery: 1-6 hours
📝 Description: {description_text}

✅ Status: Available
Once payment is confirmed, the goods will be delivered automatically.

Select quantity or buy 1 piece:"""
        
        # Используем детальное описание если есть, иначе краткое
        if detailed_desc:
            description_text = f"[{detailed_desc}]({desc['tutorial']})"
        else:
            description_text = f"[{desc['description']}]({desc['tutorial']})"
        
        return f"""🏛️ {product_name}
📦 Category: {desc['category']}
💵 Price: ${price}
🕒 Delivery: {desc['delivery']}
📝 Description: {description_text}

✅ Status: Available
Once payment is confirmed, the goods will be delivered automatically.

Select quantity or buy 1 piece:"""
