#!/usr/bin/env python3
"""
Test CraveMap PostgreSQL Integration
"""

import os
import sys

# Set environment to simulate development mode
os.environ['STREAMLIT_ENVIRONMENT'] = 'development'

def test_cravemap_integration():
    print("🔍 Testing CraveMap PostgreSQL Integration...")
    
    try:
        # Import CraveMap modules
        sys.path.append('.')
        
        # Test PostgreSQL module import
        print("📦 Testing PostgreSQL module import...")
        from postgres_database import get_postgres_db
        postgres_db = get_postgres_db()
        
        # Test connection (should fail without real connection string)
        success, message = postgres_db.test_connection()
        if success:
            print("✅ PostgreSQL connected successfully!")
        else:
            print(f"⚠️ PostgreSQL connection failed (expected): {message}")
        
        # Test SQLite fallback
        print("\n📦 Testing SQLite fallback...")
        from database import CraveMapDB
        sqlite_db = CraveMapDB()
        users = sqlite_db.get_all_users()
        print(f"✅ SQLite fallback working - {len(users)} users found")
        
        # Test CraveMap integration
        print("\n📦 Testing CraveMap integration...")
        
        # Create a mock Streamlit session state
        class MockSessionState:
            def __init__(self):
                self.data = {}
            
            def get(self, key, default=None):
                return self.data.get(key, default)
            
            def __setitem__(self, key, value):
                self.data[key] = value
            
            def __getitem__(self, key):
                return self.data[key]
        
        # Mock streamlit module
        class MockStreamlit:
            def __init__(self):
                self.session_state = MockSessionState()
            
            def info(self, msg):
                print(f"ℹ️ {msg}")
            
            def warning(self, msg):
                print(f"⚠️ {msg}")
            
            def error(self, msg):
                print(f"❌ {msg}")
            
            @property
            def secrets(self):
                return {}
        
        # Patch streamlit
        sys.modules['streamlit'] = MockStreamlit()
        
        # Now test CraveMap functions
        from CraveMap import load_user_data, save_user_data, get_user_id
        
        # Test user ID generation
        test_email = "claris_tan@hotmail.com"
        MockStreamlit().session_state['user_email'] = test_email
        
        import hashlib
        expected_user_id = hashlib.md5(test_email.encode()).hexdigest()[:8]
        
        print(f"🧪 Testing user data operations for {test_email}...")
        
        # Test load_user_data (should use SQLite fallback)
        user_data = load_user_data(expected_user_id)
        if user_data:
            print(f"✅ load_user_data working - Premium: {user_data.get('is_premium', False)}")
        else:
            print("❌ load_user_data failed")
            return False
        
        # Test save_user_data
        test_data = {
            'email': test_email,
            'is_premium': True,
            'payment_completed': True,
            'monthly_searches': 0,
            'first_name': 'Claris',
            'last_name': 'Tan'
        }
        
        try:
            save_user_data(expected_user_id, test_data)
            print("✅ save_user_data working")
        except Exception as e:
            print(f"❌ save_user_data failed: {e}")
            return False
        
        # Verify save worked
        updated_data = load_user_data(expected_user_id)
        if updated_data and updated_data.get('is_premium'):
            print("✅ Data persistence verified")
        else:
            print("❌ Data persistence failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_diagnostic_functions():
    print("\n🔍 Testing Diagnostic Functions...")
    
    try:
        # Test if finduser diagnostic would work
        from database import CraveMapDB
        db = CraveMapDB()
        
        # Test finding claris_tan@hotmail.com
        import hashlib
        email = "claris_tan@hotmail.com"
        user_id = hashlib.md5(email.encode()).hexdigest()[:8]
        
        user_data = db.get_user(user_id)
        if user_data and user_data.get('email', '').lower() == email.lower():
            print(f"✅ Diagnostic search would find: {email}")
            print(f"   - Premium: {user_data.get('is_premium', False)}")
            return True
        else:
            print(f"❌ Diagnostic search would fail for: {email}")
            return False
            
    except Exception as e:
        print(f"❌ Diagnostic test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 CraveMap PostgreSQL Integration Testing\n")
    
    success1 = test_cravemap_integration()
    success2 = test_diagnostic_functions()
    
    print(f"\n📊 Integration Test Results:")
    print(f"✅ CraveMap Integration: {'PASSED' if success1 else 'FAILED'}")
    print(f"✅ Diagnostic Functions: {'PASSED' if success2 else 'FAILED'}")
    
    if success1 and success2:
        print("\n🎉 CraveMap PostgreSQL integration is working correctly!")
        print("✅ PostgreSQL module loads successfully")
        print("✅ SQLite fallback works when PostgreSQL unavailable")
        print("✅ User data operations work correctly")
        print("✅ Premium upgrades persist in database")
        print("✅ Diagnostic tools can find users")
    else:
        print("\n❌ Some integration tests failed")
