from typing import List, Dict
from mirror_bot.constants.prices import ServicePrices


class AddInfoData:
    
    ADD_CR_ITEMS = [
        {"id": "addcr_all", "name": "➕ Add phone + address + employer (all CR)", "price": ServicePrices.ADD_INFO_PHONE_ADDRESS_EMPLOYER_ALL},
        {"id": "addcr_phone_addr", "name": "➕ Add phone + address (all CR)", "price": ServicePrices.ADD_INFO_PHONE_ADDRESS_ALL},
        {"id": "addcr_phone_all", "name": "📞 Add phone (all CR)", "price": ServicePrices.ADD_INFO_PHONE_ALL},
        {"id": "addcr_addr_all", "name": "🏠 Add address (all CR)", "price": ServicePrices.ADD_INFO_ADDRESS_ALL},
        {"id": "addcr_phone_ex", "name": "📞 Add phone (EX)", "price": ServicePrices.ADD_INFO_PHONE_EX},
        {"id": "addcr_addr_ex", "name": "🏠 Add address (EX)", "price": ServicePrices.ADD_INFO_ADDRESS_EX},
        {"id": "addcr_phone_tu", "name": "📞 Add phone (TU)", "price": ServicePrices.ADD_INFO_PHONE_TU},
        {"id": "addcr_addr_tu", "name": "🏠 Add address (TU)", "price": ServicePrices.ADD_INFO_ADDRESS_TU},
    ]
    
    ADD_BG_ITEMS = [
        {"id": "addbg_phone_addr", "name": "➕ Add phone + address (BG)", "price": ServicePrices.ADD_INFO_BG_PHONE_ADDRESS},
        {"id": "addbg_phone", "name": "📞 Add phone (BG)", "price": ServicePrices.ADD_INFO_BG_PHONE},
        {"id": "addbg_addr", "name": "🏠 Add address (BG)", "price": ServicePrices.ADD_INFO_BG_ADDRESS},
    ]
    
    ADD_EMPLOYER_ITEMS = [
        {"id": "addemp_tu", "name": "🏢 Add employer (TU)", "price": ServicePrices.ADD_EMPLOYER_TU},
        {"id": "addemp_update", "name": "👔 Update current employer", "price": ServicePrices.UPDATE_EMPLOYER},
        {"id": "addemp_remove", "name": "🧾 Remove outdated employer", "price": ServicePrices.REMOVE_EMPLOYER},
    ]
    
    UNFREEZE_ITEMS = [
        {"id": "unfreeze_tu", "name": "🧩 Permanent Unfreeze (TU)", "price": ServicePrices.UNFREEZE_TU},
        {"id": "unfreeze_ex", "name": "🛡️ Permanent Unfreeze (EX)", "price": ServicePrices.UNFREEZE_EX},
    ]
    
    CATEGORIES = {
        "addcr": {"name": "📈 Add Info in Credit Report", "items": ADD_CR_ITEMS},
        "addbg": {"name": "🧾 Add Info in BG", "items": ADD_BG_ITEMS},
        "employer": {"name": "🏢 Add Employer to CR", "items": ADD_EMPLOYER_ITEMS},
        "unfreeze": {"name": "❄️ Unfreeze CR", "items": UNFREEZE_ITEMS},
    }
    
    @classmethod
    def get_item_by_id(cls, item_id: str) -> Dict:
        for cat_data in cls.CATEGORIES.values():
            for item in cat_data["items"]:
                if item["id"] == item_id:
                    return item
        return None
    
    @classmethod
    def get_category_items(cls, category: str) -> List[Dict]:
        return cls.CATEGORIES.get(category, {}).get("items", [])

