CREATE TABLE `apiKeys` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`label` varchar(128) NOT NULL,
	`keyPrefix` varchar(24) NOT NULL,
	`keyHash` varchar(255) NOT NULL,
	`scope` enum('single','bulk','vip','admin') NOT NULL,
	`status` enum('active','revoked') NOT NULL DEFAULT 'active',
	`rpmLimit` int NOT NULL DEFAULT 60,
	`dailyLimit` int NOT NULL DEFAULT 1000,
	`lastUsedAt` timestamp,
	`expiresAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `apiKeys_id` PRIMARY KEY(`id`),
	CONSTRAINT `apiKeyPrefixUnique` UNIQUE(`keyPrefix`)
);
--> statement-breakpoint
CREATE TABLE `auditTrail` (
	`id` int AUTO_INCREMENT NOT NULL,
	`actorUserId` int,
	`actorType` enum('user','system','worker','api_key') NOT NULL,
	`action` varchar(128) NOT NULL,
	`resourceType` varchar(64) NOT NULL,
	`resourceId` varchar(128) NOT NULL,
	`status` enum('success','failure','denied') NOT NULL,
	`ipAddress` varchar(64),
	`detailsJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `auditTrail_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `jobEvents` (
	`id` int AUTO_INCREMENT NOT NULL,
	`jobId` int NOT NULL,
	`eventType` varchar(64) NOT NULL,
	`severity` enum('debug','info','warn','error') NOT NULL DEFAULT 'info',
	`message` text NOT NULL,
	`eventJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `jobEvents_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `jobs` (
	`id` int AUTO_INCREMENT NOT NULL,
	`publicId` varchar(64) NOT NULL,
	`userId` int,
	`apiKeyId` int,
	`source` enum('dashboard','api','telegram','system','testbench') NOT NULL,
	`requestMode` enum('single','bulk','vip') NOT NULL,
	`status` enum('queued','running','succeeded','failed','canceled','waiting_retry') NOT NULL,
	`queueName` varchar(64) NOT NULL DEFAULT 'default',
	`priority` int NOT NULL DEFAULT 100,
	`targetLabel` varchar(191),
	`payloadJson` json NOT NULL,
	`resultJson` json,
	`errorCode` varchar(64),
	`errorMessage` text,
	`proxyPolicyId` int,
	`workerNodeId` int,
	`attemptCount` int NOT NULL DEFAULT 0,
	`maxAttempts` int NOT NULL DEFAULT 3,
	`costEstimateUsd` decimal(10,4) NOT NULL DEFAULT '0.0000',
	`cogsUsd` decimal(10,4) NOT NULL DEFAULT '0.0000',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	`startedAt` timestamp,
	`completedAt` timestamp,
	CONSTRAINT `jobs_id` PRIMARY KEY(`id`),
	CONSTRAINT `jobs_publicId_unique` UNIQUE(`publicId`)
);
--> statement-breakpoint
CREATE TABLE `metricSnapshots` (
	`id` int AUTO_INCREMENT NOT NULL,
	`snapshotType` enum('system','provider','queue','billing','job') NOT NULL,
	`scopeKey` varchar(128) NOT NULL,
	`successRate` decimal(7,4),
	`errorRate` decimal(7,4),
	`queueDepth` int,
	`activeWorkers` int,
	`cogsUsd` decimal(12,4),
	`revenueUsd` decimal(12,4),
	`payloadJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `metricSnapshots_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `payments` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`subscriptionId` int,
	`provider` enum('btcpay','cryptobot','manual') NOT NULL,
	`status` enum('pending','paid','confirmed','expired','failed','refunded') NOT NULL,
	`currency` varchar(16) NOT NULL,
	`amount` decimal(12,2) NOT NULL,
	`amountUsd` decimal(12,2),
	`txRef` varchar(191),
	`invoiceRef` varchar(191),
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	`paidAt` timestamp,
	CONSTRAINT `payments_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `plans` (
	`id` int AUTO_INCREMENT NOT NULL,
	`code` varchar(64) NOT NULL,
	`name` varchar(128) NOT NULL,
	`tier` enum('starter','pro','vip','enterprise') NOT NULL,
	`billingInterval` enum('one_time','monthly','quarterly','yearly') NOT NULL,
	`currency` varchar(12) NOT NULL DEFAULT 'USD',
	`priceUsd` decimal(10,2) NOT NULL,
	`includedRequests` int NOT NULL DEFAULT 0,
	`monthlyApiQuota` int NOT NULL DEFAULT 0,
	`monthlyBrowserRuns` int NOT NULL DEFAULT 0,
	`maxRpm` int NOT NULL DEFAULT 60,
	`maxConcurrentJobs` int NOT NULL DEFAULT 1,
	`vipApiAccess` enum('disabled','enabled') NOT NULL DEFAULT 'disabled',
	`featuresJson` json,
	`isActive` enum('yes','no') NOT NULL DEFAULT 'yes',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `plans_id` PRIMARY KEY(`id`),
	CONSTRAINT `plans_code_unique` UNIQUE(`code`)
);
--> statement-breakpoint
CREATE TABLE `proxyLeases` (
	`id` int AUTO_INCREMENT NOT NULL,
	`leaseId` varchar(64) NOT NULL,
	`jobId` int,
	`workerNodeId` int,
	`providerId` int NOT NULL,
	`policyId` int,
	`protocol` enum('http','socks5') NOT NULL,
	`sessionMode` enum('rotating','sticky','hard_sticky') NOT NULL,
	`sessionKey` varchar(128),
	`endpointHost` varchar(255) NOT NULL,
	`endpointPort` int NOT NULL,
	`country` varchar(8),
	`status` enum('active','released','expired','failed') NOT NULL DEFAULT 'active',
	`bytesSent` bigint NOT NULL DEFAULT 0,
	`bytesReceived` bigint NOT NULL DEFAULT 0,
	`estimatedCostUsd` decimal(10,4) NOT NULL DEFAULT '0.0000',
	`lastErrorCode` varchar(64),
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`expiresAt` timestamp,
	`releasedAt` timestamp,
	CONSTRAINT `proxyLeases_id` PRIMARY KEY(`id`),
	CONSTRAINT `proxyLeases_leaseId_unique` UNIQUE(`leaseId`)
);
--> statement-breakpoint
CREATE TABLE `proxyPolicies` (
	`id` int AUTO_INCREMENT NOT NULL,
	`code` varchar(64) NOT NULL,
	`name` varchar(128) NOT NULL,
	`protocol` enum('http','socks5') NOT NULL,
	`sessionMode` enum('rotating','sticky','hard_sticky') NOT NULL,
	`stickyTtlMinutes` int,
	`country` varchar(8),
	`state` varchar(64),
	`city` varchar(128),
	`maxTransportRetries` int NOT NULL DEFAULT 2,
	`maxProviderSwitches` int NOT NULL DEFAULT 1,
	`costCeilingUsd` decimal(10,4),
	`policyJson` json,
	`isDefault` enum('yes','no') NOT NULL DEFAULT 'no',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `proxyPolicies_id` PRIMARY KEY(`id`),
	CONSTRAINT `proxyPolicies_code_unique` UNIQUE(`code`)
);
--> statement-breakpoint
CREATE TABLE `proxyProviders` (
	`id` int AUTO_INCREMENT NOT NULL,
	`code` varchar(64) NOT NULL,
	`name` varchar(128) NOT NULL,
	`protocolSupport` varchar(128) NOT NULL,
	`sessionSupport` varchar(128) NOT NULL,
	`costPerGbUsd` decimal(10,4) NOT NULL,
	`priority` int NOT NULL DEFAULT 100,
	`status` enum('healthy','degraded','disabled') NOT NULL DEFAULT 'healthy',
	`configJson` json,
	`notes` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `proxyProviders_id` PRIMARY KEY(`id`),
	CONSTRAINT `proxyProviders_code_unique` UNIQUE(`code`)
);
--> statement-breakpoint
CREATE TABLE `subscriptions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`planId` int NOT NULL,
	`status` enum('pending','active','past_due','canceled','expired') NOT NULL,
	`provider` enum('manual','btcpay','cryptobot') NOT NULL,
	`externalRef` varchar(191),
	`startedAt` timestamp,
	`currentPeriodStart` timestamp,
	`currentPeriodEnd` timestamp,
	`canceledAt` timestamp,
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `subscriptions_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `systemSettings` (
	`id` int AUTO_INCREMENT NOT NULL,
	`category` varchar(64) NOT NULL,
	`settingKey` varchar(128) NOT NULL,
	`valueJson` json,
	`updatedByUserId` int,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `systemSettings_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `telegramEndpoints` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int,
	`botLabel` varchar(128) NOT NULL,
	`chatId` varchar(64),
	`status` enum('active','disabled') NOT NULL DEFAULT 'active',
	`commandScope` varchar(128) NOT NULL DEFAULT 'owner_alerts',
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `telegramEndpoints_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `usageRecords` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int,
	`apiKeyId` int,
	`jobId` int,
	`metricType` enum('request','bulk_item','browser_run','proxy_traffic_gb','captcha','storage') NOT NULL,
	`quantity` decimal(14,4) NOT NULL,
	`unitCostUsd` decimal(10,4) NOT NULL DEFAULT '0.0000',
	`totalCostUsd` decimal(12,4) NOT NULL DEFAULT '0.0000',
	`periodKey` varchar(32) NOT NULL,
	`metadataJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `usageRecords_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `users` (
	`id` int AUTO_INCREMENT NOT NULL,
	`openId` varchar(64) NOT NULL,
	`name` text,
	`email` varchar(320),
	`loginMethod` varchar(64),
	`role` enum('user','admin') NOT NULL DEFAULT 'user',
	`telegramChatId` varchar(64),
	`status` enum('active','suspended','invited') NOT NULL DEFAULT 'active',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	`lastSignedIn` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `users_id` PRIMARY KEY(`id`),
	CONSTRAINT `users_openId_unique` UNIQUE(`openId`)
);
--> statement-breakpoint
CREATE TABLE `workerNodes` (
	`id` int AUTO_INCREMENT NOT NULL,
	`code` varchar(64) NOT NULL,
	`name` varchar(128) NOT NULL,
	`role` enum('browser','api','scheduler','hybrid') NOT NULL DEFAULT 'browser',
	`status` enum('healthy','degraded','offline','maintenance') NOT NULL DEFAULT 'healthy',
	`concurrencyLimit` int NOT NULL DEFAULT 4,
	`activeJobs` int NOT NULL DEFAULT 0,
	`version` varchar(64),
	`hostLabel` varchar(128),
	`capabilitiesJson` json,
	`lastHeartbeatAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `workerNodes_id` PRIMARY KEY(`id`),
	CONSTRAINT `workerNodes_code_unique` UNIQUE(`code`)
);
--> statement-breakpoint
CREATE TABLE `workerRuns` (
	`id` int AUTO_INCREMENT NOT NULL,
	`jobId` int NOT NULL,
	`workerNodeId` int NOT NULL,
	`runStatus` enum('started','completed','failed','timeout','canceled') NOT NULL,
	`attemptNumber` int NOT NULL DEFAULT 1,
	`profilePolicy` varchar(128),
	`fingerprintProfile` varchar(128),
	`runtimeMs` int,
	`detailsJson` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`finishedAt` timestamp,
	CONSTRAINT `workerRuns_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE INDEX `apiKeyUserIdx` ON `apiKeys` (`userId`);--> statement-breakpoint
CREATE INDEX `auditResourceIdx` ON `auditTrail` (`resourceType`,`resourceId`,`createdAt`);--> statement-breakpoint
CREATE INDEX `auditActorIdx` ON `auditTrail` (`actorUserId`,`createdAt`);--> statement-breakpoint
CREATE INDEX `jobEventsJobIdx` ON `jobEvents` (`jobId`,`createdAt`);--> statement-breakpoint
CREATE INDEX `jobsUserIdx` ON `jobs` (`userId`);--> statement-breakpoint
CREATE INDEX `jobsStatusIdx` ON `jobs` (`status`);--> statement-breakpoint
CREATE INDEX `jobsQueueIdx` ON `jobs` (`queueName`,`status`);--> statement-breakpoint
CREATE INDEX `metricTypeScopeIdx` ON `metricSnapshots` (`snapshotType`,`scopeKey`,`createdAt`);--> statement-breakpoint
CREATE INDEX `paymentsUserIdx` ON `payments` (`userId`);--> statement-breakpoint
CREATE INDEX `paymentsStatusIdx` ON `payments` (`status`);--> statement-breakpoint
CREATE INDEX `proxyLeaseJobIdx` ON `proxyLeases` (`jobId`);--> statement-breakpoint
CREATE INDEX `proxyLeaseProviderIdx` ON `proxyLeases` (`providerId`,`status`);--> statement-breakpoint
CREATE INDEX `proxyPolicyCodeIdx` ON `proxyPolicies` (`code`);--> statement-breakpoint
CREATE INDEX `subscriptionUserIdx` ON `subscriptions` (`userId`);--> statement-breakpoint
CREATE INDEX `subscriptionPlanIdx` ON `subscriptions` (`planId`);--> statement-breakpoint
CREATE INDEX `usageUserIdx` ON `usageRecords` (`userId`,`periodKey`);--> statement-breakpoint
CREATE INDEX `usageApiKeyIdx` ON `usageRecords` (`apiKeyId`,`periodKey`);--> statement-breakpoint
CREATE INDEX `workerRunsJobIdx` ON `workerRuns` (`jobId`);--> statement-breakpoint
CREATE INDEX `workerRunsWorkerIdx` ON `workerRuns` (`workerNodeId`);