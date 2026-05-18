# 📬 Seller Bot - Complete Notification Templates

## Notification Categories

### 1. 📦 Order Notifications

#### 1.1 New Order Received
```
🎉 <b>New Order #{{order_id}}!</b>

🏦 Product: <b>{{product_name}}</b>
💰 Your earnings: <b>${{seller_price}}</b>
🔢 Quantity: {{quantity}}
⏰ Deadline: {{deadline_hours}} hours

Please complete this order within the deadline to receive payment.

[📤 Complete Order] [💬 Chat with Buyer]
```

#### 1.2 Order Approved by Admin
```
✅ <b>Order #{{order_id}} Approved</b>

Your order has been approved by the admin.
You can now complete it and deliver to the buyer.

🏦 Product: {{product_name}}
💰 Earnings: <b>${{seller_price}}</b>
⏰ Complete within: {{hours_remaining}}h

[📤 Complete Now] [📦 View Details]
```

#### 1.3 Order Completed Successfully
```
✅ <b>Order #{{order_id}} Completed!</b>

Great job! Your order has been delivered.

💰 <b>+${{seller_price}}</b> added to pending balance
🕐 Escrow release in: {{escrow_hours}}h
📊 Completion rate: {{completion_rate}}%

Funds will be available for withdrawal after the escrow period.

[📦 View Order] [💰 View Balance]
```

#### 1.4 Order Disputed by Buyer
```
⚠️ <b>Order #{{order_id}} Disputed</b>

The buyer has reported an issue with this order.
Please respond within 48 hours.

🏦 Product: {{product_name}}
💰 Amount: ${{seller_price}}
📝 Reason: {{dispute_reason}}
⏰ Response deadline: {{deadline}}

[📎 Submit Evidence] [💬 Chat with Buyer] [📋 View Details]
```

#### 1.5 Dispute Resolved - In Your Favor
```
✅ <b>Dispute Resolved - You Win</b>

Order #{{order_id}}

The admin has reviewed the dispute and decided in your favor.

💰 <b>+${{seller_price}}</b> will be released to your balance
📊 Your rating: {{rating}}/5.0

[📦 View Order] [💰 View Balance]
```

#### 1.6 Dispute Resolved - Against You
```
❌ <b>Dispute Resolved - Buyer Refunded</b>

Order #{{order_id}}

The admin has reviewed the dispute and decided in favor of the buyer.

📝 Admin note: {{admin_note}}
💰 Amount refunded: ${{amount}}

Please ensure product quality to avoid future disputes.

[📋 View Details] [📞 Contact Support]
```

#### 1.7 Order Auto-Completed
```
✅ <b>Order #{{order_id}} Auto-Completed</b>

This order has been automatically completed after the review period.

💰 <b>+${{seller_price}}</b> released to withdrawable balance
🎉 No disputes were filed

[💸 Withdraw Funds] [📊 View Balance]
```

#### 1.8 Order Cancelled by Admin
```
⚪ <b>Order #{{order_id}} Cancelled</b>

This order has been cancelled by the admin.

📝 Reason: {{cancellation_reason}}
🏦 Product: {{product_name}}

Your product has been returned to inventory.

[📋 View Details]
```

---

### 2. 💳 Product Notifications

#### 2.1 Product Approved
```
✅ <b>Product Approved!</b>

Your product is now live and visible to buyers.

🏦 Product: <b>{{product_name}}</b>
📋 Batch: #{{batch_id}}
💰 Price: ${{price}}
📊 Stock: {{stock_count}} units

[📊 View Listing] [📈 View Stats]
```

#### 2.2 Product Rejected
```
❌ <b>Product Rejected</b>

Your product submission was not approved.

🏦 Product: {{product_name}}
📋 Batch: #{{batch_id}}

📝 <b>Reason:</b>
{{rejection_reason}}

Please fix the issues and resubmit.

[✏️ Edit Product] [🗑 Delete] [📞 Contact Support]
```

#### 2.3 Product Needs Changes
```
⚠️ <b>Changes Requested</b>

The admin has requested changes to your product.

🏦 Product: {{product_name}}
📋 Batch: #{{batch_id}}

📝 <b>Required changes:</b>
{{change_requests}}

Please update and resubmit for approval.

[✏️ Edit Now] [📋 View Details]
```

#### 2.4 Product Out of Stock
```
⚠️ <b>Product Out of Stock</b>

Your product is no longer available for buyers.

🏦 Product: {{product_name}}
📊 Stock: 0 units
💰 Total sold: {{total_sold}}

[➕ Restock Now] [📊 View Performance]
```

#### 2.5 Product Low Stock Alert
```
⚠️ <b>Low Stock Alert</b>

Your product is running low on inventory.

🏦 Product: {{product_name}}
📊 Remaining: {{stock_count}} units
💰 Price: ${{price}}

Consider restocking to continue receiving orders.

[➕ Add Stock] [📊 View Details]
```

#### 2.6 Product Price Drop Triggered Wishlist
```
📢 <b>Price Drop Alert Sent</b>

Your price reduction has triggered {{wishlist_count}} wishlist notifications.

🏦 Product: {{product_name}}
💰 Old price: ${{old_price}} → New price: ${{new_price}}

Expect increased interest from buyers!

[📊 View Stats]
```

---

### 3. 💰 Financial Notifications

#### 3.1 Withdrawal Request Created
```
💸 <b>Withdrawal Request Submitted</b>

Your withdrawal request has been created.

💰 Amount: <b>${{amount}}</b>
📅 Status: Pending admin approval
🔢 Request ID: #{{request_id}}

Processing time: 1-3 business days after approval.

[📋 View Request] [💰 View Balance]
```

#### 3.2 Withdrawal Approved
```
✅ <b>Withdrawal Approved!</b>

Your withdrawal request has been approved.

💰 Amount: <b>${{amount}}</b>
💳 Payment method: {{payment_method}}
📅 Processing time: 1-3 business days

Funds are being transferred to your account.

[📋 View Details] [📊 View History]
```

#### 3.3 Withdrawal Rejected
```
❌ <b>Withdrawal Rejected</b>

Your withdrawal request was not approved.

💰 Amount: ${{amount}}
📝 Reason: {{rejection_reason}}

Your balance remains unchanged.

[💸 Try Again] [📞 Contact Support]
```

#### 3.4 Withdrawal Completed
```
✅ <b>Withdrawal Completed!</b>

Your funds have been successfully transferred.

💰 Amount: <b>${{amount}}</b>
💳 Payment method: {{payment_method}}
📅 Completed: {{completion_date}}

[📊 View Balance] [📋 View History]
```

#### 3.5 Escrow Released
```
💰 <b>Escrow Released!</b>

Funds from Order #{{order_id}} are now available.

💵 <b>+${{amount}}</b> → Withdrawable balance
🏦 Product: {{product_name}}
📊 New balance: ${{new_balance}}

[💸 Withdraw Now] [📊 View Balance]
```

#### 3.6 Auto-Payout Processed
```
💸 <b>Auto-Payout Processed</b>

Your weekly auto-payout has been executed.

💰 Amount: <b>${{amount}}</b>
💳 Payment method: {{payment_method}}
📅 Period: {{start_date}} - {{end_date}}

[📋 View Details] [⚙️ Manage Auto-Payout]
```

#### 3.7 Security Deposit Paid
```
✅ <b>Security Deposit Confirmed!</b>

Your security deposit payment has been confirmed.

💰 Amount: ${{amount}}
📦 Package: {{package_name}}
🔓 Access granted to: {{categories}}

You can now start uploading products!

[🚀 Start Uploading] [📋 View Access]
```

---

### 4. 👤 Account Notifications

#### 4.1 Account Approved
```
🎉 <b>Seller Account Approved!</b>

Welcome to the seller panel!

Your account has been approved and you can now:
✅ Upload products
✅ Receive orders
✅ Earn money

📋 Next steps:
1. Pay security deposit (if required)
2. Upload your first product
3. Start earning!

[🚀 Get Started] [📖 Read Guide]
```

#### 4.2 Account Suspended
```
⚠️ <b>Account Suspended</b>

Your seller account has been temporarily suspended.

📝 Reason: {{suspension_reason}}
⏰ Duration: {{duration}}

Please contact support for more information.

[📞 Contact Support] [📋 View Details]
```

#### 4.3 Account Reactivated
```
✅ <b>Account Reactivated</b>

Your seller account has been reactivated.

You can now resume:
✅ Uploading products
✅ Receiving orders
✅ Managing inventory

[🚀 Continue Selling] [📦 View Orders]
```

#### 4.4 Vacation Mode Enabled
```
🏖 <b>Vacation Mode Enabled</b>

Your products are now hidden from buyers.

📊 Status:
• Products: Hidden
• Orders: Paused
• Messages: Still active

Remember to disable vacation mode when you return!

[🔔 Disable Now] [⚙️ Settings]
```

#### 4.5 Vacation Mode Disabled
```
🔔 <b>Vacation Mode Disabled</b>

Your products are now visible to buyers again.

📊 Status:
• Products: Live
• Orders: Active
• Ready to sell!

[📦 View Products] [📊 Dashboard]
```

---

### 5. 👥 Team Notifications

#### 5.1 Helper Invite Sent
```
👥 <b>Helper Invite Sent</b>

You've invited @{{username}} to join your team.

📋 Access level: {{access_level}}
⏰ Waiting for acceptance

They will receive a notification to accept the invite.

[📋 View Team] [⚙️ Manage Access]
```

#### 5.2 Helper Accepted Invite
```
✅ <b>Helper Joined Your Team!</b>

@{{username}} has accepted your invite.

👤 Helper: @{{username}}
📋 Access level: {{access_level}}
📅 Joined: {{join_date}}

They can now help manage your seller account.

[👥 View Team] [⚙️ Manage Permissions]
```

#### 5.3 Helper Declined Invite
```
❌ <b>Helper Declined Invite</b>

@{{username}} has declined your team invite.

You can invite someone else or try again later.

[👥 Invite Another] [📋 View Team]
```

#### 5.4 Helper Removed
```
🚪 <b>Helper Removed</b>

@{{username}} has been removed from your team.

They no longer have access to your seller account.

[👥 View Team] [➕ Invite New Helper]
```

#### 5.5 You Were Added as Helper
```
👥 <b>You're Now a Helper!</b>

@{{owner_username}} has added you as a helper.

📋 Access level: {{access_level}}
🏦 Seller: {{seller_name}}

You can now help manage their products and orders.

[🚀 Start Helping] [📋 View Access]
```

---

### 6. 💬 Chat Notifications

#### 6.1 New Message from Buyer
```
💬 <b>New Message</b>

Order #{{order_id}}

👤 Buyer: "{{message_preview}}"

[💬 Reply Now] [📦 View Order]
```

#### 6.2 New Message from Admin
```
👨‍💼 <b>Admin Message</b>

{{message_preview}}

[💬 Reply] [📋 View Details]
```

#### 6.3 Chat Closed
```
🔒 <b>Chat Closed</b>

Order #{{order_id}}

The chat for this order has been closed.

[📦 View Order]
```

---

### 7. 📊 Performance Notifications

#### 7.1 Daily Sales Summary
```
📊 <b>Daily Sales Summary</b>
{{date}}

💰 Today's earnings: <b>${{daily_earnings}}</b>
📦 Orders completed: {{orders_completed}}
⭐ Average rating: {{avg_rating}}/5.0

📈 Compared to yesterday:
{{comparison}}

[📊 View Full Report] [💸 Withdraw]
```

#### 7.2 Weekly Performance Report
```
📈 <b>Weekly Performance Report</b>
{{week_range}}

💰 Total earned: <b>${{weekly_earnings}}</b>
📦 Orders: {{total_orders}}
✅ Completion rate: {{completion_rate}}%
⭐ Rating: {{avg_rating}}/5.0
🏆 Top product: {{top_product}}

Keep up the great work!

[📊 View Details] [💸 Withdraw]
```

#### 7.3 Monthly Earnings Report
```
📊 <b>Monthly Earnings Report</b>
{{month}} {{year}}

💰 Total earned: <b>${{monthly_earnings}}</b>
📦 Orders completed: {{total_orders}}
📈 Growth: {{growth_percentage}}%
🏆 Best day: {{best_day}} (${{best_day_amount}})

🎯 Goals for next month:
• Target: ${{next_month_target}}
• Orders: {{next_month_orders_target}}

[📊 View Full Report] [🎯 Set Goals]
```

#### 7.4 Milestone Achieved
```
🎉 <b>Milestone Achieved!</b>

Congratulations! You've reached a new milestone.

🏆 {{milestone_name}}
📊 {{milestone_description}}

Keep up the excellent work!

[🎉 View Achievements] [📊 Dashboard]
```

---

### 8. ⚠️ Warning Notifications

#### 8.1 Low Completion Rate Warning
```
⚠️ <b>Completion Rate Warning</b>

Your order completion rate has dropped below 80%.

📊 Current rate: {{completion_rate}}%
📦 Incomplete orders: {{incomplete_count}}

Please complete pending orders to maintain good standing.

[📦 View Orders] [📖 Tips]
```

#### 8.2 High Dispute Rate Warning
```
⚠️ <b>High Dispute Rate Alert</b>

Your dispute rate is higher than average.

📊 Dispute rate: {{dispute_rate}}%
⚠️ Recent disputes: {{dispute_count}}

Tips to reduce disputes:
• Verify product quality
• Provide accurate descriptions
• Respond quickly to buyers

[📋 View Disputes] [📖 Best Practices]
```

#### 8.3 Inactive Account Warning
```
⏰ <b>Inactive Account Notice</b>

You haven't uploaded products in {{days_inactive}} days.

📊 Status:
• Last upload: {{last_upload_date}}
• Active products: {{active_products}}

Stay active to maintain your seller status!

[⬆️ Upload Now] [📊 Dashboard]
```

---

### 9. 🔔 System Notifications

#### 9.1 System Maintenance Scheduled
```
🔧 <b>Maintenance Scheduled</b>

The system will be under maintenance.

📅 Date: {{maintenance_date}}
⏰ Time: {{maintenance_time}}
⏱️ Duration: {{duration}}

Services may be temporarily unavailable.

[📋 Learn More]
```

#### 9.2 New Feature Announcement
```
🎉 <b>New Feature Available!</b>

{{feature_name}}

{{feature_description}}

Try it now and improve your selling experience!

[🚀 Try Now] [📖 Learn More]
```

#### 9.3 Policy Update
```
📋 <b>Policy Update</b>

Our seller policies have been updated.

📝 Changes:
{{policy_changes}}

Please review the updated policies.

[📖 Read Full Policy] [✅ Acknowledge]
```

---

## Notification Formatting Guidelines

### Text Formatting
- **Bold**: `<b>text</b>` - For emphasis, amounts, titles
- *Italic*: `<i>text</i>` - For secondary information
- `Code`: `<code>text</code>` - For IDs, technical info
- Links: `<a href="url">text</a>` - For external links

### Emojis Usage
- 🎉 Success, celebration
- ✅ Approved, completed
- ❌ Rejected, error
- ⚠️ Warning, attention needed
- 💰 Money, earnings
- 📦 Orders, products
- 💬 Messages, chat
- 📊 Statistics, reports
- 🏦 Banks, financial
- 👤 User, profile
- ⏰ Time, deadline
- 🔔 Notification, alert

### Button Guidelines
- Use clear, action-oriented text
- Maximum 2-3 buttons per notification
- Primary action first
- Use emojis in buttons for visual clarity

### Timing
- **Instant**: Order updates, messages, disputes
- **Delayed**: Reminders (6h, 24h before deadline)
- **Scheduled**: Daily summaries (9 AM), weekly reports (Monday 9 AM)

---

**Last Updated:** March 24, 2026
**Version:** 2.0
