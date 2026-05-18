import { beforeEach, vi } from "vitest";

beforeEach(() => {
  vi.stubEnv("BOT_TOKEN", "123456789:test_mock_bot_token_for_testing");
  vi.stubEnv("WORKER_COUNT", "4");
  vi.stubEnv("ADMIN_USER_IDS", "123456789");
  vi.stubEnv("WORKER_ROTATE_ON_SUCCESS", "5");
  vi.stubEnv("PRIVATE_API_KEY", "test_migrated_key_value_12345");
  vi.stubEnv("PRIVATE_API_PORT", "8000");
  vi.stubEnv("ADMIN_PASSWORD", "test_admin_secure_pass_123");
  vi.stubEnv("CAPTCHA_SERVICE", "2captcha");
  vi.stubEnv("NODE_ENV", "test");
});