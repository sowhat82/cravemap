#!/usr/bin/env python3
"""
Simple SQLite test script for CraveMap
"""

from database import CraveMapDB
import hashlib
from datetime import datetime

def test_sqlite_operations():
    print("🔍 Testing SQLite Database Operations...")
    
    # Initialize database
    db = CraveMapDB()
    
    # Test user
    email = "claris_tan@hotmail.com"
    user_id = hashlib.md5(email.encode()).hexdigest()[:8]
    
    print(f"📧 Testing user: {email} (ID: {user_id})")
    
    # Check current status
    user = db.get_user(user_id)
    if user:
        print(f"✅ User exists - Premium: {user['is_premium']}")
    else:
        print("❌ User not found")
        return False
    
    # Upgrade to premium
    print("🌟 Upgrading to premium...")
    db.save_user(
        user_id=user_id,
        email=email,
        is_premium=True,
        payment_completed=True,
        premium_since=datetime.now().isoformat(),
        promo_activation="Test upgrade via SQLite"
    )
    
    # Verify upgrade
    user_after = db.get_user(user_id)
    if user_after and user_after['is_premium']:
        print("✅ Premium upgrade successful in SQLite!")
        print(f"   - Premium: {user_after['is_premium']}")
        print(f"   - Payment Completed: {user_after['payment_completed']}")
        print(f"   - Premium Since: {user_after.get('premium_since', 'N/A')}")
        return True
    else:
        print("❌ Premium upgrade failed")
        return False

def test_persistence():
    print("\n🔄 Testing SQLite Persistence...")
    
    # Create new database connection (simulating restart)
    db = CraveMapDB()
    
    email = "claris_tan@hotmail.com"
    user_id = hashlib.md5(email.encode()).hexdigest()[:8]
    
    # Check if premium status persists
    user = db.get_user(user_id)
    if user and user['is_premium']:
        print("✅ Premium status persisted in SQLite!")
        return True
    else:
        print("❌ Premium status lost in SQLite")
        return False

if __name__ == "__main__":
    print("🚀 CraveMap SQLite Testing\n")
    
    success1 = test_sqlite_operations()
    success2 = test_persistence()
    
    print(f"\n📊 Test Results:")
    print(f"✅ SQLite Operations: {'PASSED' if success1 else 'FAILED'}")
    print(f"✅ SQLite Persistence: {'PASSED' if success2 else 'FAILED'}")
    
    if success1 and success2:
        print("\n🎉 SQLite fallback is working correctly!")
    else:
        print("\n❌ SQLite tests failed")
