#!/usr/bin/env python3
"""
API Key Management Tool for Lookup API

Usage:
  python manage_keys.py create <username> <password> [--balance AMOUNT]
  python manage_keys.py list
  python manage_keys.py balance <username>
  python manage_keys.py add-balance <username> <amount>
  python manage_keys.py deactivate <username>
  python manage_keys.py activate <username>
"""

import argparse
import os
import secrets
import sqlite3
import sys
from pathlib import Path

# Import from app.py
sys.path.insert(0, str(Path(__file__).parent))
from app import _conn, _hash_pw, DB_PATH


def create_key(username: str, password: str, initial_balance: float = 0.0) -> dict:
    """Create a new API key."""
    conn = _conn()
    try:
        # Check if user exists
        existing = conn.execute(
            "SELECT * FROM api_keys WHERE username = ?", (username,)
        ).fetchone()
        
        if existing:
            return {
                "success": False,
                "error": f"User '{username}' already exists",
                "api_key": existing["api_key"],
            }
        
        # Create new key
        api_key = secrets.token_hex(32)
        conn.execute(
            "INSERT INTO api_keys (username, password_hash, api_key, balance) VALUES (?,?,?,?)",
            (username, _hash_pw(password), api_key, initial_balance),
        )
        conn.commit()
        
        return {
            "success": True,
            "username": username,
            "api_key": api_key,
            "balance": initial_balance,
        }
    finally:
        conn.close()


def list_keys() -> list:
    """List all API keys."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, username, api_key, balance, is_active, created_at FROM api_keys ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_balance(username: str) -> dict:
    """Get balance for a user."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT username, balance, is_active FROM api_keys WHERE username = ?",
            (username,)
        ).fetchone()
        
        if not row:
            return {"success": False, "error": f"User '{username}' not found"}
        
        return {
            "success": True,
            "username": row["username"],
            "balance": row["balance"],
            "is_active": bool(row["is_active"]),
        }
    finally:
        conn.close()


def add_balance(username: str, amount: float) -> dict:
    """Add balance to a user."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT id, balance FROM api_keys WHERE username = ?", (username,)
        ).fetchone()
        
        if not row:
            return {"success": False, "error": f"User '{username}' not found"}
        
        new_balance = row["balance"] + amount
        conn.execute(
            "UPDATE api_keys SET balance = ? WHERE id = ?",
            (new_balance, row["id"])
        )
        conn.execute(
            "INSERT INTO billing_log (api_key_id, entry_type, amount, service, description) VALUES (?,?,?,?,?)",
            (row["id"], "credit", amount, "manual", f"Manual balance adjustment: +${amount}"),
        )
        conn.commit()
        
        return {
            "success": True,
            "username": username,
            "old_balance": row["balance"],
            "new_balance": new_balance,
            "added": amount,
        }
    finally:
        conn.close()


def set_active(username: str, active: bool) -> dict:
    """Activate or deactivate a user."""
    conn = _conn()
    try:
        result = conn.execute(
            "UPDATE api_keys SET is_active = ? WHERE username = ?",
            (1 if active else 0, username)
        )
        conn.commit()
        
        if result.rowcount == 0:
            return {"success": False, "error": f"User '{username}' not found"}
        
        return {
            "success": True,
            "username": username,
            "is_active": active,
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Manage Lookup API keys")
    parser.add_argument("--db", help="Database path (default: from LOOKUP_DB_PATH env)")
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # create
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("username", help="Username")
    create_parser.add_argument("password", help="Password")
    create_parser.add_argument("--balance", type=float, default=0.0, help="Initial balance")
    
    # list
    subparsers.add_parser("list", help="List all API keys")
    
    # balance
    balance_parser = subparsers.add_parser("balance", help="Get user balance")
    balance_parser.add_argument("username", help="Username")
    
    # add-balance
    add_balance_parser = subparsers.add_parser("add-balance", help="Add balance to user")
    add_balance_parser.add_argument("username", help="Username")
    add_balance_parser.add_argument("amount", type=float, help="Amount to add")
    
    # deactivate
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a user")
    deactivate_parser.add_argument("username", help="Username")
    
    # activate
    activate_parser = subparsers.add_parser("activate", help="Activate a user")
    activate_parser.add_argument("username", help="Username")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Override DB path if provided
    if args.db:
        global DB_PATH
        DB_PATH = Path(args.db)
        os.environ["LOOKUP_DB_PATH"] = str(DB_PATH)
    
    # Check DB exists
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run the API server first to initialize the database.")
        sys.exit(1)
    
    # Execute command
    if args.command == "create":
        result = create_key(args.username, args.password, args.balance)
        if result["success"]:
            print(f"✅ Created API key for '{args.username}'")
            print(f"   API Key: {result['api_key']}")
            print(f"   Balance: ${result['balance']:.2f}")
        else:
            print(f"❌ {result['error']}")
            if "api_key" in result:
                print(f"   Existing API Key: {result['api_key']}")
    
    elif args.command == "list":
        keys = list_keys()
        if not keys:
            print("No API keys found.")
        else:
            print(f"\n{'Username':<20} {'API Key':<65} {'Balance':<12} {'Active':<8} {'Created'}")
            print("-" * 130)
            for key in keys:
                active = "✅" if key["is_active"] else "❌"
                print(f"{key['username']:<20} {key['api_key']:<65} ${key['balance']:<11.2f} {active:<8} {key['created_at']}")
    
    elif args.command == "balance":
        result = get_balance(args.username)
        if result["success"]:
            active = "✅ Active" if result["is_active"] else "❌ Inactive"
            print(f"User: {result['username']}")
            print(f"Balance: ${result['balance']:.2f}")
            print(f"Status: {active}")
        else:
            print(f"❌ {result['error']}")
    
    elif args.command == "add-balance":
        result = add_balance(args.username, args.amount)
        if result["success"]:
            print(f"✅ Added ${result['added']:.2f} to '{result['username']}'")
            print(f"   Old balance: ${result['old_balance']:.2f}")
            print(f"   New balance: ${result['new_balance']:.2f}")
        else:
            print(f"❌ {result['error']}")
    
    elif args.command == "deactivate":
        result = set_active(args.username, False)
        if result["success"]:
            print(f"✅ Deactivated user '{result['username']}'")
        else:
            print(f"❌ {result['error']}")
    
    elif args.command == "activate":
        result = set_active(args.username, True)
        if result["success"]:
            print(f"✅ Activated user '{result['username']}'")
        else:
            print(f"❌ {result['error']}")


if __name__ == "__main__":
    main()
