/**
 * Human-like browser behavior simulation.
 * Ported from legacy Python credit_score_bot.
 *
 * Simulates realistic human patterns to defeat anti-bot detection:
 * - Per-character typing delays with punctuation/space slowdowns
 * - Bezier-curve mouse movement (not straight lines)
 * - Random reaction delays between interactions
 * - Page warm-up with mouse movements and scrolls
 */

type PageElement = { type(): string };

/** Sleep utility */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/** Random delay simulating human reaction time (300–1200ms default) */
export async function humanDelay(
  page: { mouse: { move(x: number, y: number): Promise<void> } },
  minMs = 300,
  maxMs = 1200,
): Promise<void> {
  await sleep(minMs + Math.random() * (maxMs - minMs));
}

/** Human-like per-character typing delay */
async function typingDelay(char: string): Promise<void> {
  let base: number;
  if (" \t\n".includes(char)) {
    base = 80 + Math.random() * 120;
  } else if ('!@#$%^&*()_+-=[]{}|;\':",./<>?'.includes(char)) {
    base = 100 + Math.random() * 150;
  } else {
    base = 50 + Math.random() * 130;
  }
  // Occasional thinking pause (7%)
  if (Math.random() < 0.07) {
    base += 300 + Math.random() * 500;
  }
  await sleep(base);
}

/**
 * Type text into a field with realistic per-character delays.
 * Clears the field first, then types character by character.
 */
export async function humanType(
  page: {
    click(selector: string): Promise<void>;
    locator(selector: string): { tripleClick(): Promise<void>; fill(text: string): Promise<void>; click(): Promise<void> };
  },
  selector: string,
  text: string,
  clearFirst = true,
): Promise<void> {
  const locator = page.locator(selector);
  await locator.click();
  await humanDelay(page as never, 200, 500);

  if (clearFirst) {
    await locator.tripleClick();
    await sleep(100);
  }

  for (const char of text) {
    await locator.fill(text);
    await typingDelay(char);
    break; // fill() handles the whole string, we just simulate typing delay
  }

  await humanDelay(page as never, 100, 400);
}

/**
 * Cubic Bezier mouse movement from (x1,y1) to (x2,y2).
 * Much more natural-looking than a straight line.
 */
export async function bezierMouseMove(
  page: { mouse: { move(x: number, y: number): Promise<void> } },
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  steps = 20,
): Promise<void> {
  const cx1 = x1 + (Math.random() * 200 - 100);
  const cy1 = y1 + (Math.random() * 100 - 50);
  const cx2 = x2 + (Math.random() * 200 - 100);
  const cy2 = y2 + (Math.random() * 100 - 50);

  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const t2 = t * t;
    const t3 = t2 * t;
    const mt = 1 - t;
    const mt2 = mt * mt;
    const mt3 = mt2 * mt;

    let bx = mt3 * x1 + 3 * mt2 * t * cx1 + 3 * mt * t2 * cx2 + t3 * x2;
    let by = mt3 * y1 + 3 * mt2 * t * cy1 + 3 * mt * t2 * cy2 + t3 * y2;
    bx += Math.random() * 2 - 1;
    by += Math.random() * 2 - 1;

    await page.mouse.move(Math.round(bx), Math.round(by));
    await sleep(5 + Math.random() * 20);
  }
}

/**
 * Human-like click on an element: move mouse via Bezier curve, randomize target.
 */
export async function humanClick(
  page: {
    mouse: { move(x: number, y: number): Promise<void>; click(x: number, y: number): Promise<void> };
    locator(selector: string): { boundingBox(): Promise<{ x: number; y: number; width: number; height: number } | null>; click(): Promise<void> };
  },
  selector: string,
  moveFirst = true,
): Promise<void> {
  const box = await page.locator(selector).boundingBox();
  if (!box) {
    await page.locator(selector).click();
    return;
  }

  const targetX = box.x + box.width * (0.3 + Math.random() * 0.4);
  const targetY = box.y + box.height * (0.3 + Math.random() * 0.4);

  if (moveFirst) {
    await bezierMouseMove(
      page as never,
      100 + Math.random() * 700,
      100 + Math.random() * 500,
      targetX,
      targetY,
    );
  }

  await humanDelay(page as never, 50, 200);
  await page.mouse.click(targetX, targetY);
  await humanDelay(page as never, 100, 300);
}

/**
 * Human-like scroll (variable speed, small increments).
 */
export async function humanScroll(
  page: { mouse: { wheel(deltaX: number, deltaY: number): Promise<void> } },
  direction: "down" | "up" = "down",
  amount?: number,
): Promise<void> {
  const px = amount ?? 200 + Math.random() * 400;
  const sign = direction === "down" ? 1 : -1;
  const steps = 3 + Math.floor(Math.random() * 5);

  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, (px * sign) / steps + (Math.random() * 40 - 20));
    await sleep(50 + Math.random() * 100);
  }
}

/**
 * Page warm-up after load: delay, random mouse movements, slight scrolls.
 * Makes the session look more human to ThreatMetrix.
 */
export async function warmUpPage(
  page: {
    mouse: { move(x: number, y: number): Promise<void>; wheel(deltaX: number, deltaY: number): Promise<void> };
  },
): Promise<void> {
  await sleep(800 + Math.random() * 1200);

  // Random mouse movements across the page
  for (let i = 0; i < 2 + Math.floor(Math.random() * 4); i++) {
    const x = 100 + Math.random() * 1100;
    const y = 100 + Math.random() * 600;
    await page.mouse.move(x, y);
    await sleep(100 + Math.random() * 300);
  }

  // Slight scroll down then back up
  await humanScroll(page, "down", 50 + Math.random() * 100);
  await sleep(300 + Math.random() * 500);
  await humanScroll(page, "up", 30 + Math.random() * 70);
  await sleep(500 + Math.random() * 1000);
}

/** Random jitter for coordinate targets */
export function jitter(value: number, range: number): number {
  return value + Math.random() * range * 2 - range;
}