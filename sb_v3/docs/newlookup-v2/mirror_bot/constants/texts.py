class BotTexts:
    
    START_MESSAGE = """⚡ ONE PROJECT — not just a bot, but your gateway to the ONE Ecosystem.

🚀 Capabilities:
🔹 24/7 WORK — Always ON. Always Connected.
🔹 Instant access to ONE HUB, ONE LOOKUP, ONE BANKS
🔹 Manage everything in one secure dashboard

🔐 Safe. Fast. Smart.
🧩 ONE SYSTEM — ONE ACCESS — ONE CONTROL.

💡 Built for creators, operators, and builders of the new digital world.

🌍 Choose your language to continue 👇"""

    MAIN_MENU_TEXT = "🏠 Main Menu"
    
    PROFILE_TEXT = """👤 Profile

🧩 Your ID: {user_id}
💰 Balance: {balance} USD
🕓 Registered: {created_at}

🔗 Referral link: {referral_link}
👥 Number of referrals: {referrals_count}

————————————————
🌐 ACTUAL LINK
————————————————"""

    TOPUP_STEP1 = """🪙 Step 1 — Choose Payment System"""
    
    TOPUP_STEP2 = """💵 Step 2 — Enter the Amount

💰 Enter the amount you wish to top-up:
10 — 5000 USD

⚠️ Minimum: $10 · Maximum: $5000

After you send the payment, the system will verify it automatically."""

    TOPUP_STEP3 = """🔗 Step 3 — Payment Link

Your payment link has been generated.

Tap below to complete your transaction:"""

    TOPUP_SUCCESS = """✅ Balance successfully topped-up by +{amount}$

💼 Your new balance has been updated automatically.

🔁 Type /menu to return to the main interface.

⚡ Thank you for using ONE PROJECT — your ecosystem for smart automation."""

    TOPUP_EXPIRED = """❌ Your payment session has expired or failed.

Please create a new payment link or contact Support if funds were sent but not credited.

🧠 Support → Create TICKET"""

    TOPUP_INVALID_AMOUNT = """❌ Invalid amount

⚠️ Minimum: $10 · Maximum: $5000

Please enter a valid amount:"""

    SEND_MONEY_TEXT = """💸 Send money to another user

Enter recipient User ID:"""

    SEND_MONEY_AMOUNT = """💰 Enter amount to send:

Your balance: {balance} USD"""

    SEND_MONEY_SUCCESS = """✅ Successfully sent ${amount} to user {user_id}

💰 Your new balance: ${balance}"""

    SEND_MONEY_INSUFFICIENT = """❌ Insufficient balance

💰 Your balance: ${balance}
💳 Required: ${amount}"""

    REFERRAL_SYSTEM = """🤝 Referral Program — up to +25%

🔗 Your referral link:
{referral_link}

📊 4-level system:
1️⃣ Level 1 — 10%
2️⃣ Level 2 — 7%
3️⃣ Level 3 — 5%
4️⃣ Level 4 — 3%

👥 Total referrals: {count}
💵 Total earned: ${earned} USD

💰 Every purchase in your chain earns you a bonus — automatically!"""

    LOOKUP_MAIN = """🔎 Lookup Services

Choose a service to continue:"""

    ORDER_CONFIRMATION = """✅ Order Confirmation

Service: {service_name}
💰 Price: ${price}

📝 Your data has been validated!

Confirm order?"""

    ORDER_CREATED = """✅ Order #{order_id} created!

⏳ Your order is being processed...
You will be notified when it's ready.

💰 New balance: ${balance}"""

    ORDER_COMPLETED = """✅ Order #{order_id} completed!

Service: {service_name}

{result_text}

💰 Your balance: ${balance}

Type /menu to return to main menu."""

    ORDER_NOT_FOUND = """❌ Order #{order_id} - NOT FOUND

Service: {service_name}

💰 Refund: +${price}
💰 Your balance: ${balance}

Type /menu to return to main menu."""

    BULK_ORDER_RESULT = """✅ Bulk Order #{order_id} completed!

Service: {service_name}

{items_text}

💰 Refund for NOT FOUND: +${refund}
💰 Your balance: ${balance}

Type /menu to return to main menu."""

    INVALID_DATA = """❌ Invalid data format

{error_message}

📝 Example:
{example}"""

    INSUFFICIENT_BALANCE = """❌ Insufficient balance

💰 Your balance: ${balance}
💳 Required: ${price}

Please top-up your balance to continue."""

    RULES_TEXT = """📜 Service Rules

[Coming soon...]"""

    BACK_TO_MAIN = "⬅️ Back to Main Menu"

