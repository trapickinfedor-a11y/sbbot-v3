"""
Seed data for Selfreg CC Card Names
Based on Mini App v2 data

Run after migration: sync_mini_app_v2
"""

SELFREG_CC_CARD_NAMES = {
    "chase": [
        "Freedom Unlimited",
        "Freedom Flex",
        "Sapphire Preferred",
        "Sapphire Reserve",
        "Ink Business Cash",
        "Ink Business Unlimited",
    ],
    "bofa": [
        "Customized Cash Rewards",
        "Unlimited Cash Rewards",
        "Travel Rewards",
        "Premium Rewards",
    ],
    "citi": [
        "Double Cash",
        "Custom Cash",
        "Premier",
        "Rewards+",
        "Simplicity",
    ],
    "wells": [
        "Active Cash",
        "Autograph",
        "Reflect",
        "Attune",
    ],
    "capital_one": [
        "Venture X",
        "Venture",
        "Quicksilver",
        "SavorOne",
        "Savor",
    ],
    "discover": [
        "it Cash Back",
        "it Miles",
        "it Student Cash Back",
        "it Chrome",
    ],
    "amex": [
        "Gold",
        "Platinum",
        "Blue Cash Preferred",
        "Blue Cash Everyday",
        "Green",
    ],
    "usbank": [
        "Altitude Connect",
        "Altitude Go",
        "Cash+",
        "Shopper Cash Rewards",
    ],
    "pnc": [
        "Cash Rewards",
        "Points Visa",
        "Core Visa",
    ],
    "td": [
        "Cash Credit Card",
        "First Class Visa",
        "Aeroplan Visa",
    ],
    "barclays": [
        "AAdvantage Aviator Red",
        "Wyndham Rewards Earner",
        "JetBlue Plus",
    ],
    "synchrony": [
        "Premier World Mastercard",
        "HOME Credit Card",
        "Car Care",
    ],
}


def generate_insert_sql():
    """Generate SQL INSERT statements for card names"""
    
    # First, we need to get category IDs
    # This assumes categories already exist from migration
    
    sql_statements = []
    
    sql_statements.append("-- Insert Selfreg CC Card Names")
    sql_statements.append("-- Run after sync_mini_app_v2 migration\n")
    
    for bank_code, card_names in SELFREG_CC_CARD_NAMES.items():
        sql_statements.append(f"-- {bank_code.upper()} cards")
        
        for position, card_name in enumerate(card_names, start=1):
            # Escape single quotes in card names
            escaped_name = card_name.replace("'", "''")
            
            sql = f"""INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, '{escaped_name}', {position}, TRUE
FROM selfreg_cc_categories
WHERE code = '{bank_code}'
ON CONFLICT DO NOTHING;"""
            
            sql_statements.append(sql)
        
        sql_statements.append("")  # Empty line between banks
    
    return "\n".join(sql_statements)


if __name__ == "__main__":
    print(generate_insert_sql())
