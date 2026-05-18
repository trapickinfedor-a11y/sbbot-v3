# UploadsTab Full Rewrite Spec

## BANKS form
- [ ] Registration Date: 3 fields MM + DD + YYYY (separate inputs, auto-advance)
- [ ] Balance: placeholder "e.g. $5,000" only, no hint text
- [ ] Phone Access (OTP): toggle ON/OFF
  - IF ON: field "Days" + toggle "Can extend rental?" 
  - IF OFF: toggle "Can swap number?"
- [ ] Email Access: toggle
- [ ] Return Item toggle → opens dropdown/stepper for days (1/3/7/14/30)
- [ ] Add custom bank: search list + "Add custom" button
- [ ] Product Type: preloaded dropdown per category
- [ ] Upload .txt / .zip file at bottom
- [ ] Price ($) required

## BRUTE form (single)
- [ ] Bank: preloaded list + Add custom bank (request via moderation)
- [ ] Attributes: AUTO-DETECTED from bulk line fields that are non-empty
  - Bulk format: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price
  - Auto-detect: if AN present → tag "AN", if RN → tag "RN", if NAME → tag "NAME", etc.
  - Can also add custom bank request for validation in bulk
- [ ] Exact Balance field
- [ ] Account Type: CHECKING/SAVINGS/BUSINESS/MONEY MARKET
- [ ] Toggles (single mode): Have Login / Have AN:RN / Have Name+Address / Additional Info / Docs
- [ ] Bulk mode:
  - Format: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price
  - Auto-detect attributes from non-empty fields per line
  - Show tags per line: [AN] [RN] [NAME] [ADDR] [ZIP] etc.
  - Price per item from last field OR separate price field
  - Show bank breakdown summary
  - File upload .txt
- [ ] Price ($) required

## CC form (single)
- [ ] Fields: Number / Exp / CVV / Name / ZIP / State / Country / Type
- [ ] BANK field: AUTO-DETECT from BIN (first 6 digits of card number) — show detected bank name
- [ ] NON VBV: checkbox/badge visible in the section navigation tile (not just inside form)
- [ ] Bulk mode:
  - Format: NUMBER|EXP|CVV|NAME|ZIP|STATE|COUNTRY|BANK|TYPE|NON_VBV
  - BANK in bulk = optional, can be left empty (binchecked on backend)
  - NON_VBV flag at end of line
  - Auto-count: total / US / World / NON VBV
  - Price per card + separate price for NON VBV cards (two price fields)
  - File upload .txt / .csv

## NFC form
- [ ] Bank: preloaded list + request via moderation ONLY (no instant custom add)
- [ ] Balance field
- [ ] NFC type: Apple Pay / Google Pay / Samsung Pay / Other
- [ ] Country selector
- [ ] Upload .zip file (required)
- [ ] Price ($)

## OTP form
- [ ] Bank: preloaded list + custom
- [ ] Balance field
- [ ] SMS Access: TOGGLE — ON = "In Chat" (seller forwards OTP), OFF = "File" (access file sent)
- [ ] Has Fullz toggle → EXPANDS block with fields:
  - First Name / Last Name
  - Date of Birth (MM/DD/YYYY)
  - SSN
  - Address / City / State / ZIP
- [ ] Upload access file (always shown, required for file delivery)
- [ ] Price ($)

## SELFREG CC form
- [ ] Bank selector → loads preloaded card names for that bank
- [ ] Card Name: dropdown from preloaded list per bank
- [ ] Registration Date: MM + DD + YYYY (3 fields)
- [ ] VCC toggle → if ON: VCC Limit ($) + VCC BIN fields
- [ ] Phone Access (OTP): toggle ON/OFF
  - IF ON: Days field + "Can extend rental?" toggle
  - IF OFF: "Can swap number?" toggle
- [ ] Return Item toggle → days selector (1/3/7/14/30)
- [ ] Price ($)

## ENROLLMENT form
- [ ] Portal: preloaded list + request custom via moderation
- [ ] Bank: preloaded list + Add custom bank
- [ ] First Name / Last Name: toggle → fields expand
- [ ] Address: toggle → field expands
- [ ] DOB: toggle → MM/DD/YYYY fields
- [ ] SSN: toggle → field
- [ ] Phone: toggle → field
- [ ] Email: toggle → field
- [ ] Additional Info: free textarea (always shown)
- [ ] Has Docs: toggle
- [ ] Upload file (.txt / .zip)
- [ ] Price ($)

## LOGS form (SINGLE ONLY — no bulk)
- [ ] Format: LOGIN|PASS|AN|RN|BALANCE|STATE|ROUTING|NAME|ADDRESS|ZIP|CVV|ZELLE|WIRE|BT|PROMO|SAFEPASS|EMAIL|SCREENSHOT
- [ ] Single entry form with all fields:
  - LOGIN (required)
  - PASS (required)
  - AN (Account Number) — toggle
  - RN (Routing Number) — toggle
  - BALANCE — field
  - STATE — dropdown
  - ROUTING — field (if different from RN)
  - NAME — toggle → First + Last fields
  - ADDRESS — toggle → Address / City / State / ZIP
  - CVV — toggle → field
  - ZELLE — toggle (enrolled yes/no)
  - WIRE — toggle (enabled yes/no)
  - BT (Balance Transfer) — toggle
  - PROMO — toggle → field (promo code/offer)
  - SAFEPASS — toggle
  - EMAIL — toggle → field
  - SCREENSHOT — toggle → file upload
- [ ] MULTIPLE ACCOUNTS: "Add another account" button — can add N accounts with different names/balances
  - Each account row: account name + balance + account type
  - Summary shows all accounts with total balance
- [ ] Bank: preloaded + custom
- [ ] Price ($) per log

## CHECKS form
- [ ] Check Format: PS (printed scan) / PHOTO (photo of physical check)
- [ ] Check Type: Personal / Business / Payroll / Cashier
- [ ] Bank: request via moderation ONLY (no preloaded list)
- [ ] Check Amount ($)
- [ ] State
- [ ] Upload scan/photo (required)
- [ ] Price ($)

## SELFREG BA form
- [ ] Bank: preloaded + custom
- [ ] Single mode: all account fields
- [ ] Bulk mode: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|ATTRS
- [ ] Price ($)

## SETTINGS
- [ ] Language flags: 🇺🇸 EN / 🇷🇺 RU / 🇪🇸 ES / 🇨🇳 ZH

## CC SECTION TILE
- [ ] NON VBV badge/checkbox visible on the section card in the uploads menu

## CC BULK PRICES
- [ ] Two price fields in bulk: "Price per card ($)" + "Price per NON VBV card ($)"
