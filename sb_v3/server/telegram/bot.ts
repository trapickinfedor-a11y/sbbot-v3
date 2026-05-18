/**
 * Telegram bot — FSM + i18n (framework-agnostic interface)
 * Can be wired to grammY, node-telegram-bot-api, or any other Telegram framework
 */
import { buildOneCsResult } from "../../shared/oneCsScoring";
import { t, Locale, SUPPORTED_LOCALES, LOCALE_FLAGS } from "./i18n";
import { sessionStore, UserSession } from "./fsm";

export interface BotContext {
  from?: { id: number };
  message?: { text: string };
  reply: (text: string, opts?: object) => Promise<void>;
}

function getSession(ctx: BotContext): UserSession {
  const userId = ctx.from?.id ?? 0;
  let session = sessionStore.get(userId);
  if (!session) {
    session = { state: "idle", locale: "en", userId, isAdmin: false, createdAt: new Date() };
    sessionStore.set(userId, session);
  }
  return session;
}

async function processScoreFlow(ctx: BotContext, session: UserSession, text: string): Promise<void> {
  const locale = session.locale;
  switch (session.state) {
    case "idle":
      session.state = "awaiting_name";
      session.name = text;
      sessionStore.update(ctx.from!.id, session);
      await ctx.reply(t(locale, "score_awaiting_name"));
      break;
    case "awaiting_name":
      session.name = text;
      session.state = "awaiting_state";
      sessionStore.update(ctx.from!.id, session);
      await ctx.reply(t(locale, "score_awaiting_state"));
      break;
    case "awaiting_state":
      session.state_ = text;
      session.state = "processing";
      sessionStore.update(ctx.from!.id, session);
      await ctx.reply(t(locale, "score_processing"));

      const score = text.toLowerCase() === "skip" ? null : parseInt(text, 10);
      if (score !== null && (isNaN(score) || score < 300 || score > 850)) {
        session.state = "idle";
        sessionStore.update(ctx.from!.id, session);
        await ctx.reply("❌ Score 300-850 or 'skip'");
        return;
      }

      const result = buildOneCsResult({
        creditScore: score,
        completenessScore: 0.8,
        adverseReasons: [],
        priceUsd: 0, durationMs: 0,
        source: "telegram",
      });

      session.lastResult = {
        score: result.creditScore,
        productScore: result.productScore,
        dataQuality: result.dataQualityScore,
        status: result.status,
      };
      session.state = "idle";
      sessionStore.update(ctx.from!.id, session);

      await ctx.reply(t(locale, "score_result", {
        score: score ?? "N/A",
        productScore: result.productScore,
        dataQuality: result.dataQualityScore,
        status: result.status,
      }));
      break;
    default:
      await ctx.reply(t(locale, "unknown"));
  }
}

export function createBot(token: string) {
  const handlers: Array<(ctx: BotContext) => Promise<void>> = [];

  async function handleMessage(ctx: BotContext): Promise<void> {
    const session = getSession(ctx);
    const text = ctx.message?.text ?? "";

    if (text === "/start") {
      await ctx.reply(t(session.locale, "start"));
    } else if (text === "/help") {
      await ctx.reply(t(session.locale, "help"));
    } else if (text === "/score") {
      session.state = "awaiting_name";
      sessionStore.update(ctx.from!.id, session);
      await ctx.reply(t(session.locale, "score_prompt"));
    } else if (text === "/status") {
      if (session.lastResult) {
        await ctx.reply(t(session.locale, "score_result", {
          score: session.lastResult.score ?? "N/A",
          productScore: session.lastResult.productScore,
          dataQuality: session.lastResult.dataQuality,
          status: session.lastResult.status,
        }));
      } else {
        await ctx.reply("ℹ️ No previous result. Use /score to start.");
      }
    } else if (text === "/language") {
      const kb = SUPPORTED_LOCALES.map(l => `${LOCALE_FLAGS[l]} ${l.toUpperCase()}`).join("\n");
      await ctx.reply(t(session.locale, "language_select") + "\n\n" + kb);
    } else if (text === "/cancel") {
      session.state = "idle";
      sessionStore.update(ctx.from!.id, session);
      await ctx.reply(t(session.locale, "cancel"));
    } else if (text.startsWith("/lang_")) {
      const locale = text.replace("/lang_", "").toLowerCase() as Locale;
      if (SUPPORTED_LOCALES.includes(locale)) {
        session.locale = locale;
        session.state = "idle";
        sessionStore.update(ctx.from!.id, session);
        await ctx.reply(t(locale, "language_changed"));
      }
    } else if (session.state !== "idle") {
      await processScoreFlow(ctx, session, text);
    } else {
      await ctx.reply(t(session.locale, "unknown"));
    }
  }

  return { handleMessage, token };
}