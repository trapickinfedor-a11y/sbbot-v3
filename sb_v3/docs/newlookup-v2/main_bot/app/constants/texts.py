class BotTexts:
    
    START_NEW_USER = """🎉 **ONE PROJECT is BACK — Plug In & Enter** 🎉

⚡ **Access in 60 seconds:** 1️⃣ Open [@BotFather](https://t.me/BotFather) → send `/newbot`
2️⃣ Pick a Name + Username *(must end with **bot**)*
3️⃣ Copy your token → e.g. `12345:6789ABCDEF`
4️⃣ Paste the token **here** → get `Status: Started ✅`

💡 **Pro tips:**
🔁 Lost the token? → Regenerate in @BotFather and resend
🧰 Need control later? → Use **Stop Bot / Delete Bot** buttons
🔐 Keep your token private — treat it like a **password**"""

    @staticmethod
    def bot_confirmed(bot_username: str) -> str:
        return f"""⚡️ **ONE — Access Confirmed**
**Your Bot:** [@{bot_username}](https://t.me/{bot_username})
**Status:** ✅ *Started*

**What's next?**

- 🔗 Open your bot → [@{bot_username}](https://t.me/{bot_username})
- 🗑 Delete Bot → confirm via bot button
- 🌐 Language → `RU / EN / 中文`

**Tips:**

- 🔐 Keep your token private *(like a password)*
- 🔁 Lost it? Regenerate in @BotFather → resend here
- 📌 Need links? Check **ACTUAL LINKS**"""

    BOT_DELETED = """✅ **Bot Deleted Successfully**

Your mirror bot has been stopped and removed from the system.

To create a new bot, send me a new token from @BotFather."""

    VALIDATING_TOKEN = "⏳ Validating token and starting bot..."
    DELETING_BOT = "🗑 Deleting bot..."
    ERROR_DELETING = "❌ Error deleting bot. Please try again or contact support."
    ERROR_INVALID_TOKEN = "❌ Invalid token. Please check the token and try again."
    ERROR_ALREADY_HAS_BOT = "You already have an active bot. Please delete it first."

