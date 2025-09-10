import unittest
import tempfile
import os
import sys
from datetime import datetime
import sqlite3

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import CraveMapDB

class TestPromoCodeFunctionality(unittest.TestCase):
    """Test suite for promo code functionality and database persistence"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db_file.close()
        self.db = CraveMapDB(self.test_db_file.name)
        
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.test_db_file.name)
    
    def test_promo_code_constants(self):
        """Test that promo code constants are correctly defined"""
        # Import the constants from CraveMap
        import CraveMap
        
        self.assertEqual(CraveMap.ADMIN_UPGRADE_CODE, "cravemap2024premium")
        self.assertEqual(CraveMap.ADMIN_DOWNGRADE_CODE, "resetfree")
        self.assertEqual(CraveMap.ADMIN_RESET_COUNTER, "resetcounter")
    
    def test_database_save_premium_user(self):
        """Test saving a premium user to database"""
        user_id = "test_user_123"
        
        # Save user as premium
        self.db.save_user(
            user_id=user_id,
            email="test@example.com",
            is_premium=True,
            payment_completed=True,
            monthly_searches=5
        )
        
        # Retrieve user data
        user_data = self.db.get_user(user_id)
        
        # Verify premium status persisted
        self.assertTrue(user_data['is_premium'])
        self.assertTrue(user_data['payment_completed'])
        self.assertEqual(user_data['email'], "test@example.com")
        self.assertEqual(user_data['monthly_searches'], 5)
    
    def test_promo_code_upgrade_downgrade_cycle(self):
        """Test full upgrade -> downgrade -> upgrade cycle"""
        user_id = "test_cycle_user"
        
        # Start as free user
        self.db.save_user(user_id=user_id, email="cycle@test.com", is_premium=False)
        user_data = self.db.get_user(user_id)
        self.assertFalse(user_data['is_premium'])
        
        # Upgrade to premium (simulate promo code)
        self.db.save_user(
            user_id=user_id,
            email="cycle@test.com",
            is_premium=True,
            payment_completed=True,
            monthly_searches=user_data['monthly_searches']
        )
        user_data = self.db.get_user(user_id)
        self.assertTrue(user_data['is_premium'])
        
        # Downgrade to free (simulate reset promo)
        self.db.save_user(
            user_id=user_id,
            email="cycle@test.com",
            is_premium=False,
            payment_completed=False,
            monthly_searches=user_data['monthly_searches']
        )
        user_data = self.db.get_user(user_id)
        self.assertFalse(user_data['is_premium'])
        
        # Upgrade again
        self.db.save_user(
            user_id=user_id,
            email="cycle@test.com",
            is_premium=True,
            payment_completed=True,
            monthly_searches=user_data['monthly_searches']
        )
        user_data = self.db.get_user(user_id)
        self.assertTrue(user_data['is_premium'])
    
    def test_search_counter_reset(self):
        """Test search counter reset functionality"""
        user_id = "test_counter_user"
        
        # Create user with some searches
        self.db.save_user(
            user_id=user_id,
            email="counter@test.com",
            is_premium=False,
            monthly_searches=8
        )
        user_data = self.db.get_user(user_id)
        self.assertEqual(user_data['monthly_searches'], 8)
        
        # Reset counter (simulate reset promo)
        self.db.save_user(
            user_id=user_id,
            email="counter@test.com",
            is_premium=user_data['is_premium'],
            payment_completed=user_data['payment_completed'],
            monthly_searches=0
        )
        user_data = self.db.get_user(user_id)
        self.assertEqual(user_data['monthly_searches'], 0)
    
    def test_database_persistence_across_connections(self):
        """Test that data persists when database is reopened"""
        user_id = "persistence_test"
        
        # Save data with first connection
        self.db.save_user(
            user_id=user_id,
            email="persist@test.com",
            is_premium=True,
            payment_completed=True
        )
        
        # Close and reopen database
        db_path = self.db.db_path
        del self.db
        
        # Create new database connection
        new_db = CraveMapDB(db_path)
        
        # Verify data persisted
        user_data = new_db.get_user(user_id)
        self.assertTrue(user_data['is_premium'])
        self.assertTrue(user_data['payment_completed'])
        self.assertEqual(user_data['email'], "persist@test.com")
    
    def test_multiple_users_independence(self):
        """Test that multiple users maintain independent premium status"""
        user1_id = "user1"
        user2_id = "user2"
        
        # Create two users with different statuses
        self.db.save_user(user_id=user1_id, email="user1@test.com", is_premium=True)
        self.db.save_user(user_id=user2_id, email="user2@test.com", is_premium=False)
        
        # Verify independence
        user1_data = self.db.get_user(user1_id)
        user2_data = self.db.get_user(user2_id)
        
        self.assertTrue(user1_data['is_premium'])
        self.assertFalse(user2_data['is_premium'])
        
        # Change user2, verify user1 unaffected
        self.db.save_user(user_id=user2_id, email="user2@test.com", is_premium=True)
        
        user1_data = self.db.get_user(user1_id)
        user2_data = self.db.get_user(user2_id)
        
        self.assertTrue(user1_data['is_premium'])  # Should still be premium
        self.assertTrue(user2_data['is_premium'])  # Should now be premium

class TestPromoCodeIntegration(unittest.TestCase):
    """Integration tests for promo code functionality in the app"""
    
    def test_promo_code_validation(self):
        """Test promo code string matching"""
        test_codes = [
            ("cravemap2024premium", True),
            ("CRAVEMAP2024PREMIUM", False),  # Case sensitive
            ("cravemap2024premium ", False),  # Trailing space
            (" cravemap2024premium", False),  # Leading space
            ("resetfree", True),
            ("resetcounter", True),
            ("invalid_code", False),
            ("", False)
        ]
        
        # Import constants
        import CraveMap
        
        for test_code, expected_match in test_codes:
            with self.subTest(code=test_code):
                matches_upgrade = (test_code == CraveMap.ADMIN_UPGRADE_CODE)
                matches_downgrade = (test_code == CraveMap.ADMIN_DOWNGRADE_CODE)
                matches_reset = (test_code == CraveMap.ADMIN_RESET_COUNTER)
                
                is_valid = matches_upgrade or matches_downgrade or matches_reset
                
                if expected_match:
                    self.assertTrue(is_valid, f"Code '{test_code}' should be valid")
                else:
                    self.assertFalse(is_valid, f"Code '{test_code}' should be invalid")

def run_promo_code_debug():
    """Debug function to test current promo code state"""
    print("🔍 PROMO CODE DEBUG ANALYSIS")
    print("=" * 50)
    
    # Test database directly
    db = CraveMapDB()
    
    # Create test user
    test_user_id = "debug_test_user"
    print(f"Testing with user ID: {test_user_id}")
    
    # Test 1: Save as premium user
    print("\n1. Saving user as premium...")
    db.save_user(
        user_id=test_user_id,
        email="debug@test.com",
        is_premium=True,
        payment_completed=True,
        monthly_searches=0
    )
    
    # Test 2: Retrieve user data
    print("2. Retrieving user data...")
    user_data = db.get_user(test_user_id)
    print(f"   User data: {user_data}")
    print(f"   is_premium: {user_data.get('is_premium')}")
    print(f"   payment_completed: {user_data.get('payment_completed')}")
    
    # Test 3: Test constants
    import CraveMap
    print(f"\n3. Testing constants...")
    print(f"   ADMIN_UPGRADE_CODE: '{CraveMap.ADMIN_UPGRADE_CODE}'")
    print(f"   Test string: 'cravemap2024premium'")
    print(f"   Match: {CraveMap.ADMIN_UPGRADE_CODE == 'cravemap2024premium'}")
    
    # Test 4: Database verification
    print(f"\n4. Direct database check...")
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, email, is_premium, payment_completed FROM users WHERE user_id = ?",
            (test_user_id,)
        ).fetchone()
        if row:
            print(f"   Database row: {dict(row)}")
        else:
            print("   No user found in database!")
    
    print("\n" + "=" * 50)
    print("Debug complete. Check the output above for issues.")

if __name__ == "__main__":
    # Run debug first
    print("Running promo code debug analysis...")
    run_promo_code_debug()
    
    print("\n" + "="*60)
    print("Running unit tests...")
    unittest.main(verbosity=2)
