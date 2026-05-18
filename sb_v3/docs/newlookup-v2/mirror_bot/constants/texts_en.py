from __future__ import annotations

"""
English texts for Mirror Bot
"""

class BotTexts:
    
    # ========== MAIN MESSAGES ==========
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
    
    # ========== PROFILE ==========
    PROFILE_TEXT = """👤 Profile

🧩 Your ID: {user_id}
💰 Balance: {balance} USD
🕓 Registered: {created_at}

🔗 Referral link: {referral_link}
👥 Number of referrals: {referrals_count}

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
🌐 ACTUAL LINK
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"""

    # ========== PAYMENT ==========
    TOPUP_STEP1 = """🪙 Step 1 — Choose Payment System"""

    TOPUP_STEP2 = """💵 Step 2 — Enter the Amount

💰 Enter the amount you wish to top-up:
10 — 5000 USD

⚠️ Minimum: $10 · Maximum: $5000

After you send the payment, the system will verify it automatically."""

    TOPUP_STEP2_CRYPTOPAY = """💵 Step 2 — Enter the Amount

💰 Enter the amount you wish to top-up:
10 — 5000 USD

⚠️ Minimum: $10 · Maximum: $5000

🚨 ATTENTION! CryptoBot is a third-party payment service!
Topping up your balance in CryptoBot itself does NOT credit money to us.
After topping up in CryptoBot, you MUST pay the invoice that we will create.

After you send the payment, the system will verify it automatically."""

    TOPUP_STEP3 = """🔗 Step 3 — Payment Link

Your payment link has been generated.

Tap below to complete your transaction:"""

    TOPUP_STEP3_CRYPTOPAY = """🔗 Step 3 — Payment Link

💰 Amount: ${amount} USD

⚠️ IMPORTANT! CryptoBot is a third-party service!
After topping up your balance in CryptoBot, you MUST pay the invoice using the link below.
Money will NOT arrive to your balance until you pay the invoice!

ℹ️ A payment processing fee applies

📌 Accepted cryptocurrencies:
   • USDT (TRC20/ERC20)
   • TON
   • BTC
   • ETH
   • USDC

⏱ Invoice expires in 1 hour

Tap below to complete your transaction:"""

    TOPUP_SUCCESS = """✅ Balance successfully topped-up by +{amount}$

💼 Your new balance has been updated automatically.

🔁 Type /menu to return to the main interface.

⚡ Thank you for using ONE PROJECT — your ecosystem for smart automation."""

    TOPUP_SUCCESS_SHORT = "✅ Payment successful! ${amount} has been added to your balance."

    # Auto payment notifications
    PAYMENT_AUTO_SUCCESS_TITLE = "✅ <b>Payment successfully received!</b>\n\n"
    PAYMENT_AUTO_SUCCESS_AMOUNT = "💵 Credited: <b>${amount}</b>\n"
    PAYMENT_AUTO_SUCCESS_BALANCE = "💰 Your balance: <b>${balance}</b>\n\n"
    PAYMENT_AUTO_SUCCESS_THANKS = "Thank you for your top-up! 🎉"
    
    PAYMENT_AUTO_EXPIRED_TITLE = "⏰ <b>Payment time expired</b>\n\n"
    PAYMENT_AUTO_EXPIRED_AMOUNT = "Payment for <b>${amount}</b> was cancelled.\n"
    PAYMENT_AUTO_EXPIRED_CREATE_NEW = "Create a new payment if you want to top up your balance."

    TOPUP_EXPIRED = """❌ Your payment session has expired or failed.

Please create a new payment link or contact Support if funds were sent but not credited.

🧠 Support → Create TICKET"""

    TOPUP_INVALID_AMOUNT = """❌ Invalid amount

⚠️ Minimum: $10 · Maximum: $5000

Please enter a valid amount:"""

    # ========== PAYMENT MESSAGES ==========
    PAYMENT_SYSTEM_NOT_CONFIGURED = "❌ Payment system is not configured"
    PAYMENT_ERROR_CREATING = "❌ Error creating payment: {error}"
    PAYMENT_SYSTEM_NOT_CONFIGURED_ALERT = "❌ Payment system not configured"
    PAYMENT_INVOICE_NOT_FOUND = "❌ Invoice not found"
    PAYMENT_CONFIRMED = "✅ Payment confirmed!"
    PAYMENT_CONFIRMED_TEXT = """✅ **Payment Confirmed!**

Amount: **${amount} {asset}**
Invoice ID: `{invoice_id}`
Paid at: {paid_at}"""
    PAYMENT_EXPIRED = "❌ Invoice expired"
    PAYMENT_WAITING = "⏳ Waiting for payment..."
    PAYMENT_CHECK_ERROR = "❌ Error checking payment"
    PAYMENT_CANCELLED_SUCCESS = "✅ Payment cancelled"
    PAYMENT_CANCELLED_TEXT = "❌ **Payment cancelled**"
    PAYMENT_CANCEL_FAILED = "❌ Could not cancel payment"
    PAYMENT_CANCEL_ERROR = "❌ Error cancelling payment"
    
    CRYPTOPAY_PAYMENT_FORMAT = """🪙 **{description}**
**Payment via CryptoBot**

**Amount to balance:** ${balance_amount:.2f} USD
**Platform fee ({fee_percent}%):** +${fee_amount:.2f} USD
━━━━━━━━━━━━━━━━━━━━━━
**Total to pay:** ${total_amount:.2f} USD

ℹ️ *Payment processing fee: {fee_percent}%*

📌 **Accepted cryptocurrencies:**
   • USDT (TRC20/ERC20)
   • TON
   • BTC
   • ETH
   • USDC

⏱ Invoice expires in 1 hour
🆔 Invoice ID: `{invoice_id}`"""

    CRYPTOMUS_PAYMENT_FORMAT = """💎 **{description}**
**Payment via Cryptomus**

**Amount to balance:** ${balance_amount:.2f} USD
**Platform fee ({fee_percent}%):** +${fee_amount:.2f} USD
━━━━━━━━━━━━━━━━━━━━━━
**Total to pay:** ${total_amount:.2f} USD

ℹ️ *Payment processing fee: {fee_percent}%*

📌 **Accepted cryptocurrencies:**
   • USDT (TRC20/ERC20/BEP20)
   • BTC, ETH, TON
   • LTC, TRX, USDC
   • And more...

⏱ Invoice expires in 1 hour
🆔 Order ID: `{order_id}`
🔖 Payment UUID: `{uuid}`"""

    # ========== MONEY TRANSFER ==========
    SEND_MONEY_TEXT = """💸 Send money to another user

Enter recipient User ID:"""

    SEND_MONEY_AMOUNT = """💰 Enter amount to send:

Your balance: {balance} USD"""
    
    SEND_MONEY_AMOUNT_SHORT = "💰 Enter amount to send:\n\nYour balance: ${balance}"

    SEND_MONEY_SUCCESS = """✅ Successfully sent ${amount} to user {user_id}

💰 Your new balance: ${balance}"""
    
    SEND_MONEY_SUCCESS_SHORT = "✅ Transfer successful!\n\n💸 Sent: ${amount}\n👤 To User ID: {recipient_id}\n💰 Your balance: ${balance}"
    
    SEND_MONEY_CONFIRM = "📝 **Confirm transfer**\n\n💸 Amount: ${amount}\n👤 To User ID: {recipient_id}\n\n💰 Your balance after: ${balance_after}\n\nConfirm transfer?"

    SEND_MONEY_INSUFFICIENT = """❌ Insufficient balance

💰 Your balance: ${balance}
💳 Required: ${amount}"""
    
    SEND_MONEY_INSUFFICIENT_SHORT = "❌ Insufficient balance!\n\nYour balance: ${balance}\nRequested: ${amount}"
    
    LANGUAGE_CHANGED = "✅ Language changed to {language}"
    MAIN_MENU_WITH_CHECKMARK = "✅ {menu_text}"

    # ========== REFERRAL SYSTEM ==========
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

    # ========== ORDERS ==========
    LOOKUP_MAIN = """🔎 Lookup Services

Choose a service to continue:"""

    ORDER_CONFIRMATION = """✅ Order Confirmation

Service: {service_name}
💰 Price: ${price}

📝 Your data has been validated!

Confirm order?"""

    ORDER_CREATED = """✅ **Order Created Successfully!**

🎲 **{product}**
💵 **Price:** ${price:.2f}
⏱ **ETA:** {eta}
💳 **Balance:** ${balance:.2f}

Your order has been sent to support team for processing."""
    
    ORDER_CREATED_DISCOUNT_SAVINGS = "\n💰 **Bulk discount (-{discount_percent}%):** ${savings:.2f}"

    ORDER_COMPLETED = """✅ Order #{order_id} completed!

Service: {service_name}

{result_text}

💰 Your balance: ${balance}

Type /menu to return to main menu."""

    BULK_ORDER_RESULT = """✅ Bulk Order #{order_id} completed!

Service: {service_name}

{items_text}

💰 Refund for NOT FOUND: +${refund}
💰 Your balance: ${balance}

Type /menu to return to main menu."""

    # ========== VALIDATION ==========
    INVALID_DATA = """❌ Invalid data format

{error_message}

📝 Example:
{example}"""

    INSUFFICIENT_BALANCE = """❌ Insufficient balance

💰 Your balance: ${balance}
💳 Required: ${price}

Please top-up your balance to continue."""

    # ========== MISC ==========
    RULES_TEXT = """📜 **User Policy / Terms of Service**

⚖️ **1. General Provisions**
• The bot provides informational, analytical and technical services only  
• The service is not a bank, financial institution, credit bureau, or government authority  
• By using the bot, you confirm that you are at least 18 years old and act in accordance with the laws of your country  
• The service may be unavailable or restricted in certain jurisdictions where such services are prohibited  

🔐 **2. Data & Privacy**
• You only submit data that you are legally allowed to process (your own data, data submitted with the owner’s consent, under a contract, law, etc.)  
• It is prohibited to submit personal data of third parties in violation of privacy and data protection laws  
• All data is processed automatically and used only to fulfill your request  
• The service does not undertake to store results and may automatically delete data after processing  
• We do not share your data with third parties, except where required by law  

🚫 **3. Prohibited Use**
It is strictly prohibited to use the service for:  
• Fraud, deception, financial schemes, money laundering, or any other illegal activity  
• Unauthorized access to accounts, devices, databases, or systems of third parties  
• Collecting, leaking, publishing, or selling personal data without a legal basis (doxxing or similar activities)  
• Circumventing requirements of banks, payment systems, government authorities, or regulators  
• Harassment, blackmail, extortion, threats, pressure, or discrimination against any person  
• Any actions that violate the laws of the country where you are located or whose laws apply to you  

👤 **4. User Responsibility**
• You fully and unconditionally bear responsibility for **how and for what purposes** you use the information and results obtained through the bot  
• The service administration cannot practically verify your intentions and does not control your compliance with the law  
• All risks associated with the use of the service (legal, financial, reputational, etc.) are borne by the user  
• In case of suspected violation of the rules or the law, the service may restrict, freeze, or block access without explanation and without compensation  

📎 **5. Limitation of Liability**
• All information and results are provided “as is” and for informational/technical purposes only  
• The service does not provide legal, financial, tax, or any other professional advice  
• The administration is not liable for any direct or indirect losses arising from the use or inability to use the service  
• The service may change functionality, rules, and conditions at any time without prior notice to the user  

🧾 **6. Changes to this Policy**
• This User Policy may be updated and supplemented from time to time  
• By continuing to use the bot after changes are made, you confirm your agreement with the updated version of the Policy  
• The current version of the Policy is always the one displayed in the bot at the moment of use  

✅ **7. Acceptance of the Policy**
• By launching the bot and continuing to use it, you confirm that you:
  – have carefully read this Policy and the Service Rules;  
  – fully understand their content;  
  – voluntarily and consciously agree to them;  
  – accept full responsibility for your use of the service.  

• If you **do not agree** with any part of this Policy, you must immediately stop using the bot and the service.  

**The service does not encourage or support any illegal activity.  
All responsibility for complying with the law lies with the user.**"""

    CALL_SERVICE_TEXT = """📦 *Hold Ups / Order Issues*

*Examples of tasks we solve:*
• Clarifying the status of a package stuck in customs
• Changing the shipping address after placing an order
• Resolving disputes with the store regarding a lost or damaged item
• Removing a "hold" from an order that was mistakenly blocked

✅ *To correctly process your request, we will need:*
• Tracking Number: (tracking number)
• Shop Name: (shop name)
• Full Name, Shipping Address, and Phone Number: (full name, shipping address, phone number)
📞 *Contact Support:* @one1caller

💳 *PayPal*

*Examples of tasks we solve:*
• Linking a new bank account or card to your account
• Removing limits and completing account verification
• Restoring access to a blocked account

✅ *To correctly process your request, please provide:*
• Personal Data: Name, address, SSN, date of birth
• Email Access: Linked email (can you receive emails?)
• Phone Access: Spoofed number (can you receive SMS messages?)
• Linked Accounts/Cards: Bank name, account/card type, last 4 digits
• Background Report (BG): May be required for linking accounts
• Task Description: Explain in detail what needs to be done
📞 *Contact Support:* @one1caller

📞 *Order Over the Phone*

*Examples of tasks we solve:*
• Purchasing limited items available only by phone
• Placing an order using specific discounts or conditions

✅ *To correctly process your request, we need the following information:*
• Contact for Call: Store number (where to call) and spoofed number
• Addresses: Name + billing address, Name + shipping address
• Order Details: Link to the item(s), quantity, color, size, etc
• Gift Cards: For E-gift — type, amount, recipient's name and email
• Payment Details: Full card details
📞 *Contact Support:* @one1caller

🏦 *Bank Calls / Loans*

*Examples of tasks we solve:*
• Unblocking online access after failed login attempts
• Verifying a large transfer (wire transfer)
• Resetting data for a credit card (CC reset)

⚠️ *Important: Every bank is unique. The more information you provide, the better.*

✅ *To correctly process your request, we will need:*
• Situation Description: Describe in detail what happened
• Contact for Call: Bank number and spoofed number (can you receive SMS?)
• Personal Data: Full Name, SSN, date of birth, address (with county)
• Access Details: Email (can you receive emails?), MMN, DL, EIN (for business)
• Secret Data: Full account/card number, login, verbal word, PIN, security Q&A
• History: Last 3-5 transactions (screenshot or text)
• Documents: BG (Background Check), CR (Credit Report) — if available
📞 *Contact Support:* @one1caller

💼 *Merchant Call*

*Examples of tasks we solve:*
• Setting up a merchant account and integrating payment systems
• Discussing contract terms and payment operations

✅ *To correctly process your request, we will need:*
• Contact for Call: Merchant number and the number to call from (SMS access available?)
• Personal Information: Name, SSN, Date of Birth, Address, Position
• Email Access: Email address (is email access available?)
• Company Details: Name, Website, EIN
• Business Description and Financial Information
• Account registration details and service payment information

📞 *Contact Support:* @one1caller"""

    BACK_TO_MAIN = "⬅️ Back to Main Menu"

    # ========== ERROR MESSAGES ==========
    ERROR_INVALID_DATA_FORMAT = "❌ Error: Invalid data format"
    ORDER_CREATED_ALERT = "✅ Order created!"
    ERROR_GENERAL = "❌ Error"
    TRY_ANOTHER_STATE = "Please try another state or check back later."
    PLEASE_TOPUP_BALANCE = "Please top up your balance to continue."
    PLEASE_CONTACT_SUPPORT = "Please contact support."
    FILE_ERROR_TITLE = "File Error"
    FILE_DELIVERY_FAILED = "Couldn't deliver file"
    USER_NOT_FOUND = "❌ User not found. Please /start"
    INVALID_PAYMENT_METHOD = "❌ Invalid payment method. Please start again with /profile"
    INVALID_USER_ID = "❌ Invalid User ID. Please enter a number."
    RECIPIENT_NOT_FOUND = "❌ Recipient not found. User with ID {recipient_id} does not exist in the system."
    USER_NOT_FOUND_CONTACT_SUPPORT = "❌ User not found. Please contact support."
    INVALID_AMOUNT_NUMBER = "❌ Invalid amount. Please enter a number."
    ERROR_CREATING_PAYMENT = "❌ Error creating payment: {error}\n\nPlease try again or contact support."
    PAYMENT_SUCCESSFUL = "✅ Payment successful!"
    PAYMENT_NOT_RECEIVED = "⏳ Payment not received yet..."
    ERROR_CHANGING_LANGUAGE = "❌ Error changing language"
    PLEASE_START_AGAIN = "⚠️ Please start the process again"

    # ========== VALIDATION ERRORS ==========
    MINIMUM_ENTRIES_REQUIRED = "❌ Minimum {min_items} entries required"
    MAXIMUM_ENTRIES_ALLOWED = "❌ Maximum {max_items} entries allowed"
    ENTRY_EMPTY_DATA = "❌ Entry #{entry}: Empty data"
    ERROR_PROCESSING_BULK = "❌ Error processing bulk entries:\n{error}"
    ORDER_CANCELLED = "❌ Order cancelled"

    # ========== DOCUMENTS ==========
    DOCUMENTS_MAIN = "Choose a category:"
    DOCUMENT_EXAMPLE_FORMAT = "John;Doe\n123 Main St;Los Angeles;{state};90210\n01/15/1990"
    DOCUMENT_INVALID_DATA = "❌ Invalid data format\n\n{issues_text}\n\n📝 Example:\n{example}"
    DOCUMENT_VALIDATION_ERROR = "❌ Invalid data:\n\n{errors}\n\n📝 Example:\n{example}"
    DOCUMENT_UNKNOWN_TYPE = "Unknown document type"
    PHOTO_CATALOG_HEADER = "📸 Photo Catalog\n\nSelect a document type:"
    SELECT_STATE = "Select state:"
    HIGH_QUALITY_DRAWING_COMING_SOON = "🧑‍🎨 High-Quality Drawing\n\n🚧 Coming soon...\n\nPlease contact support for custom orders."
    ROBOT_DRAWING_COMING_SOON = "🤖 Robot Drawing — Coming soon!"
    
    # ========== LOOKUP SERVICES ==========
    
    # ========== ESIM ==========
    ESIM_MAIN = "📶 eSIM\n\nChoose type:"
    ESIM_SMS_SELECT_OPERATOR = "🇺🇸 eSIM for SMS\n\nSelect operator:"
    ESIM_DATA_SELECT_OPERATOR = "📶 eSIM for Data\n\nSelect operator:"
    ESIM_SMS_SELECT_PERIOD = "📶 {operator} — SMS\n\nSelect period:"
    ESIM_DATA_SELECT_PLAN = "📶 {operator} — Data\n\nSelect data plan:"
    ESIM_SMS_ORDER_DETAILS = """📶 eSIM Order

🇺🇸 Type: SMS
📶 Operator: {operator}
⏳ Period: {period} month(s)
💵 Price per item: ${price}
🕒 Delivery: 5-10 minutes (auto)
📖 Instructions: [eSIM SMS](https://t.me/ONE_TUTORIAL/esim_sms)

Select quantity or buy 1 item:"""
    ESIM_DATA_ORDER_DETAILS = """📶 eSIM Order

📶 Type: Data
📶 Operator: {operator}
📦 Data: {gb} GB
💵 Price per item: ${price}
🕒 Delivery: 5-10 minutes (auto)
📖 Instructions: [eSIM Data](https://t.me/ONE_TUTORIAL/esim_data)

Select quantity or buy 1 item:"""
    ESIM_GV_SELECT = "📞 Google Voice\n\nChoose a product:"
    
    # ========== ACCOUNTS ==========
    ACCOUNTS_MAIN = "🧾 Subscriptions / Accounts\n\nChoose a category:"
    
    # ========== ADD INFO ==========
    ADDINFO_MAIN = "✍️ Add info in CR\n\nChoose a category:"
    
    # Add Info service formats
    ADDINFO_TU_FORMAT = "✍️ Add info in TU — ${price}\n⏱ ETA: 10-24 hours\n📖 Instructions: [Add info TU](https://t.me/ONE_TUTORIAL/78)\n\n📝 Enter data:\n\n{example}"
    ADDINFO_EX_FORMAT = "✍️ Add info in EX — ${price}\n⏱ ETA: 48-72 hours\n📖 Instructions: [Add info EX](https://t.me/ONE_TUTORIAL/79)\n\n📝 Enter data:\n\n{example}"
    ADDINFO_ALL_FORMAT = "✍️ Add info in ALL — ${price}\n⏱ ETA: 48-72 hours\n📖 Instructions: [Add info ALL](https://t.me/ONE_TUTORIAL/80)\n\n📝 Enter data:\n\n{example}"
    ADDINFO_BG_FORMAT = "✍️ Add info in BG — ${price}\n⏱ ETA: 48-72 hours\n📖 Instructions: [Add info BG](https://t.me/ONE_TUTORIAL/81)\n\n📝 Enter data:\n\n{example}"
    UNFREEZE_TU_FORMAT = "🔓 Unfreeze TU — ${price}\n⏱ ETA: 10-24 hours\n📖 Instructions: [Unfreeze TU](https://t.me/ONE_TUTORIAL/82)\n\n📝 Enter data:\n\n{example}"
    UNFREEZE_EX_FORMAT = "🔓 Unfreeze EX — ${price}\n⏱ ETA: 48-72 hours\n📖 Instructions: [Unfreeze EX](https://t.me/ONE_TUTORIAL/83)\n\n📝 Enter data:\n\n{example}"
    ADD_EMPLOYER_FORMAT = "🏢 Add employer — ${price}\n⏱ ETA: 10-24 hours\n📖 Instructions: [Add employer](https://t.me/ONE_TUTORIAL/84)\n\n📝 Enter data:\n\n{example}"
    
    # ========== FULLZ ==========
    FULLZ_MAIN = "🧰 PROS & FULLZ\n\nChoose type:"
    FULLZ_PERSONAL_PROFILES = "👤 Personal FULLZ\n\nChoose profile:"
    FULLZ_BUSINESS_MAIN = "🏢 BUSINESS FULLZ\n\nSelect state:"
    FULLZ_BUSINESS_SELECT_STATE = "🏢 BUSINESS FULLZ\n\nSelect state:"
    FULLZ_PROFILE_SELECT_STATE = "📍 Profile: {profile}\n\nSelect state:"
    FULLZ_SELECT_STATE = "📍 Select state:"
    
    # Business FULLZ specific texts
    FULLZ_STATE_SELECT_COMPANY = "📍 State: {state}\n🏢 Select Company Type:"
    FULLZ_COMPANY_SELECT_LOAN = "🏢 Company Type: {company_type}\n💰 Select Loan Size:"
    FULLZ_CS_SELECT_REPORT = "💳 Credit Score: {cs}\n📑 Select Report Group:"
    FULLZ_SELECT_AGE = "🎂 Select Age Group:"
    FULLZ_LOAN_SELECT_CS = "💰 Revenue: {loan_size}\n💳 Select Credit Score:"
    FULLZ_SELECT_GENDER = "👥 Select Gender:"
    FULLZ_SELECT_CARRIER_EXCLUSION = "📱 **Carrier Exclusion**\n\nExclude a specific carrier from the fullz? This costs extra."
    FULLZ_SELECT_BANK_EXCLUSION = "🏦 **Bank Exclusion**\n\nExclude a specific bank from the fullz? This costs extra."
    FULLZ_SELECT_REPORT_GROUP = "📑 Select Report Group:"
    FULLZ_COMPANY_SELECT_CEO_CS = "🏢 Company Type: {company_type}\n💳 Select CEO CS:"
    FULLZ_CEO_CS_SELECT_LOAN = "💳 CEO CS: {ceo_cs}\n💰 Select Loan Size:"
    FULLZ_REPORT_SELECT_QUANTITY = "📑 Report Group: {report}\n🔢 Select Quantity:"
    FULLZ_SELECT_QUANTITY = "🔢 Select Quantity:"
    FULLZ_STATE_SELECT_CS = "📍 State: {state}\n\nSelect Credit Score:"
    
    # FULLZ Order Summary
    FULLZ_BUSINESS_ORDER_TITLE = "🧾 **BUSINESS FULLZ ORDER**"
    FULLZ_PERSONAL_ORDER_TITLE = "📋 **PERSONAL FULLZ ORDER**"
    FULLZ_ORDER_QUANTITY = "📊 **Quantity:**"
    FULLZ_ORDER_STATE = "📍 **State:**"
    FULLZ_ORDER_COMPANY_TYPE = "🏢 **Company Type:**"
    FULLZ_ORDER_LOAN_SIZE = "💰 **Loan Size:**"
    FULLZ_ORDER_CREDIT_SCORE = "💳 **Credit Score:**"
    FULLZ_ORDER_AGE = "🎂 **Age:**"
    FULLZ_ORDER_GENDER = "👥 **Gender:**"
    FULLZ_ORDER_REPORT_GROUP = "📑 **Report Group:**"
    FULLZ_ORDER_TOTAL_COST = "💵 **Total Cost:**"
    FULLZ_ORDER_CURRENT_BALANCE = "💳 **Current Balance:**"
    FULLZ_ORDER_NEW_BALANCE = "📊 **New Balance:**"
    FULLZ_ORDER_DISCOUNT = "🎁 Discount:"
    FULLZ_ORDER_DISCOUNT_SAVE = "Save"
    
    FULLZ_RANDOM_ORDER_CREATED = """✅ Order Created Successfully!

🎲 **Random Personal FULLZ**
💰 **Price:** ${price}
⏱ **ETA:** {eta}
💳 **Balance:** ${balance}

Your order has been sent to support team for processing."""

    # FULLZ Support info
    FULLZ_SUPPORT_INFO = """📞 **FULLZ SUPPORT**

Here you can order specialized fullz that require individual processing:

🎖️ **Military Fullz** — military personnel data
✈️ **Work & Travel** — work visa profiles
🧒 **Young Fullz** — profiles under 25

For these and other custom requests, contact our seller directly:

👤 **Contact:** @fullz_support_seller

⏱ **Processing time:** 12-48 hours
💬 Describe your requirements in the chat and the seller will provide a quote."""

    ORDER_CREATION_ERROR = "❌ Error creating order. Please try again."
    
    # ========== PAYMENT BUTTONS ==========
    OPEN_PAYMENT_LINK = "💳 Open Payment Link"
    REFRESH_STATUS = "♻️ Refresh Status"
    CHECK_STATUS = "♻️ Check Status"
    PAY_INVOICE = "💳 Pay Invoice"
    PAY_WITH_CRYPTO = "💳 Pay with Crypto"
    
    # ========== LANGUAGE BUTTONS ==========
    LANG_RUSSIAN = "🇷🇺 Russian"
    LANG_ENGLISH = "🇬🇧 English"
    LANG_CHINESE = "🇨🇳 Chinese"
    
    # ========== SYSTEM MESSAGES ==========
    LANGUAGE_SAVED = "✅ Language saved!"
    USER_NOT_FOUND_ALERT = "❌ User not found"
    
    # ========== ERROR MESSAGES ==========
    ITEM_NOT_FOUND = "❌ Item not found"
    INSUFFICIENT_BALANCE_ALERT = "❌ Insufficient balance"
    INSUFFICIENT_BALANCE_DETAILED = "❌ Insufficient balance\nRequired: ${required}\nYour balance: ${balance}"
    INVALID_QUANTITY = "❌ Invalid quantity. Please enter 1-100."
    INVALID_FORMAT_NUMBER = "❌ Invalid format. Please enter a number (1-100)."
    PLEASE_ENTER_DATA = "❌ Please enter data\n\n📝 Example:\n{example}"
    INVALID_DATA_FORMAT = "❌ Invalid data format\n\n{issues_text}\n\n📝 Example:\n{example}"
    VALIDATION_ERROR = "❌ Validation error\n\n{errors}\n\n📝 Example:\n{example}"
    MIN_ENTRIES_REQUIRED = "❌ Minimum {min_items} entries required"
    MAX_ENTRIES_ALLOWED = "❌ Maximum {max_items} entries allowed"
    EMPTY_DATA_ENTRY = "❌ Entry #{entry_num}: Empty data"
    ENTRY_ISSUES = "❌ Entry #{entry_num}:\n{issues_text}"
    ENTRY_VALIDATION_ERROR = "❌ Entry #{entry_num}: {error_msg}"
    BULK_PROCESSING_ERROR = "❌ Error processing bulk entries:\n{error}"
    
    # ========== EXAMPLE FORMAT TEXTS ==========
    EXAMPLE_FORMATS_LABEL = "📝 Example formats:"
    REQUIRED_LABEL = "💡 Required:"
    OPTIONAL_LABEL = "💡 Optional:"
    ANY_FORMAT_WORKS = "✅ Any format works"
    DOB_OPTIONAL = "💡 DOB optional"
    NO_VALIDATION = "No validation"
    BUSINESS_NAME_REQUIRED = "💡 Business Name required"
    BULK_ENTRY_SEPARATOR = "📦 Enter 2-20 entries — EMPTY LINE between entries:"
    LEAVE_EMPTY_LINE = "📦 leave **ONE EMPTY LINE** between each record."
    CAN_SEND_ENTRIES = "➡️ You can send from 2 up to 20 entries in one message."
    NAME_ADDRESS_DOB_REQUIRED = "Name, Address, DOB"
    
    # ========== SUCCESS MESSAGES ==========
    ORDER_CREATED_SUCCESS = "✅ Order created!"
    ENTRIES_VALIDATED = "✅ {count} entries validated!\n\n"
    
    # ========== CONFIRMATION MESSAGES ==========
    BULK_TOTAL_CONFIRM = "💰 Total: ${price}\n\nConfirm?"
    ENTER_DATA_MMN = "📝 Enter data:\n\n{example}"
    ENTER_DATA_EIN = "📝 Enter data:\n\n{example}"
    
    # ========== GENERAL SERVICE MESSAGES ==========
    SERVICE_BULK_ORDER_HEADER = "📝 {service_name} — Bulk Order"
    SERVICE_PRICE_PER_ENTRY = "💰 Price per entry: ${price}"
    YOUR_DATA_LABEL = "📄 **Your data:**"
    DATA_RECEIVED_LABEL = "📄 Data received:"
    PLEASE_ENTER_YOUR_DATA = "📝 Please enter your data:"
    NO_VALIDATION_NOTE = "⚠️ NO VALIDATION - send any format"
    EXAMPLE_LABEL = "💡 Example:"
    PRICE_LABEL = "💵 Price:"
    PROCESSING_LABEL = "🕒 Processing:"
    MANUAL_PROCESSING = "Manual (support team)"
    NOTE_LABEL = "📝 Note:"
    REQUIRED_FIELDS_NOTE = "Name, address, SSN, DOB required (NO VALIDATION)"
    STATUS_AVAILABLE = "✅ Status: Available"
    PAYMENT_CONFIRMATION_NOTE = "Once payment is confirmed, our team will process your request."
    PRESS_BUY_NOW = "Press Buy Now to continue:"
    SELECT_A_SERVICE = "Select a service:"
    SELECT_A_PRODUCT_NOTE = "Select a product to view details and purchase"
    CLICK_BUY_NOW_NOTE = "Click 'Buy Now' to purchase this product"
    TAP_TOPUP_TO_ADD_FUNDS = "Tap /topup to add funds"
    CHOOSE_YOUR_LANGUAGE = "🌍 Choose your language / Выберите язык / 选择语言 / Elige idioma:"
    
    # ========== PRODUCTS ==========
    AVAILABLE_PRODUCTS = "🛍️ **Available Products**"
    CATEGORY_LABEL = "📂 **Category:**"
    STATE_LABEL = "🏛️ **State:**"
    TOTAL_LABEL = "📦 **Total:**"
    PRODUCTS_COUNT = "{total} products"
    PRODUCT_LABEL = "📦 **Product:**"
    PAID_LABEL = "💰 **Paid:**"
    NEW_BALANCE_LABEL = "💳 **New Balance:**"
    FILE_WILL_BE_DELETED = "⚠️ *File will be deleted in 1 hour for security*"
    PURCHASE_SUCCESSFUL = "✅ **Purchase Successful!**"
    PURCHASE_COMPLETED = "✅ **Purchase Completed!**"
    FILE_HAS_BEEN_SENT = "📁 **File has been sent to you!**"
    PURCHASE_SUCCESSFUL_SHORT = "Purchase successful! ✅"
    INSUFFICIENT_BALANCE_CAPS = "❌ **Insufficient Balance**"
    REQUIRED_LABEL_CAPS = "💰 **Required:**"
    YOUR_BALANCE_LABEL = "💳 **Your Balance:**"
    NEED_LABEL = "💸 **Need:**"
    PURCHASE_FAILED = "❌ **Purchase Failed**"
    FILE_DELIVERY_FAILED_SHORT = "❌ **File delivery failed:**"
    FILE_NOT_FOUND_SERVER = "File not found on server"
    BUY_NOW_BUTTON = "💰 Buy Now"
    BACK_TO_LIST_BUTTON = "🔙 Back to List"
    BACK_TO_STATES_BUTTON = "🔙 Back to States"
    FILE_TYPE_LABEL = "**File Type:**"
    DESCRIPTION_LABEL = "📝 **Description:**"
    YOUR_ORDER_READY = "✅ **Your order{order_text} is ready!**"
    YOUR_FILE_ATTACHED_BELOW = "📎 Your file is attached below:"
    VALIDATION_ERROR_SHORT = "❌ Validation error:"
    TOTAL_WITH_CONFIRM = "💰 Total: ${total}\n\nConfirm?"
    CONFIRM_PURCHASE_QUESTION = "Confirm purchase?"
    NO_PRODUCTS_AVAILABLE = "❌ **No products available**"
    INVALID_DATA_FORMAT_SHORT = "❌ Invalid data format"
    ERROR_LOADING_PRODUCTS = "❌ Error loading products"
    ERROR_LOADING_PAGE = "❌ Error loading page"
    ERROR_LOADING_PRODUCT = "❌ Error loading product"
    ERROR_PROCESSING_PURCHASE = "❌ Error processing purchase"
    ERROR_LOADING_STATES = "Error loading states"
    PRODUCT_NOT_FOUND = "❌ Product not found"
    PURCHASE_FAILED_SHORT = "❌ Purchase failed"
    PURCHASE_PINNED = "📌 Order #{order_id} data pinned in chat."
    PURCHASE_ARCHIVED = "📢 Data also sent to your archive channel."
    PURCHASE_HISTORY_TITLE = "📦 My Purchases"
    PURCHASE_HISTORY_EMPTY = "You do not have any purchases yet."
    PURCHASE_HISTORY_FILTER_CATEGORY = "🗂 By Categories"
    PURCHASE_HISTORY_FILTER_SELLER = "👨‍💼 By Sellers"
    PURCHASE_HISTORY_DETAILS = "Details"
    PURCHASE_HISTORY_SELECT_CATEGORY = "Choose a category filter:"
    PURCHASE_HISTORY_SELECT_SELLER = "Choose a seller filter:"
    HISTORY_FILTER_ALL = "📋 All Categories"
    ARCHIVE_SETUP_INSTRUCTIONS = "📁 Archive setup\n\n1. Create a private channel.\n2. Add this bot as administrator.\n3. Forward any message from that channel here."
    ARCHIVE_SETUP_SUCCESS = "✅ Archive channel connected successfully."
    ARCHIVE_SETUP_INVALID = "❌ Forward a message from a channel so I can save its ID."
    ARCHIVE_SETUP_BOT_NOT_ADMIN = "❌ Add this bot as channel administrator first, then try again."
    PHONE_EXAMPLE_FORMAT = "Example: +1 (320) 932-0202 or 3209320202"
    INVALID_DATA_FORMAT_WITH_EXAMPLE = "❌ Invalid data format\n\n{issues_text}\n\n📝 Example:\n{example}"
    
    # ========== FALLBACK ==========
    PLEASE_START_PROCESS_AGAIN = "⚠️ Please start the process again"
    UNHANDLED_ACTION = "⚠️"
    VIOLATION_OF_SERVICE_RULES = "Violation of service rules"

    RULES_ACCEPT_PROMPT = "📜 Please read and accept the rules before using the service:"
    RULES_ACCEPTED_SUCCESS = "✅ Rules accepted! Welcome to the service."
    RULES_DECLINED_MESSAGE = "❌ You must accept the rules to use the service. Send /start to try again."
    
    # ========== LOOKUP SERVICES ==========
    PHONE_SEARCH_HEADER = "📞 Phone Search\n\nChoose search type:"
    
    PHONE_LOOKUP_FORMAT = "📞 Phone Search — {service_name} — ${price}\n⏱ ETA: 4-15 minutes\n📖 Instructions: {tutorial_link}\n\nEnter phone number:\nFormat: +1 (320) 932-0202 or 3209320202"
    
    # Lookup service formats
    SSN_LOOKUP_FORMAT = "🧾 SSN & DOB Lookup — ${price}\n⏱ ETA: 4-10 minutes\n📖 Instructions: [SSN](https://t.me/ONE_TUTORIAL/85)\n\n📝 Enter data:\nNAME, ADRESS, DOB(if have)\n\n{example}"
    SSN_BULK_FORMAT = "🧾 BULK ORDER SSN — ${price} per entry\n⏱ ETA: 5-30 minutes\n📖 Instructions: [SSN Bulk](https://t.me/ONE_TUTORIAL/86)\n\n📝 Enter data:\nNAME, ADRESS, DOB(if have)\n\n{example}"
    # DL Examples
    DL_SINGLE_EXAMPLE = """📝 Example formats:
John Doe\n123 Main St, Los Angeles, CA, 90210\n 01/15/1990

💡 Required: Name, Address, DOB | ✅ Any format works"""

    DL_BULK_EXAMPLE = """📦 Enter 2-20 entries — EMPTY LINE between entries:

JOHN SMITH
123 MAIN ST NEW YORK NY 10001  
01/15/1990

JANE DOE
456 OAK AVE
LOS ANGELES CA 90001
01/15/1990

MARK TAYLOR  
789 ELM ST CHICAGO IL 60601  
01/15/1990

💡 Required: Name, Address, DOB | ✅ Any format works
📦 leave **ONE EMPTY LINE** between each record.
➡️ You can send from 2 up to 20 entries in one message."""

    # Background Examples  
    BG_SINGLE_EXAMPLE = """📝 Example formats:
John Doe\n123 Main St, Los Angeles, CA, 90210

💡 DOB optional | ✅ Any format works"""

    BG_BULK_EXAMPLE = """📦 Enter 2-20 entries — EMPTY LINE between entries:

Example 1:
John Doe  
123 Main St, Los Angeles, CA 90001  

Example 2:
123 Main St, 
Los Angeles, 
CA 
90001

Example 3:
John Doe  
123 Main St, Los Angeles, CA 90001
04/05/1995 apr 5,1995 04-05-1996

📦 **ONE EMPTY LINE** between each record.
➡️ DOB (Date of Birth) is optional.  
➡️ You can send from 2 up to 20 entries in one message."""

    # MMN Examples
    MMN_SINGLE_EXAMPLE = """📝 Example formats:
John Doe\n123 Main St, Los Angeles, CA, 90210

💡 DOB optional | ✅ Any format works"""

    MMN_BULK_EXAMPLE = """📦 Enter 2-20 entries — EMPTY LINE between entries:

Example 1:
John Doe  
123 Main St, Los Angeles, CA 90001  

Example 2:
123 Main St, 
Los Angeles, 
CA 
90001

Example 3:
John Doe  
123 Main St, Los Angeles, CA 90001
04/05/1995 apr 5,1995 04-05-1996

📦 leave **ONE EMPTY LINE** between each record.
➡️ DOB (Date of Birth) is optional.  
➡️ You can send from 2 up to 20 entries in one message."""

    # EIN Examples
    EIN_SINGLE_EXAMPLE = """(Kellington Protection Service, LLC)\nNAME BIZ/ DBA NAME\n123 Main St, Los Angeles, CA 90001

📝 Send any data in any format
💡 All information will be accepted as is"""

    EIN_BULK_EXAMPLE = """(Kellington Protection Service, LLC)\nNAME BIZ/ DBA NAME\n123 Main St, Los Angeles, CA 90001

📦 Enter 2-20 entries — EMPTY LINE between entries

📝 Send any data in any format
💡 All information will be accepted as is

📦 leave **ONE EMPTY LINE** between each record.
➡️ You can send from 2 up to 20 entries in one message."""

    # MVR Examples
    MVR_SINGLE_EXAMPLE = """John Doe\n123 Main St, Los Angeles, CA 90001\n04-05-1995 000-00-0000\nDL NUMBER; state issued\n✅ No validation required

📝 Send any data in any format
💡 All information will be accepted as is"""

    MVR_BULK_EXAMPLE = """
Example 1:
John Doe  
123 Main St, Los Angeles, CA 90001  
04-05-1995
000-00-0000
DL NUMBER; state issued 

Example 2:
123 Main St, 
Los Angeles, 
CA 
90001
apr 5,1995
000000000
DL NUMBER; state issued 

Example 3:
John Doe  
123 Main St, Los Angeles, CA 90001
04/05/1995
000-00-0000
DL NUMBER; state issued \n✅ No validation required

📦 Enter 2-20 entries — EMPTY LINE between entries

📝 Send any data in any format
💡 All information will be accepted as is

📦 leave **ONE EMPTY LINE** between each record.
➡️ You can send from 2 up to 20 entries in one message."""

    # CS Examples
    CS_SINGLE_EXAMPLE = """📝 Example formats:
John Doe\n123 Main St, Los Angeles, CA, 90210\n12/03/1998(if have)

💡 DOB optional | ✅ Any format works"""

    CS_BULK_EXAMPLE = """📦 Enter 2-20 entries — EMPTY LINE between entries:

Example 1:
John Doe  
123 Main St, Los Angeles, CA 90001  

Example 2:
123 Main St, 
Los Angeles, 
CA 
90001

Example 3:
John Doe  
123 Main St, Los Angeles, CA 90001
04/05/1995 apr 5,1995 04-05-1996

📦 leave **ONE EMPTY LINE** between each record.
➡️ You can send from 2 up to 20 entries in one message."""

    DL_LOOKUP_FORMAT = "🪪 Driver's License Lookup — ${price}\n⏱ ETA: 4-30 minutes\n📖 Instructions: [DL](https://t.me/ONE_TUTORIAL/87)\n\n📝 Enter data:\nNAME, ADRESS,DOB\n\n{example}"
    DL_BULK_FORMAT = "🪪 BULK ORDER DL — ${price} per entry\n⏱ ETA: 15-60 minutes\n📖 Instructions: [DL Bulk](https://t.me/ONE_TUTORIAL/88)\n\n📝 Enter data:\nNAME, ADRESS,DOB\n\n{example}"
    MVR_LOOKUP_FORMAT = "🚗 MVR Lookup — ${price}\n⏱ ETA: 10-90 minutes\n📖 Instructions: [MVR](https://t.me/ONE_TUTORIAL/91)\n\n📝 Enter data:\nNAME, ADRESS, SSN, DOB, DL\n\n{example}"
    MVR_BULK_FORMAT = "🚗 BULK ORDER MVR — ${price} per entry\n⏱ ETA: 15-120 minutes\n📖 Instructions: [MVR Bulk](https://t.me/ONE_TUTORIAL/2)\n\n📝 Enter data:\nNAME, ADRESS, SSN, DOB, DL\n\n{example}"
    FULL_MVR_LOOKUP_FORMAT = "📋 Full MVR Lookup — ${price}\n⏱ ETA: 10-150 minutes\n📖 Instructions: [Full MVR](https://t.me/ONE_TUTORIAL/3)\n\n📝 Enter data:\nNAME, ADRESS, SSN, DOB, DL\n\n{example}"
    CREDIT_SCORE_LOOKUP_FORMAT = "💳 Credit Score Lookup — ${price}\n⏱ ETA: 4-15 minutes\n📖 Instructions: [CS](https://t.me/ONE_TUTORIAL/89)\n\n📝 Enter data:\nNAME, ADRESS,DOB(if have)\n\n{example}"
    CS_BULK_FORMAT = "💳 BULK ORDER CS — ${price} per entry\n⏱ ETA: 10-30 minutes\n📖 Instructions: [CS Bulk](https://t.me/ONE_TUTORIAL/90)\n\n📝 Enter data:\nNAME, ADRESS,DOB(if have)\n\n{example}"
    BACKGROUND_LOOKUP_FORMAT = "🔍 Background Check — ${price}\n⏱ ETA: 4-15 minutes\n📖 Instructions: [BG](https://t.me/ONE_TUTORIAL/8)\n\n📝 Enter data:\nNAME, ADRESS,DOB(if have)\n\n{example}"
    BG_BULK_FORMAT = "🔍 BULK ORDER BG — ${price} per entry\n⏱ ETA: 10-30 minutes\n📖 Instructions: [BG Bulk](https://t.me/ONE_TUTORIAL/9)\n\n📝 Enter data:\nNAME, ADRESS,DOB(if have)\n\n{example}"
    MMN_LOOKUP_FORMAT = "👩‍👦 MMN Lookup — ${price}\n⏱ ETA: 4-15 minutes\n📖 Instructions: [MMN](https://t.me/ONE_TUTORIAL/10)\n\n📝 Enter data:\nNAME, ADRESS,DOB(if have)\n\n{example}"
    MMN_BULK_FORMAT = "👩‍👦 BULK ORDER MMN — ${price} per entry\n⏱ ETA: 10-30 minutes\n📖 Instructions: [MMN Bulk](https://t.me/ONE_TUTORIAL/11)\n\n📝 Enter data:\nNAME, ADRESS,DOB(if have)\n\n{example}"
    EIN_LOOKUP_FORMAT = "🏢 EIN Lookup — ${price}\n⏱ ETA: 4-20 minutes\n📖 Instructions: [EIN](https://t.me/ONE_TUTORIAL/12)\n\n📝 Enter data:\n\n{example}"
    EIN_BULK_FORMAT = "🏢 BULK ORDER EIN — ${price} per entry\n⏱ ETA: 10-40 minutes\n📖 Instructions: [EIN Bulk](https://t.me/ONE_TUTORIAL/13)\n\n📝 Enter data:\n\n{example}"
    
    # ========== BANKS ==========
    BANKS_MAIN = "🏦 BANKS\n\nChoose a category:"
    BANKS_MAIN_TEXT = BANKS_MAIN
    BANKS_SELECT_ITEM = "{category_name}\n\nSelect an item:"
    BANKS_INSUFFICIENT_BALANCE_MSG = "❌ Insufficient balance\n{detailed_msg}\n\n💡 Tap /topup to add funds"
    BANKS_ITEM_PRICE = "💵 Price: ${price} per item"
    BANKS_BULK_DISCOUNT = "💡 Bulk discount: 3+ (-{d3}%), 5+ (-{d5}%), 10+ (-{d10}%)"
    BANKS_ENTER_QTY = "{item_name}\n\n{price_text}\n{discount_text}\n\n{enter_quantity}"

    # ========== CREDIT REPORTS ==========
    CREDIT_REPORTS_HEADER = "📈 {provider}\n\nChoose a provider:"
    CREDIT_REPORT_FORMAT = """🛡️ **CR {service_name}**
**Details:** All credit cards (issuer, limit, balance, payment history), loans (mortgage, auto, student), public records (bankruptcies), inquiries, FICO/VantageScore credit rating.
—
💵 **Price:** ${single_price}
⏱ **ETA:** 4-30 minutes
📖 **Full Instructions:** {tutorial_link}
—
✅ **Ready to order?** Send the data for immediate processing.


📘 Input guide:
{example_text}

➡️ After sending, the bot validates and prepares data for the next steps."""
    
    # ========== DOCUMENTS ==========
    DOCUMENTS_PHOTO_BUTTON = "📸 Photo"
    
    # ========== ACCOUNTS ==========
    ACCOUNTS_BACK_BUTTON = "⬅️ Back"
    
    # ========== ADDINFO ==========
    ADDINFO_BACK_BUTTON = "⬅️ Back"
    
    # ========== QUANTITY INPUT ==========
    ENTER_QUANTITY = "📝 Enter quantity (1-100):"
    ENTER_CUSTOM_QUANTITY = "📝 Enter custom quantity (1-100):"
    
    # ========== SUPPORT TICKETS ==========
    MY_TICKETS_HEADER = "📋 **My Requests**\n\n"
    OPEN_TICKETS_HEADER = "🟢 **Open:**\n"
    NO_OPEN_TICKETS = "🟢 **No open tickets**"
    CLOSED_TICKETS_HEADER = "⚪️ **Closed (last 10):**"
    TICKET_NUMBER_PREFIX = "Ticket #"
    CATEGORY_PREFIX = "Category:"
    STATUS_PREFIX = "Status:"
    CREATED_PREFIX = "Created:"
    TICKET_HEADER = "🎫 **Ticket #{ticket_id}**"
    SENDER_YOU = "👤 You"
    SENDER_SUPPORT = "👨‍💼 Support"
    FILES_COUNT = "📎 Files: {count}"
    YOUR_TICKET_CREATED = "✅ **Your ticket #{ticket_id} has been created!**"
    OUR_SPECIALISTS_WILL_REPLY = "Our specialists will respond to you shortly."
    YOU_WILL_BE_NOTIFIED = "You will receive a notification when a response arrives."
    WANT_TO_ATTACH_FILES = "Would you like to attach files or screenshots?"
    YOUR_MESSAGE_SENT = "✅ Your message has been sent!"
    DESCRIBE_YOUR_PROBLEM = "📝 Describe your problem or question in detail.\n\nYou can also attach photos or files after sending the message."
    WRITE_YOUR_MESSAGE = "✍️ Write your message:\n\n(You can also send a photo or file)"
    SEND_FILES_INSTRUCTION = "📎 Send files, photos or documents.\n\nWhen finished, press /done"
    
    # ========== SUPPORT SYSTEM ==========
    SUPPORT_MAIN = """📞 Support

Choose your inquiry category:

💰 Payment - questions about payments and balance
📦 Product - questions about orders and services
💬 General - general questions
🤝 Partnership - partnership proposals"""

    SUPPORT_CHOOSE_CATEGORY = """📝 Describe your problem or question in detail.

You can also attach photos or files after sending the message."""

    SUPPORT_MESSAGE_TOO_SHORT = "❌ Message too short. Please describe the problem in more detail (minimum 10 characters)."

    SUPPORT_TICKET_CREATED = """✅ Your inquiry #{ticket_id} has been created!

Category: {category}
Status: Open

Our specialists will respond to you shortly.
You will receive a notification when a response arrives.

Would you like to attach files or screenshots?"""

    SUPPORT_TICKET_NOT_FOUND = "❌ Ticket not found"
    SUPPORT_ACCESS_DENIED = "❌ Access denied"
    SUPPORT_TICKET_CLOSED = "❌ This ticket is already closed. Create a new inquiry."
    SUPPORT_MESSAGE_EMPTY = "❌ Message cannot be empty."
    SUPPORT_MESSAGE_SENT = """✅ Your message has been sent!

Ticket #{ticket_id}
You will receive a notification when a response arrives."""

    SUPPORT_ATTACH_FILES = """📎 Send files, photos or documents.

When finished, press /done"""
    SUPPORT_FILES_ATTACHED = "✅ Files attached!"
    SUPPORT_FILE_ATTACHED = "✅ File attached! Send more or press /done"

    # ========== MY TICKETS ==========
    MY_TICKETS_MAIN = "📋 My Tickets"
    MY_TICKETS_OPEN = "🟢 Open:"
    MY_TICKETS_NO_OPEN = "🟢 No open tickets"
    MY_TICKETS_CLOSED = "⚪️ Closed (last 10):"

    # ========== TICKET DETAILS ==========
    TICKET_DETAIL_HEADER = """🎫 Ticket #{ticket_id}

Category: {category}
Status: {status}
Created: {created_at}

━━━━━━━━━━━━━━━━━"""

    TICKET_SENDER_YOU = "👤 You"
    TICKET_SENDER_SUPPORT = "👨‍💼 Support"
    TICKET_FILES_COUNT = "📎 Files: {count}"

    # ========== TICKET REPLIES ==========
    TICKET_WRITE_REPLY = """✍️ Write your message:

(You can also send a photo or file)"""

    # ========== ADMIN NOTIFICATIONS ==========
    ADMIN_MESSAGE_FROM = "📢 Message from Admin:"
    ADMIN_BROADCAST_FROM = "📢 Broadcast from Administration:"
    SUPPORT_NEW_REPLY = "💬 New reply in ticket #{ticket_id}"
    SUPPORT_REPLY_CATEGORY = "Category: {category}"
    SUPPORT_REPLY_SUBJECT = "Subject: {subject}"
    SUPPORT_REPLY_FROM_SUPPORT = "Support response:"
    SUPPORT_STATUS_CHANGED = "📊 Ticket status changed #{ticket_id}"
    SUPPORT_NEW_STATUS = "New status: {status}"

    # ========== DATA EXAMPLES ==========
    SSN_SINGLE_EXAMPLE = """📝 Example formats:
John Doe\n123 Main St, Los Angeles, CA, 90210\n01/15/1990(if have)

💡 DOB optional | ✅ Any format works"""

    SSN_BULK_EXAMPLE = """📦 Enter 2-20 entries — EMPTY LINE between entries:

JOHN SMITH
123 MAIN ST
NEW YORK NY 10001
123-45-6789 | 01/15/1990

JANE DOE
456 OAK AVE
LOS ANGELES CA 90001
234-56-7890 | 02/20/1985

MIKE WILSON
789 ELM RD
CHICAGO IL 60601
345-67-8901 | 03/10/1992

💡 Required: Name, Address, City, State, ZIP, SSN, DOB
✅ Any format works"""

    CR_SINGLE_EXAMPLE = """📝 Example formats:
Example 1:
John Doe  
123 Main St, Los Angeles, CA 90001  
04-05-1995
000-00-0000

Example 2:
123 Main St, 
Los Angeles, 
CA 
90001
apr 5,1995
000000000

Example 3:
John Doe  
123 Main St, Los Angeles, CA 90001
04/05/1995
000-00-0000

✅ Any format works"""

    CR_BULK_EXAMPLE = """📦 Enter 2-20 entries — EMPTY LINE between entries:

Example 1:
John Doe  
123 Main St, Los Angeles, CA 90001  
04-05-1995
000-00-0000

Example 2:
123 Main St, 
Los Angeles, 
CA 
90001
apr 5,1995
000000000

Example 3:
John Doe  
123 Main St, Los Angeles, CA 90001
04/05/1995
000-00-0000

💡 Required: Name, Address, City, State, ZIP, SSN, DOB
✅ Any format works"""

    # ========== BULK ORDER CONFIRMATIONS ==========
    BULK_ENTRIES_VALIDATED = "✅ {count} entries validated!"
    BULK_ENTRY_NUMBER = "📋 **Entry #{number}:**"
    BULK_PRICE_PER_ITEM = "💰 Price per item: ${price}"
    BULK_TOTAL_PRICE = "💰 Total: ${total}"
    BULK_CONFIRM_QUESTION = "Confirm?"

    # ========== CATEGORIES ==========
    CATEGORY_PAYMENT = "💰 Payment"
    CATEGORY_PRODUCT = "📦 Product"  
    CATEGORY_GENERAL = "💬 General"
    CATEGORY_PARTNERSHIP = "🤝 Partnership"

    # ========== STATUS ==========
    STATUS_OPEN = "Open"
    STATUS_IN_PROGRESS = "In Progress"
    STATUS_WAITING_USER = "Waiting for Response"
    STATUS_CLOSED = "Closed"

    # ========== SUPPORT BOT MESSAGES ==========
    ACCESS_DENIED = "❌ Access denied"
    ORDER_NOT_FOUND = "Order not found"
    ORDER_TAKEN = "✅ Order taken!"
    ORDER_ALREADY_TAKEN = "❌ Order already taken by another worker"
    WRONG_CATEGORY = "❌ You can't take this order (wrong category)"
    ORDER_MARKED_DONE = "✅ Order marked as DONE!"
    ORDER_MARKED_NF = "Order marked as NF, balance refunded"
    INFO_WILL_BE_ADDED = "✅ Info will be added in ~{hours}h"
    ERROR_ORDER_INFO_NOT_FOUND = "❌ Error: Order information not found"

    # ========== WEB PANEL BROADCASTS ==========
    WEB_ADMIN_MESSAGE_PREFIX = "📢 **Message from Admin:**\n\n"
    WEB_ADMIN_BROADCAST_PREFIX = "📢 **Broadcast from Administration:**\n\n"

    # ========== SUPPORT NOTIFICATIONS (HARDCODED) ==========
    SUPPORT_NEW_REPLY_TITLE = "💬 **New reply in ticket #{ticket_id}**\n\n"
    SUPPORT_REPLY_CATEGORY_LABEL = "Category: {category}\n"
    SUPPORT_REPLY_SUBJECT_LABEL = "Subject: {subject}\n\n"
    SUPPORT_REPLY_FROM_SUPPORT_LABEL = "**Support response:**\n"
    SUPPORT_STATUS_CHANGE_TITLE = "📊 **Ticket status changed #{ticket_id}**\n\n"
    SUPPORT_STATUS_SUBJECT_LABEL = "Subject: {subject}\n"
    SUPPORT_STATUS_NEW_STATUS_LABEL = "New status: {status}"

    # ========== HANDLER ERROR MESSAGES ==========
    INVALID_FORMAT_TRY_AGAIN = "❌ Invalid format. Please try again."
    ERROR_IN_ENTRY = "❌ Error in entry #{entry}:\n{issues}\n\n{example}"
    MINIMUM_ENTRIES_FOR_BULK = "❌ Minimum {min_items} entries required for bulk"
    MAXIMUM_ENTRIES_FOR_BULK = "❌ Maximum {max_items} entries allowed"
    
    # ========== BAN MESSAGES ==========
    ACCOUNT_BLOCKED_MESSAGE = """🚫 Account Blocked

Your account has been blocked.
Reason: {reason}

If you believe this is a mistake, please contact support."""

    # Сообщение о деактивации бота
    BOT_DEACTIVATED_MESSAGE = """🚫 Bot Deactivated

This bot has been temporarily deactivated by the administrator.

Please contact support for more information."""

    # Префикс сообщений от администратора
    ADMIN_MESSAGE_PREFIX = "📢 Message from Admin:\n\n"
    
    # Префикс массовой рассылки от администратора
    ADMIN_BROADCAST_PREFIX = "📢 Mass Broadcast from Administration:\n\n"
    
    # ========== PRODUCT DESCRIPTION TEMPLATE ==========
    PRODUCT_DESCRIPTION_TEMPLATE = """🏛️ {product_name}
📦 Category: {category}
💵 Price: ${price}
🕒 Delivery: {delivery}
📝 Description: [{description}]({tutorial_link})

✅ Status: Available
Once payment is confirmed, the goods will be delivered automatically.

Select quantity or buy 1 piece:"""
    
    # ========== PRODUCT DATA ==========
    PRODUCT_DATA = {
        # VCC BANKS
        "vcc_chime": {"category": "VCC", "delivery": "20-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/28", "description": "Virtual card with cash functionality"},
        "vcc_paypal": {"category": "VCC", "delivery": "20-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/29", "description": "PayPal + VCC + Crypto functionality"},
        "vcc_current": {"category": "VCC", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/30", "description": "Current bank virtual card"},
        "vcc_wise": {"category": "VCC", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/31", "description": "Wise personal virtual card"},
        "vcc_onepay": {"category": "VCC", "delivery": "20-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/32", "description": "One Pay virtual card"},
        "vcc_go2bank": {"category": "VCC", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/33", "description": "Go2Bank virtual card"},
        "vcc_venmo": {"category": "VCC", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/35", "description": "Venmo virtual card"},
        "vcc_kikoff": {"category": "VCC", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/36", "description": "Kikoff virtual card"},
        "vcc_shopify": {"category": "VCC", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/37", "description": "Shopify virtual card"},
        "vcc_varo": {"category": "VCC", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/38", "description": "Varo virtual card"},
        "vcc_blockchain": {"category": "VCC", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/39", "description": "Blockchain virtual card"},
        
        # PERSONAL BANKS
        "pers_ally": {"category": "PERSONAL", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/40", "description": "Ally personal account"},
        "pers_citi_gold": {"category": "PERSONAL", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/41", "description": "Citi Gold premium account"},
        "pers_usalliance": {"category": "PERSONAL", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/42", "description": "US Alliance personal account"},
        "pers_boa": {"category": "PERSONAL", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/43", "description": "Bank of America personal account"},
        "pers_alliant": {"category": "PERSONAL", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/44", "description": "Alliant Credit Union account"},
        "pers_pnc": {"category": "PERSONAL", "delivery": "40-180 min", "tutorial": "https://t.me/ONE_TUTORIAL/45", "description": "PNC Bank personal account"},
        
        # ACCOUNTS
        "bg_intelius_30": {"category": "AGGREGATORS", "delivery": "1-5 hours", "tutorial": "https://t.me/ONE_TUTORIAL/76", "description": "Intelius 30-day premium access"},
        "bg_truthfinder_30": {"category": "AGGREGATORS", "delivery": "1-5 hours", "tutorial": "https://t.me/ONE_TUTORIAL/77", "description": "TruthFinder 30-day premium access"},
        "bg_instantcheck_30": {"category": "AGGREGATORS", "delivery": "1-5 hours", "tutorial": "https://t.me/ONE_TUTORIAL/78", "description": "InstantCheckmate 30-day premium access"},
        "bg_whitepages_30": {"category": "AGGREGATORS", "delivery": "1-5 hours", "tutorial": "https://t.me/ONE_TUTORIAL/79", "description": "Whitepages 30-day premium access"}
    }

# ========== NOTIFICATION TEXTS ==========
    ORDER_COMPLETED_BULK_ITEM = "✅ Your bulk order item completed!"
    ORDER_COMPLETED_SINGLE = "✅ Your order completed!"
    ORDER_NOT_FOUND_BULK_ITEM = "❌ Your bulk order item - NOT FOUND"
    ORDER_NOT_FOUND_SINGLE = "❌ Your order - NOT FOUND"
    BULK_ORDER_COMPLETED = "🎯 Your bulk order completed!"
    DATA_NOT_FOUND_MESSAGE = "Unfortunately, we couldn't find the requested information.\nYour balance has been refunded automatically."
    REFUND_AMOUNT = "Refund amount"
    ORDER_UPDATE = "Order Update"
    ORDER_NUMBER = "Order"
    SERVICE = "Service"
    CUSTOMER_DATA = "Customer Data"
    RESULT = "Result"
    DETAILS = "Details"
    THANK_YOU_FOR_ORDER = "Thank you for your order! 🙏"

    ORDER_DETAILS = "📋 Order Details:"
    SERVICE_TEXT = "Service:"
    STATUS_TEXT = "Status:"
    ITEM_TEXT = "Item:"
    FILES_TEXT = "Files:"
    BALANCE_TEXT = "Balance:"
    REFUND_TEXT = "Refund:"
    RESULT_READY = "Your result is ready! 🎉"
    ORDER_COMPLETE_THANKS = "Your order is complete! Thank you for using our service! 🎉"
    NOT_FOUND_MESSAGE = "Unfortunately, we couldn't find information for this item.\nYour money has been refunded automatically. 💸"
    REFUND_PROCESSED = "Unfortunately, we couldn't find the requested information.\nYour money has been refunded automatically. 💸"

    FINAL_RESULTS = "📊 Final Results:"
    ITEMS_FOUND_DELIVERED = "Found & Delivered:"
    ITEMS_NOT_FOUND_REFUNDED = "Not Found (Refunded):"
    SUMMARY_TEXT = "💰 Summary:"
    ITEMS_FOUND = "Items found:"
    ITEMS_REFUNDED = "Items refunded:"
    CHECK_CHAT_HISTORY = "All individual results have been sent above. Check your chat history for each item's details and files."
    CURRENT_BALANCE = "Your current balance:"
    THANK_YOU = "Thank you for your order! 🙏"

    # ========== ADD INFO NOTIFICATIONS ==========
    ADD_INFO_PROCESSING_TITLE = "Your Add Info order is processing!"
    ADD_INFO_STATUS_IN_PROGRESS = "🔄 IN PROGRESS"
    ADD_INFO_PROCESSING_MESSAGE = "Your request is being processed. Please wait approximately **{hours} hours** for the result."
    ADD_INFO_NOTIFY_READY = "We'll notify you as soon as it's ready!"
    ADD_INFO_COMPLETED_TITLE = "Add Info order completed!"
    ADD_INFO_COMPLETED_MESSAGE = "✅ Information has been successfully added to your credit reports!"

    # ========== BALANCE NOTIFICATIONS ==========
    BALANCE_UPDATED = "Balance Update"
    BALANCE_ADDED = "Added"
    BALANCE_DEDUCTED = "Deducted"
    REASON = "Reason"
    CONTACT_SUPPORT_IF_QUESTIONS = "Contact support if you have any questions."

    # ========== ORDER CANCELLATION NOTIFICATIONS ==========
    ORDER_CANCELLED_TITLE = "⚠️ Order Cancelled"
    ORDER_CANCELLED_MESSAGE = "Your order #{order_id} has been cancelled."
    ORDER_CANCELLED_SERVICE = "Service: {service}"
    ORDER_CANCELLED_REFUND = "💰 Refund: ${amount:.2f} has been returned to your balance."
    ORDER_CANCELLED_BALANCE = "Your current balance: ${balance:.2f}"
    ORDER_CANCELLED_SUPPORT = "If you have any questions, please contact support."
    ORDER_CANCELLED_INVALID_DATA = "❌ Invalid data provided"
    ORDER_CANCELLED_NO_STOCK = "❌ Product not available"

    # ========== ADMIN MESSAGES ==========
    ADMIN_MESSAGE_TITLE = "Message from Admin"
    USER_BANNED_TITLE = "Account Status Update"
    USER_BANNED_MESSAGE = "Your account has been temporarily suspended."
    USER_UNBANNED_MESSAGE = "Your account has been reactivated."
    BAN_REASON = "Reason"

    # ========== PRODUCT DISPLAY ==========
    CATEGORY = "Category"
    PRICE = "Price"
    DELIVERY = "Delivery"
    DESCRIPTION = "Description"
    STATUS = "Status"
    AVAILABLE = "Available"
    PREMIUM_SERVICE = "Premium service"
    PAYMENT_CONFIRMATION_TEXT = "Once payment is confirmed, the goods will be delivered automatically"
    SELECT_QUANTITY_TEXT = "Select quantity or buy 1 piece"
    HOURS = "hours"

    # ========== BULK PURCHASE CONFIRMATION ==========
    BULK_PURCHASE_TITLE = "⚠️ **Purchase Confirmation**"
    BULK_PURCHASE_WARNING = "Please confirm your bulk purchase:"
    BULK_PURCHASE_PRODUCT = "📦 **Product:** {product_name}"
    BULK_PURCHASE_QUANTITY = "🔢 **Quantity:** {quantity} items"
    BULK_PURCHASE_UNIT_PRICE = "💵 **Unit Price:** ${unit_price:.2f}"
    BULK_PURCHASE_DISCOUNT = "💸 **Discount:** {discount_percent}%"
    BULK_PURCHASE_TOTAL = "💰 **Total Cost:** ${total_price:.2f}"
    BULK_PURCHASE_BALANCE = "💳 **Your Balance:** ${balance:.2f}"
    BULK_PURCHASE_NEW_BALANCE = "📊 **Balance After Purchase:** ${new_balance:.2f}"
    BULK_PURCHASE_CONFIRM_TEXT = "Are you sure you want to purchase {quantity} items for ${total_price:.2f}?"
    CONFIRM_PURCHASE = "✅ Confirm Purchase"
    CANCEL_PURCHASE = "❌ Cancel"
    PURCHASE_CANCELLED = "❌ Purchase cancelled"
    
    # ========== LOOKUP SUPPORT ==========
    LOOKUP_SUPPORT_TEXT = """💬 **Lookup Support**

    📋 **Available Services:**

    • **SSN & DOB** ($2.8-$3) - Social Security Number and Date of Birth lookup
    • **Credit Score** ($1.6-$2) - Credit score information
    • **DL** ($6.50-$7) - Driver's License lookup
    • **MVR** ($10-$11) - Motor Vehicle Report
    • **Full MVR** ($20-$22) - Complete Motor Vehicle Report
    • **Phone Search** - Various phone lookup services
    • **Background** ($1.5-$2) - Background check
    • **MMN** ($9) - Mother's Maiden Name lookup
    • **EIN** ($11) - Employer Identification Number lookup

    📞 **Need Help?**
    Contact our support team for assistance with any lookup service."""
    
    LOOKUP_SUPPORT_BANKS = """🔐 *Bank Brute Force Integration*

    *Available Services:*

    🏦 [Bank Logins Brute Force](your_link)
    • Automated login attempts
    • Multiple bank support
    • Custom wordlist integration

    💳 [Card Brute Force](your_link)
    • CC number generation
    • BIN-based generation
    • Validity checking

    (SOON)"""

    LOOKUP_SUPPORT_ACCOUNTS = """SOON"""

    # ========== ACTIONS / CANCEL ==========
    CANCELLED = "❌ Cancelled"

    # ========== EDUCATION ==========
    EDUCATION_MAIN = (
        "📚 *Education*\n\n"
        "📅 Subscriptions — time-based access to materials\n"
        "📖 Manuals — purchase files with instant delivery"
    )

    # ========== OTHER SERVICES ==========
    ANOTHER_SERVICES_MAIN = (
        "📞 *Other Services*\n\n"
        "Additional services and tools.\n"
        "For questions contact Support."
    )

