"""
Database Migration Script: SQLite to PostgreSQL
This script migrates existing user data from SQLite to PostgreSQL
"""

import sqlite3
import sys
import os
from postgres_database import get_postgres_db
from database import CraveMapDB
import streamlit as st

def migrate_sqlite_to_postgres():
    """Migrate all data from SQLite to PostgreSQL"""
    print("Starting migration from SQLite to PostgreSQL...")
    
    try:
        # Initialize PostgreSQL database
        postgres_db = get_postgres_db()
        
        # Test PostgreSQL connection
        success, message = postgres_db.test_connection()
        if not success:
            print(f"❌ PostgreSQL connection failed: {message}")
            return False
        
        print("✅ PostgreSQL connection successful")
        
        # Check if SQLite database exists
        sqlite_path = "cravemap.db"
        if not os.path.exists(sqlite_path):
            print(f"❌ SQLite database not found at {sqlite_path}")
            return False
        
        print(f"✅ SQLite database found at {sqlite_path}")
        
        # Get all users from SQLite
        try:
            sqlite_db = CraveMapDB()
            sqlite_users = sqlite_db.get_all_users()
            print(f"📊 Found {len(sqlite_users)} users in SQLite database")
        except Exception as e:
            print(f"❌ Error reading SQLite database: {e}")
            return False
        
        if not sqlite_users:
            print("ℹ️ No users found in SQLite database - nothing to migrate")
            return True
        
        # Migrate each user
        migrated_count = 0
        failed_count = 0
        
        for user_record in sqlite_users:
            try:
                # SQLite returns records as tuples, extract email
                user_email = user_record[1] if isinstance(user_record, tuple) else user_record.get('email', '')
                
                if not user_email:
                    print(f"⚠️ No email found for user record: {user_record}")
                    failed_count += 1
                    continue
                
                # Get full user data from SQLite using the user's ID
                user_id = user_record[0] if isinstance(user_record, tuple) else user_record.get('user_id', '')
                user_data = sqlite_db.get_user(user_id)
                
                if not user_data:
                    print(f"⚠️ No data found for user: {user_email}")
                    failed_count += 1
                    continue
                
                # Create user in PostgreSQL
                success = postgres_db.create_user(
                    email=user_data['email'],
                    password_hash=user_data['password'],
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    phone=user_data.get('phone', '')
                )
                
                if success:
                    # Update premium status if applicable
                    if user_data.get('is_premium', False):
                        postgres_db.upgrade_to_premium(
                            user_data['email'], 
                            user_data.get('premium_expiry')
                        )
                        print(f"✅ Migrated PREMIUM user: {user_email}")
                    else:
                        print(f"✅ Migrated user: {user_email}")
                    
                    migrated_count += 1
                else:
                    print(f"❌ Failed to migrate user: {user_email}")
                    failed_count += 1
                    
            except Exception as e:
                print(f"❌ Error migrating user {user_email}: {e}")
                failed_count += 1
        
        print(f"\n📊 Migration Summary:")
        print(f"   Total users: {len(sqlite_users)}")
        print(f"   ✅ Successfully migrated: {migrated_count}")
        print(f"   ❌ Failed to migrate: {failed_count}")
        
        return migrated_count > 0
        
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    print("\n🔍 Verifying migration...")
    
    try:
        postgres_db = get_postgres_db()
        
        # Get user count from PostgreSQL
        postgres_count = postgres_db.get_user_count()
        print(f"📊 PostgreSQL user count: {postgres_count}")
        
        # Get all users from PostgreSQL
        postgres_users = postgres_db.get_all_users()
        
        print(f"\n👥 Users in PostgreSQL:")
        for user in postgres_users:
            premium_status = "PREMIUM" if user['is_premium'] else "FREE"
            premium_expiry = f" (expires: {user['premium_expiry']})" if user['premium_expiry'] else ""
            print(f"   - {user['email']} [{premium_status}]{premium_expiry}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def test_specific_user(email):
    """Test a specific user in PostgreSQL"""
    print(f"\n🔍 Testing user: {email}")
    
    try:
        postgres_db = get_postgres_db()
        user_data = postgres_db.get_user(email)
        
        if user_data:
            print(f"✅ User found in PostgreSQL:")
            print(f"   Email: {user_data['email']}")
            print(f"   Name: {user_data['first_name']} {user_data['last_name']}")
            print(f"   Premium: {user_data['is_premium']}")
            if user_data['premium_expiry']:
                print(f"   Premium Expiry: {user_data['premium_expiry']}")
            return True
        else:
            print(f"❌ User not found in PostgreSQL")
            return False
            
    except Exception as e:
        print(f"❌ Error testing user: {e}")
        return False

if __name__ == "__main__":
    print("🚀 CraveMap Database Migration Tool\n")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "migrate":
            migrate_sqlite_to_postgres()
            verify_migration()
        elif command == "verify":
            verify_migration()
        elif command == "test" and len(sys.argv) > 2:
            test_specific_user(sys.argv[2])
        else:
            print("Usage:")
            print("  python migrate_database.py migrate    # Migrate SQLite to PostgreSQL")
            print("  python migrate_database.py verify     # Verify migration")
            print("  python migrate_database.py test <email>  # Test specific user")
    else:
        print("Usage:")
        print("  python migrate_database.py migrate    # Migrate SQLite to PostgreSQL")
        print("  python migrate_database.py verify     # Verify migration")
        print("  python migrate_database.py test <email>  # Test specific user")
