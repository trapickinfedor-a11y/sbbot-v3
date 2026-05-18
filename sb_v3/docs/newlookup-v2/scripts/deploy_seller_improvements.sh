#!/bin/bash

# Deployment script for seller bot improvements
# Run this after pulling the latest code

set -e  # Exit on error

echo "=================================================="
echo "🚀 Deploying Seller Bot Improvements"
echo "=================================================="
echo ""

# Step 1: Database Migration
echo "📊 Step 1: Running database migration..."
echo "--------------------------------------------------"
cd /Users/user/Desktop/прокты/newlookup

# Check if migration file exists
if [ ! -f "shared/database/migrations/add_bank_requests.py" ]; then
    echo "❌ Migration file not found!"
    exit 1
fi

# Run migration
echo "Running: alembic upgrade head"
python3 -m alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migration completed successfully"
else
    echo "❌ Database migration failed"
    exit 1
fi

echo ""

# Step 2: Seed Brute Banks
echo "🏦 Step 2: Seeding Brute Bank groups..."
echo "--------------------------------------------------"

if [ ! -f "scripts/seed_brute_banks.py" ]; then
    echo "❌ Seed script not found!"
    exit 1
fi

echo "Running: python3 scripts/seed_brute_banks.py"
python3 scripts/seed_brute_banks.py

if [ $? -eq 0 ]; then
    echo "✅ Brute banks seeded successfully"
else
    echo "❌ Brute banks seeding failed"
    exit 1
fi

echo ""

# Step 3: Restart bots (if needed)
echo "🔄 Step 3: Restart recommendation"
echo "--------------------------------------------------"
echo "⚠️  Please restart the seller bot to apply changes:"
echo ""
echo "   ./start_bots.sh"
echo ""
echo "Or restart individual bot:"
echo "   pkill -f seller_bot"
echo "   python3 -m seller_bot.main &"
echo ""

echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "📋 Summary of changes:"
echo "  ✅ Removed Selfreg BA section"
echo "  ✅ Added order # to chat messages"
echo "  ✅ Added custom bank request to Banks section"
echo "  ✅ Added custom bank request to Brute Bank section"
echo "  ✅ Preloaded 70+ Brute Bank groups"
echo ""
echo "📄 Documentation:"
echo "  - docs/SELLER_SECTIONS_REVIEW.md"
echo "  - docs/IMPLEMENTATION_COMPLETE.md"
echo "  - QUICK_SUMMARY.md"
echo ""
echo "🎉 Ready to test!"
