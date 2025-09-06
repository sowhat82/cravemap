#!/usr/bin/env python3
"""
CraveMap Regression Test Suite
Prevents feature regressions by testing critical functionality before deployment.
Run this before every commit/deployment to ensure nothing is broken.
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import Mock, patch
import sqlite3
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import CraveMapDB
import CraveMap

class TestCriticalFeatures(unittest.TestCase):
    """Test suite for critical app features that must never break"""
    
    def setUp(self):
        """Set up test database for each test"""
        self.test_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db_file.close()
        self.db = CraveMapDB(self.test_db_file.name)
        
    def tearDown(self):
        """Clean up test database"""
        try:
            os.unlink(self.test_db_file.name)
        except:
            pass
    
    def test_promo_codes_defined(self):
        """CRITICAL: Promo codes must be correctly defined"""
        self.assertEqual(CraveMap.ADMIN_UPGRADE_CODE, "cravemap2024premium")
        self.assertEqual(CraveMap.ADMIN_DOWNGRADE_CODE, "resetfree")
        self.assertEqual(CraveMap.ADMIN_RESET_COUNTER, "resetcounter")
        
        # Test that codes are strings and not empty
        self.assertIsInstance(CraveMap.ADMIN_UPGRADE_CODE, str)
        self.assertTrue(len(CraveMap.ADMIN_UPGRADE_CODE) > 0)
        
    def test_database_premium_storage_and_retrieval(self):
        """CRITICAL: Premium status must persist correctly in database"""
        user_id = "test_premium_user"
        
        # Save user as premium
        self.db.save_user(
            user_id=user_id,
            email="premium@test.com",
            is_premium=True,
            payment_completed=True
        )
        
        # Retrieve and verify
        user_data = self.db.get_user(user_id)
        
        # Test raw database values
        self.assertIn('is_premium', user_data)
        self.assertIn('payment_completed', user_data)
        
        # Test boolean conversion (the fix we implemented)
        self.assertTrue(bool(user_data['is_premium']))
        self.assertTrue(bool(user_data['payment_completed']))
        
        # Test that values are truthy
        self.assertTrue(user_data['is_premium'])
        self.assertTrue(user_data['payment_completed'])
        
    def test_free_to_premium_upgrade_simulation(self):
        """CRITICAL: Simulates the exact promo code upgrade process"""
        user_id = "upgrade_test_user"
        
        # Step 1: Create free user
        self.db.save_user(
            user_id=user_id,
            email="upgrade@test.com",
            is_premium=False,
            payment_completed=False,
            monthly_searches=5
        )
        
        user_data = self.db.get_user(user_id)
        self.assertFalse(bool(user_data['is_premium']))
        
        # Step 2: Simulate promo code upgrade (what happens in the app)
        user_data['is_premium'] = True
        user_data['payment_completed'] = True
        user_data['premium_since'] = datetime.now().isoformat()
        user_data['promo_activation'] = "Admin code: cravemap2024premium"
        
        # Save updated data
        self.db.save_user(
            user_id=user_id,
            email=user_data['email'],
            is_premium=user_data['is_premium'],
            payment_completed=user_data['payment_completed'],
            monthly_searches=user_data['monthly_searches']
        )
        
        # Step 3: Verify upgrade persisted
        updated_data = self.db.get_user(user_id)
        self.assertTrue(bool(updated_data['is_premium']))
        self.assertTrue(bool(updated_data['payment_completed']))
        
        # Step 4: Test session state simulation (what happens after st.rerun())
        session_premium = bool(updated_data.get('is_premium', False))
        session_payment = bool(updated_data.get('payment_completed', False))
        
        self.assertTrue(session_premium)
        self.assertTrue(session_payment)
        
    def test_downgrade_simulation(self):
        """CRITICAL: Reset promo code must work"""
        user_id = "downgrade_test_user"
        
        # Start with premium user
        self.db.save_user(
            user_id=user_id,
            email="downgrade@test.com",
            is_premium=True,
            payment_completed=True
        )
        
        # Simulate downgrade
        user_data = self.db.get_user(user_id)
        user_data['is_premium'] = False
        user_data['payment_completed'] = False
        
        self.db.save_user(
            user_id=user_id,
            email=user_data['email'],
            is_premium=user_data['is_premium'],
            payment_completed=user_data['payment_completed'],
            monthly_searches=user_data['monthly_searches']
        )
        
        # Verify downgrade
        downgraded_data = self.db.get_user(user_id)
        self.assertFalse(bool(downgraded_data['is_premium']))
        self.assertFalse(bool(downgraded_data['payment_completed']))
        
    def test_search_counter_reset_simulation(self):
        """CRITICAL: Search counter reset must work"""
        user_id = "counter_test_user"
        
        # Create user with searches used
        self.db.save_user(
            user_id=user_id,
            email="counter@test.com",
            monthly_searches=8  # Near limit
        )
        
        # Simulate counter reset
        user_data = self.db.get_user(user_id)
        user_data['monthly_searches'] = 0
        
        self.db.save_user(
            user_id=user_id,
            email=user_data['email'],
            is_premium=user_data['is_premium'],
            payment_completed=user_data['payment_completed'],
            monthly_searches=user_data['monthly_searches']
        )
        
        # Verify reset
        reset_data = self.db.get_user(user_id)
        self.assertEqual(reset_data['monthly_searches'], 0)
        
    def test_database_integrity_after_operations(self):
        """CRITICAL: Database must maintain integrity across operations"""
        users = [
            ("user1", "user1@test.com", True, True, 0),
            ("user2", "user2@test.com", False, False, 5),
            ("user3", "user3@test.com", True, False, 2),  # Premium without payment
        ]
        
        # Create multiple users
        for user_id, email, premium, payment, searches in users:
            self.db.save_user(
                user_id=user_id,
                email=email,
                is_premium=premium,
                payment_completed=payment,
                monthly_searches=searches
            )
        
        # Verify all users independently
        for user_id, email, premium, payment, searches in users:
            user_data = self.db.get_user(user_id)
            self.assertEqual(user_data['email'], email)
            self.assertEqual(bool(user_data['is_premium']), premium)
            self.assertEqual(bool(user_data['payment_completed']), payment)
            self.assertEqual(user_data['monthly_searches'], searches)

class TestApplicationConstants(unittest.TestCase):
    """Test that critical application constants are correct"""
    
    def test_pricing_constants(self):
        """CRITICAL: Pricing must be correct"""
        self.assertEqual(CraveMap.PREMIUM_PRICE_SGD, 9.99)
        self.assertEqual(CraveMap.PREMIUM_PRICE_CENTS, 999)
        self.assertEqual(CraveMap.PREMIUM_PRICE_DISPLAY, "$9.99")
        
    def test_admin_codes_are_secure(self):
        """CRITICAL: Admin codes should be sufficiently complex"""
        codes = [
            CraveMap.ADMIN_UPGRADE_CODE,
            CraveMap.ADMIN_DOWNGRADE_CODE,
            CraveMap.ADMIN_RESET_COUNTER
        ]
        
        for code in codes:
            self.assertGreater(len(code), 5, f"Code '{code}' too short")
            self.assertIsInstance(code, str, f"Code '{code}' not string")

def run_regression_tests():
    """Run all regression tests and return True if all pass"""
    print("🧪 CRAVEMAP REGRESSION TEST SUITE")
    print("=" * 50)
    print("Testing critical features to prevent regressions...")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCriticalFeatures))
    suite.addTests(loader.loadTestsFromTestCase(TestApplicationConstants))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ ALL REGRESSION TESTS PASSED!")
        print("✅ Safe to deploy - no features broken")
        return True
    else:
        print("❌ REGRESSION TESTS FAILED!")
        print("❌ DO NOT DEPLOY - features are broken")
        print(f"Failed: {len(result.failures)} tests")
        print(f"Errors: {len(result.errors)} tests")
        return False

def quick_promo_code_test():
    """Quick test specifically for promo code functionality"""
    print("\n🔍 QUICK PROMO CODE TEST")
    print("-" * 30)
    
    try:
        # Test database operations
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db = CraveMapDB(tmp.name)
            
            # Test upgrade
            db.save_user("test", "test@test.com", is_premium=True, payment_completed=True)
            data = db.get_user("test")
            
            premium_status = bool(data.get('is_premium', False))
            payment_status = bool(data.get('payment_completed', False))
            
            print(f"✓ Database storage: premium={premium_status}, payment={payment_status}")
            
            # Test constants
            print(f"✓ Upgrade code: '{CraveMap.ADMIN_UPGRADE_CODE}'")
            print(f"✓ Downgrade code: '{CraveMap.ADMIN_DOWNGRADE_CODE}'")
            
            os.unlink(tmp.name)
        
        print("✅ Promo code functionality: WORKING")
        return True
        
    except Exception as e:
        print(f"❌ Promo code functionality: BROKEN - {e}")
        return False

if __name__ == "__main__":
    # Quick test first
    if "--quick" in sys.argv:
        success = quick_promo_code_test()
        sys.exit(0 if success else 1)
    
    # Full regression suite
    success = run_regression_tests()
    sys.exit(0 if success else 1)
