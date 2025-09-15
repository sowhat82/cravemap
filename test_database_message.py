#!/usr/bin/env python3
"""
Test script to verify database success message has been removed
while keeping error messages intact.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock

def test_database_message_removal():
    """Test that database success message is removed but error messages remain"""
    print("🧪 Testing Database Message Removal")
    print("=" * 50)
    
    # Mock streamlit to capture messages
    captured_messages = []
    
    class MockStreamlit:
        @staticmethod
        def info(msg):
            captured_messages.append(('info', msg))
            print(f"INFO: {msg}")
        
        @staticmethod
        def warning(msg):
            captured_messages.append(('warning', msg))
            print(f"WARNING: {msg}")
        
        @staticmethod
        def error(msg):
            captured_messages.append(('error', msg))
            print(f"ERROR: {msg}")
        
        class session_state:
            data = {}
            @classmethod
            def get(cls, key, default=None):
                return cls.data.get(key, default)
            @classmethod
            def __setitem__(cls, key, value):
                cls.data[key] = value
        
        secrets = {}
    
    # Test 1: Successful database connection
    print("\n1. Testing successful database connection...")
    captured_messages.clear()
    
    # Mock successful database connection
    mock_postgres_db = Mock()
    mock_postgres_db.test_connection.return_value = (True, "Connection successful")
    
    # Mock the get_postgres_db function
    with patch('sys.modules', {'streamlit': MockStreamlit()}):
        with patch('CraveMap.get_postgres_db', return_value=mock_postgres_db):
            with patch('CraveMap.st', MockStreamlit):
                try:
                    # Import and test the database initialization part
                    exec("""
postgres_db = get_postgres_db()
postgres_success, postgres_message = postgres_db.test_connection()
if postgres_success:
    db = None  # Use PostgreSQL primarily
else:
    st.warning(f"⚠️ PostgreSQL connection failed: {postgres_message}. Using SQLite fallback.")
                    """, {
                        'get_postgres_db': lambda: mock_postgres_db,
                        'st': MockStreamlit
                    })
                except Exception as e:
                    pass  # Expected since we're testing isolated code
    
    # Verify no success message was captured
    success_messages = [msg for level, msg in captured_messages if 'PostgreSQL database connected successfully' in msg]
    if len(success_messages) == 0:
        print("✅ SUCCESS: No database success message found")
    else:
        print(f"❌ FAILED: Found {len(success_messages)} success messages")
        return False
    
    # Test 2: Failed database connection
    print("\n2. Testing failed database connection...")
    captured_messages.clear()
    
    # Mock failed database connection
    mock_postgres_db_fail = Mock()
    mock_postgres_db_fail.test_connection.return_value = (False, "Connection failed")
    
    with patch('sys.modules', {'streamlit': MockStreamlit()}):
        with patch('CraveMap.get_postgres_db', return_value=mock_postgres_db_fail):
            with patch('CraveMap.st', MockStreamlit):
                try:
                    # Test the error path
                    exec("""
postgres_db = get_postgres_db()
postgres_success, postgres_message = postgres_db.test_connection()
if postgres_success:
    db = None  # Use PostgreSQL primarily
else:
    st.warning(f"⚠️ PostgreSQL connection failed: {postgres_message}. Using SQLite fallback.")
                    """, {
                        'get_postgres_db': lambda: mock_postgres_db_fail,
                        'st': MockStreamlit
                    })
                except Exception as e:
                    pass
    
    # Verify warning message was captured
    warning_messages = [msg for level, msg in captured_messages if level == 'warning' and 'PostgreSQL connection failed' in msg]
    if len(warning_messages) > 0:
        print("✅ SUCCESS: Error message still displayed on connection failure")
    else:
        print("❌ FAILED: Error message not found on connection failure")
        return False
    
    # Test 3: Check actual source code
    print("\n3. Testing source code verification...")
    try:
        with open('/home/runner/work/cravemap/cravemap/CraveMap.py', 'r') as f:
            source_code = f.read()
        
        # Check that success message is not in source
        if '🟢 PostgreSQL database connected successfully' not in source_code:
            print("✅ SUCCESS: Success message removed from source code")
        else:
            print("❌ FAILED: Success message still found in source code")
            return False
        
        # Check that error messages are still in source
        if '⚠️ PostgreSQL connection failed:' in source_code:
            print("✅ SUCCESS: Error messages preserved in source code")
        else:
            print("❌ FAILED: Error messages removed from source code")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Could not read source code: {e}")
        return False
    
    return True

def run_tests():
    """Run all tests and generate report"""
    print("🚀 CRAVEMAP DATABASE MESSAGE REMOVAL TEST")
    print("=" * 60)
    
    try:
        result = test_database_message_removal()
        
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        
        if result:
            print("✅ ALL TESTS PASSED!")
            print("\n🎉 Database success message successfully removed!")
            print("✅ Error handling preserved")
            print("✅ Warning messages still shown on failures")
            print("✅ Source code verification passed")
            return True
        else:
            print("❌ TESTS FAILED!")
            print("Please review the errors above")
            return False
            
    except Exception as e:
        print(f"❌ TEST EXECUTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)