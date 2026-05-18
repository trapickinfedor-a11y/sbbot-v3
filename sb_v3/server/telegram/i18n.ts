/**
 * i18n — 4 languages: EN, RU, ES, ZH
 */
export type Locale = "en" | "ru" | "es" | "zh";

const MESSAGES: Record<Locale, Record<string, string>> = {
  en: {
    start: "Hello! I'm ONE CS bot for credit scoring. Press /help.",
    help: "📊 Commands:\n/score — Start check\n/status — Last result\n/language — Change language\n/cancel — Cancel",
    score_prompt: "Enter your name:",
    score_awaiting_name: "Name received. Enter your state (CA, NY, TX...):",
    score_awaiting_state: "Got it. Enter credit range (300-850) or 'skip':",
    score_processing: "⏳ Running ONE CS algorithm...",
    score_result: "📊 Result:\nScore: {score}\nProduct: {productScore}/20\nQuality: {dataQuality}/10\nStatus: {status}",
    score_skip: "⏳ Checking without score...",
    language_select: "Choose language:",
    language_changed: "✅ Language: English",
    cancel: "❌ Cancelled.",
    unknown: "Unknown. Type /help.",
    error: "⚠️ Error. Try again.",
  },
  ru: {
    start: "Привет! Я ONE CS бот. Нажми /help.",
    help: "📊 Команды:\n/score — Проверка\n/status — Результат\n/language — Язык\n/cancel — Отмена",
    score_prompt: "Введите имя:",
    score_awaiting_name: "Имя принято. Введите штат (CA, NY, TX...):",
    score_awaiting_state: "Принято. Введите диапазон (300-850) или 'пропустить':",
    score_processing: "⏳ Запускаю ONE CS...",
    score_result: "📊 Результат:\nСчёт: {score}\nПродукт: {productScore}/20\nКачество: {dataQuality}/10\nСтатус: {status}",
    score_skip: "⏳ Проверяю без скоринга...",
    language_select: "Выберите язык:",
    language_changed: "✅ Язык: Русский",
    cancel: "❌ Отменено.",
    unknown: "Неизвестно. Напишите /help.",
    error: "⚠️ Ошибка.",
  },
  es: {
    start: "¡Hola! Soy ONE CS bot. Presiona /help.",
    help: "📊 Comandos:\n/score — Verificar\n/status — Resultado\n/language — Idioma\n/cancel — Cancelar",
    score_prompt: "Ingresa tu nombre:",
    score_awaiting_name: "Nombre recibido. Ingresa tu estado (CA, NY...):",
    score_awaiting_state: "Ok. Ingresa rango (300-850) o 'saltar':",
    score_processing: "⏳ Ejecutando ONE CS...",
    score_result: "📊 Resultado:\nPuntaje: {score}\nProducto: {productScore}/20\nCalidad: {dataQuality}/10\nEstado: {status}",
    score_skip: "⏳ Verificando sin puntaje...",
    language_select: "Elige idioma:",
    language_changed: "✅ Idioma: Español",
    cancel: "❌ Cancelado.",
    unknown: "Desconocido. Escribe /help.",
    error: "⚠️ Error.",
  },
  zh: {
    start: "你好！我是 ONE CS 机器人。发送 /help。",
    help: "📊 命令：\n/score — 查询\n/status — 结果\n/language — 语言\n/cancel — 取消",
    score_prompt: "请输入您的姓名：",
    score_awaiting_name: "已收到。请输入州（CA, NY, TX...）：",
    score_awaiting_state: "好的。请输入评分范围（300-850）或“跳过”：",
    score_processing: "⏳ 正在运行 ONE CS 算法...",
    score_result: "📊 结果：\n评分：{score}\n产品：{productScore}/20\n质量：{dataQuality}/10\n状态：{status}",
    score_skip: "⏳ 无评分检查中...",
    language_select: "选择语言：",
    language_changed: "✅ 语言：中文",
    cancel: "❌ 已取消。",
    unknown: "未知命令。请发送 /help。",
    error: "⚠️ 发生错误。",
  },
};

export function t(locale: Locale, key: string, params: Record<string, string | number> = {}): string {
  let msg = MESSAGES[locale]?.[key] ?? MESSAGES["en"]?.[key] ?? key;
  for (const [k, v] of Object.entries(params)) {
    msg = msg.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
  }
  return msg;
}

export const SUPPORTED_LOCALES: Locale[] = ["en", "ru", "es", "zh"];
export const LOCALE_FLAGS: Record<Locale, string> = { en: "🇺🇸", ru: "🇷🇺", es: "🇪🇸", zh: "🇨🇳" };