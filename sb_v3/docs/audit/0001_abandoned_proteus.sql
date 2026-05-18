CREATE TABLE `apiKeys` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`name` varchar(120) NOT NULL,
	`keyHash` varchar(255) NOT NULL,
	`keyPreview` varchar(24) NOT NULL,
	`status` enum('active','revoked') NOT NULL DEFAULT 'active',
	`lastUsedAt` timestamp,
	`expiresAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `apiKeys_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `apiUsageMetrics` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`apiKeyId` int,
	`route` varchar(180) NOT NULL,
	`method` enum('GET','POST','PUT','DELETE') NOT NULL DEFAULT 'GET',
	`statusCode` int NOT NULL,
	`requestUnits` int NOT NULL DEFAULT 1,
	`latencyMs` int NOT NULL DEFAULT 0,
	`ipAddress` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `apiUsageMetrics_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `auditLogs` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int,
	`actionType` varchar(120) NOT NULL,
	`entityType` varchar(120) NOT NULL,
	`entityId` varchar(120),
	`ipAddress` varchar(64),
	`userAgent` text,
	`locale` enum('en','ru','es','cn') NOT NULL DEFAULT 'en',
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `auditLogs_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `complianceEvents` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int,
	`searchRequestId` int,
	`eventType` enum('consent_captured','terms_accepted','policy_acknowledged','access_granted','access_denied','review_flagged','export_requested') NOT NULL,
	`severity` enum('info','warning','critical') NOT NULL DEFAULT 'info',
	`notes` text,
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `complianceEvents_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `notifications` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`kind` enum('low_balance','subscription_renewal','search_complete','api_quota_warning','system') NOT NULL,
	`channel` enum('in_app','email','webhook') NOT NULL DEFAULT 'in_app',
	`status` enum('unread','read','sent','failed') NOT NULL DEFAULT 'unread',
	`title` varchar(180) NOT NULL,
	`body` text NOT NULL,
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`readAt` timestamp,
	CONSTRAINT `notifications_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `searchCandidates` (
	`id` int AUTO_INCREMENT NOT NULL,
	`searchRequestId` int NOT NULL,
	`candidateOrder` int NOT NULL DEFAULT 0,
	`fullName` varchar(180) NOT NULL,
	`ageBand` varchar(64),
	`primaryPhone` varchar(32),
	`primaryAddress` varchar(255),
	`summary` text,
	`confidenceScore` int NOT NULL DEFAULT 0,
	`dataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `searchCandidates_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `searchRequests` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`type` enum('phone','address','ssn','driver_license','credit_report','background_check') NOT NULL,
	`status` enum('queued','processing','completed','failed') NOT NULL DEFAULT 'queued',
	`inputQuery` text NOT NULL,
	`locale` enum('en','ru','es','cn') NOT NULL DEFAULT 'en',
	`selectedCandidateId` int,
	`candidateCount` int NOT NULL DEFAULT 0,
	`totalChargeCents` int NOT NULL DEFAULT 0,
	`sourceLabel` varchar(120),
	`ipAddress` varchar(64),
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`completedAt` timestamp,
	CONSTRAINT `searchRequests_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `subscriptionPlans` (
	`id` int AUTO_INCREMENT NOT NULL,
	`code` varchar(32) NOT NULL,
	`name` varchar(120) NOT NULL,
	`billingPeriod` enum('monthly','yearly') NOT NULL DEFAULT 'monthly',
	`audience` enum('regular','vip') NOT NULL,
	`priceCents` int NOT NULL,
	`includedCreditsCents` int NOT NULL DEFAULT 0,
	`includedApiQuota` int NOT NULL DEFAULT 0,
	`rateLimitPerMinute` int NOT NULL DEFAULT 0,
	`featuresJson` json,
	`isActive` int NOT NULL DEFAULT 1,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `subscriptionPlans_id` PRIMARY KEY(`id`),
	CONSTRAINT `subscriptionPlans_code_unique` UNIQUE(`code`)
);
--> statement-breakpoint
CREATE TABLE `subscriptions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`planId` int NOT NULL,
	`status` enum('trial','active','past_due','canceled','expired') NOT NULL DEFAULT 'active',
	`startedAt` timestamp NOT NULL DEFAULT (now()),
	`renewsAt` timestamp,
	`canceledAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `subscriptions_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `systemSettings` (
	`id` int AUTO_INCREMENT NOT NULL,
	`settingKey` varchar(120) NOT NULL,
	`scope` enum('global','billing','search','api','notifications','localization') NOT NULL DEFAULT 'global',
	`settingValue` text NOT NULL,
	`updatedByUserId` int,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `systemSettings_id` PRIMARY KEY(`id`),
	CONSTRAINT `systemSettings_settingKey_unique` UNIQUE(`settingKey`)
);
--> statement-breakpoint
CREATE TABLE `transactions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`kind` enum('top_up','subscription','search_charge','api_charge','refund','adjustment') NOT NULL,
	`status` enum('pending','completed','failed','canceled') NOT NULL DEFAULT 'pending',
	`paymentMethod` enum('card','crypto','bank_transfer','manual','balance') NOT NULL DEFAULT 'card',
	`provider` varchar(64),
	`amountCents` int NOT NULL,
	`balanceBeforeCents` int NOT NULL DEFAULT 0,
	`balanceAfterCents` int NOT NULL DEFAULT 0,
	`referenceId` varchar(120),
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`completedAt` timestamp,
	CONSTRAINT `transactions_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `users` ADD `subscriptionTier` enum('regular','vip') DEFAULT 'regular' NOT NULL;--> statement-breakpoint
ALTER TABLE `users` ADD `preferredLanguage` enum('en','ru','es','cn') DEFAULT 'en' NOT NULL;--> statement-breakpoint
ALTER TABLE `users` ADD `balanceCents` int DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `users` ADD `monthlyApiQuota` int DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `users` ADD `apiCallsUsed` int DEFAULT 0 NOT NULL;