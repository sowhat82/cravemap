"""
Local Testing Script for PostgreSQL Integration
Run this to test the PostgreSQL database connection and features
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_postgres_connection():
    """Test PostgreSQL connection without Streamlit"""
    print("🔗 Testing PostgreSQL Connection...")
    
    try:
        from postgres_database import PostgresDatabase
        
        # Initialize database
        postgres_db = PostgresDatabase()
        
        # Test connection
        success, message = postgres_db.test_connection()
        
        if success:
            print(f"✅ {message}")
            return postgres_db
        else:
            print(f"❌ {message}")
            return None
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def test_user_operations(postgres_db):
    """Test user creation, retrieval, and update operations"""
    print("\n👤 Testing User Operations...")
    
    test_email = "test_user@example.com"
    test_password_hash = "test_hash_12345"
    
    try:
        # Test user creation
        print(f"📝 Creating test user: {test_email}")
        success = postgres_db.create_user(
            email=test_email,
            password_hash=test_password_hash,
            first_name="Test",
            last_name="User",
            phone="123-456-7890"
        )
        
        if success:
            print("✅ User created successfully")
        else:
            print("⚠️ User creation failed (might already exist)")
        
        # Test user retrieval
        print(f"🔍 Retrieving user: {test_email}")
        user_data = postgres_db.get_user(test_email)
        
        if user_data:
            print("✅ User retrieved successfully")
            print(f"   - Email: {user_data['email']}")
            print(f"   - Name: {user_data['first_name']} {user_data['last_name']}")
            print(f"   - Premium: {user_data['is_premium']}")
        else:
            print("❌ User retrieval failed")
            return False
        
        # Test premium upgrade
        print(f"🌟 Testing premium upgrade for: {test_email}")
        from datetime import datetime, timedelta
        premium_expiry = datetime.now() + timedelta(days=30)
        
        upgrade_success = postgres_db.upgrade_to_premium(test_email, premium_expiry)
        
        if upgrade_success:
            print("✅ Premium upgrade successful")
            
            # Verify upgrade
            updated_user = postgres_db.get_user(test_email)
            if updated_user and updated_user['is_premium']:
                print("✅ Premium status verified")
                print(f"   - Premium Expiry: {updated_user['premium_expiry']}")
            else:
                print("❌ Premium status verification failed")
        else:
            print("❌ Premium upgrade failed")
        
        return True
        
    except Exception as e:
        print(f"❌ User operations test failed: {e}")
        return False

def test_persistence_simulation():
    """Simulate app restart by reconnecting to database"""
    print("\n🔄 Testing Persistence (Simulating App Restart)...")
    
    test_email = "claris_tan@hotmail.com"
    
    try:
        # Import here to avoid issues
        from postgres_database import PostgresDatabase
        
        # First connection - create user
        print("📱 First 'session' - Creating premium user...")
        postgres_db1 = PostgresDatabase()
        
        # Create user if not exists
        postgres_db1.create_user(
            email=test_email,
            password_hash="hash_for_claris",
            first_name="Claris",
            last_name="Tan"
        )
        
        # Upgrade to premium
        from datetime import datetime, timedelta
        premium_expiry = datetime.now() + timedelta(days=365)
        upgrade_success = postgres_db1.upgrade_to_premium(test_email, premium_expiry)
        
        if upgrade_success:
            print(f"✅ {test_email} upgraded to premium")
        else:
            print(f"⚠️ Premium upgrade failed (might already be premium)")
        
        # Simulate "app restart" by creating new database connection
        print("\n🔄 Simulating app restart (new database connection)...")
        postgres_db2 = PostgresDatabase()
        
        # Check if user data persists
        user_data = postgres_db2.get_user(test_email)
        
        if user_data:
            print(f"✅ User data persisted after 'restart'")
            print(f"   - Email: {user_data['email']}")
            print(f"   - Premium: {user_data['is_premium']}")
            print(f"   - Premium Expiry: {user_data['premium_expiry']}")
            
            if user_data['is_premium']:
                print("🎉 PERSISTENCE TEST PASSED - Premium status maintained!")
                return True
            else:
                print("❌ PERSISTENCE TEST FAILED - Premium status lost!")
                return False
        else:
            print("❌ PERSISTENCE TEST FAILED - User data lost!")
            return False
            
    except Exception as e:
        print(f"❌ Persistence test failed: {e}")
        return False

def main():
    print("🚀 CraveMap PostgreSQL Local Testing\n")
    
    # Check if connection string is configured
    connection_string = os.getenv("POSTGRES_CONNECTION_STRING")
    if not connection_string or "username:password" in connection_string:
        print("❌ PostgreSQL connection string not configured!")
        print("Please update the .env file with your actual Neon PostgreSQL connection string.")
        print("\nSteps to get connection string:")
        print("1. Go to https://neon.tech")
        print("2. Sign up for free account")
        print("3. Create a new project")
        print("4. Copy the connection string")
        print("5. Update POSTGRES_CONNECTION_STRING in .env file")
        return
    
    # Test 1: Connection
    postgres_db = test_postgres_connection()
    if not postgres_db:
        print("\n❌ Cannot proceed with tests - connection failed")
        return
    
    # Test 2: User Operations
    user_ops_success = test_user_operations(postgres_db)
    if not user_ops_success:
        print("\n❌ User operations test failed")
        return
    
    # Test 3: Persistence
    persistence_success = test_persistence_simulation()
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    print(f"✅ Connection Test: PASSED")
    print(f"✅ User Operations: {'PASSED' if user_ops_success else 'FAILED'}")
    print(f"✅ Persistence Test: {'PASSED' if persistence_success else 'FAILED'}")
    
    if user_ops_success and persistence_success:
        print("\n🎉 ALL TESTS PASSED! PostgreSQL integration is working correctly.")
        print("You can now run the CraveMap application with persistent data storage.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
