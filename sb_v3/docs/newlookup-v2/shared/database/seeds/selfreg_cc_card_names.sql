-- Insert Selfreg CC Card Names
-- Run after sync_mini_app_v2 migration

-- CHASE cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Chase Freedom Unlimited', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'chase'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Chase Freedom Flex', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'chase'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Chase Sapphire Preferred', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'chase'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Chase Sapphire Reserve', 4, TRUE
FROM selfreg_cc_categories
WHERE code = 'chase'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Chase Ink Business Cash', 5, TRUE
FROM selfreg_cc_categories
WHERE code = 'chase'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Chase Ink Business Unlimited', 6, TRUE
FROM selfreg_cc_categories
WHERE code = 'chase'
ON CONFLICT DO NOTHING;

-- BOFA cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Bank of America Customized Cash Rewards', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'bofa'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Bank of America Unlimited Cash Rewards', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'bofa'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Bank of America Travel Rewards', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'bofa'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Bank of America Premium Rewards', 4, TRUE
FROM selfreg_cc_categories
WHERE code = 'bofa'
ON CONFLICT DO NOTHING;

-- CITI cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Citi Double Cash', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'citi'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Citi Custom Cash', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'citi'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Citi Premier', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'citi'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Citi Rewards+', 4, TRUE
FROM selfreg_cc_categories
WHERE code = 'citi'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Citi Simplicity', 5, TRUE
FROM selfreg_cc_categories
WHERE code = 'citi'
ON CONFLICT DO NOTHING;

-- WELLS cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Wells Fargo Active Cash', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'wells'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Wells Fargo Autograph', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'wells'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Wells Fargo Reflect', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'wells'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Wells Fargo Attune', 4, TRUE
FROM selfreg_cc_categories
WHERE code = 'wells'
ON CONFLICT DO NOTHING;

-- CAPITAL_ONE cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Capital One Venture X', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'capital_one'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Capital One Venture', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'capital_one'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Capital One Quicksilver', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'capital_one'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Capital One SavorOne', 4, TRUE
FROM selfreg_cc_categories
WHERE code = 'capital_one'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Capital One Savor', 5, TRUE
FROM selfreg_cc_categories
WHERE code = 'capital_one'
ON CONFLICT DO NOTHING;

-- DISCOVER cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Discover it Cash Back', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'discover'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Discover it Miles', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'discover'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Discover it Student Cash Back', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'discover'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Discover it Chrome', 4, TRUE
FROM selfreg_cc_categories
WHERE code = 'discover'
ON CONFLICT DO NOTHING;

-- AMEX cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'American Express Gold', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'amex'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'American Express Platinum', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'amex'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'American Express Blue Cash Preferred', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'amex'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'American Express Blue Cash Everyday', 4, TRUE
FROM selfreg_cc_categories
WHERE code = 'amex'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'American Express Green', 5, TRUE
FROM selfreg_cc_categories
WHERE code = 'amex'
ON CONFLICT DO NOTHING;

-- USBANK cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'US Bank Altitude Connect', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'usbank'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'US Bank Altitude Go', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'usbank'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'US Bank Cash+', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'usbank'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'US Bank Shopper Cash Rewards', 4, TRUE
FROM selfreg_cc_categories
WHERE code = 'usbank'
ON CONFLICT DO NOTHING;

-- PNC cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'PNC Cash Rewards', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'pnc'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'PNC Points Visa', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'pnc'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'PNC Core Visa', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'pnc'
ON CONFLICT DO NOTHING;

-- TD cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'TD Cash Credit Card', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'td'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'TD First Class Visa', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'td'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'TD Aeroplan Visa', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'td'
ON CONFLICT DO NOTHING;

-- BARCLAYS cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Barclays AAdvantage Aviator Red', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'barclays'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Barclays Wyndham Rewards Earner', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'barclays'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Barclays JetBlue Plus', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'barclays'
ON CONFLICT DO NOTHING;

-- SYNCHRONY cards
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Synchrony Premier World Mastercard', 1, TRUE
FROM selfreg_cc_categories
WHERE code = 'synchrony'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Synchrony HOME Credit Card', 2, TRUE
FROM selfreg_cc_categories
WHERE code = 'synchrony'
ON CONFLICT DO NOTHING;
INSERT INTO selfreg_cc_card_names (category_id, card_name, position, is_active)
SELECT id, 'Synchrony Car Care', 3, TRUE
FROM selfreg_cc_categories
WHERE code = 'synchrony'
ON CONFLICT DO NOTHING;

