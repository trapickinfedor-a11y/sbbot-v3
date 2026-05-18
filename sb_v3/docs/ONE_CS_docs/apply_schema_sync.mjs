import mysql from "mysql2/promise";
import fs from "node:fs/promises";

const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  console.error("DATABASE_URL is not set");
  process.exit(1);
}

const migrationPath = new URL("./drizzle/0000_bouncy_drax.sql", import.meta.url);
const rawSql = await fs.readFile(migrationPath, "utf8");
const statements = rawSql
  .split("--> statement-breakpoint")
  .map((part) => part.trim())
  .filter(Boolean);

const connection = await mysql.createConnection(databaseUrl);

async function getCurrentDatabase() {
  const [rows] = await connection.query("SELECT DATABASE() AS db");
  return rows[0]?.db;
}

async function tableExists(schemaName, tableName) {
  const [rows] = await connection.execute(
    `SELECT 1 AS ok FROM information_schema.tables WHERE table_schema = ? AND table_name = ? LIMIT 1`,
    [schemaName, tableName],
  );
  return rows.length > 0;
}

async function columnExists(schemaName, tableName, columnName) {
  const [rows] = await connection.execute(
    `SELECT 1 AS ok FROM information_schema.columns WHERE table_schema = ? AND table_name = ? AND column_name = ? LIMIT 1`,
    [schemaName, tableName, columnName],
  );
  return rows.length > 0;
}

function extractCreatedTableName(statement) {
  const match = statement.match(/^CREATE TABLE `([^`]+)`/i);
  return match?.[1] ?? null;
}

const schemaName = await getCurrentDatabase();
if (!schemaName) {
  console.error("Unable to detect current database name");
  process.exit(1);
}

try {
  await connection.beginTransaction();

  const userTablePresent = await tableExists(schemaName, "users");
  if (userTablePresent) {
    const hasTelegramChatId = await columnExists(schemaName, "users", "telegramChatId");
    if (!hasTelegramChatId) {
      await connection.query(
        "ALTER TABLE `users` ADD COLUMN `telegramChatId` varchar(64) NULL AFTER `role`",
      );
      console.log("Added users.telegramChatId");
    }

    const hasStatus = await columnExists(schemaName, "users", "status");
    if (!hasStatus) {
      await connection.query(
        "ALTER TABLE `users` ADD COLUMN `status` enum('active','suspended','invited') NOT NULL DEFAULT 'active' AFTER `telegramChatId`",
      );
      console.log("Added users.status");
    }
  }

  for (const statement of statements) {
    const tableName = extractCreatedTableName(statement);
    if (!tableName) continue;

    const exists = await tableExists(schemaName, tableName);
    if (exists) continue;

    await connection.query(statement);
    console.log(`Created table ${tableName}`);
  }

  await connection.commit();
  console.log("Schema sync completed successfully.");
} catch (error) {
  await connection.rollback();
  console.error("Schema sync failed:", error);
  process.exitCode = 1;
} finally {
  await connection.end();
}
