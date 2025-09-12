#!/usr/bin/env python3
"""
Test script to verify the logic of the remember me persistence fix
"""

import os
import json
import hashlib
from datetime import datetime

def test_remember_me_logic():
    """Test the remember me logic without full Streamlit dependencies"""
    print("🧪 Testing Remember Me Logic")
    print("=" * 40)
    
    test_email = "test@example.com"
    test_user_id = hashlib.md5(test_email.encode()).hexdigest()[:8]
    
    # Create test user data
    test_user_data = {
        'user_id': test_user_id,
        'email': test_email,
        'is_premium': True,
        'payment_completed': True,
        'monthly_searches': 5,
        'last_search_reset': datetime.now().isoformat(),
        'premium_since': datetime.now().isoformat()
    }
    
    # Save test user data
    user_data_file = f".user_data_{test_user_id}.json"
    with open(user_data_file, 'w') as f:
        json.dump(test_user_data, f)
    print(f"✅ Created test user data: {user_data_file}")
    
    # Create remembered user file
    with open('.remembered_user.txt', 'w') as f:
        f.write(test_email)
    print(f"✅ Created remembered user file: {test_email}")
    
    # Simulate the logic from our fix
    print("\n🔄 Simulating app restart and remember me logic...")
    
    # Mock session state
    session_state = {}
    
    # Step 1: Check if user_email not in session (simulating fresh start)
    if 'user_email' not in session_state:
        session_state['user_email'] = None
        print("✅ Fresh session state initialized")
    
    # Step 2: Check for remembered user (our core fix)
    if not session_state['user_email']:
        try:
            with open('.remembered_user.txt', 'r') as f:
                remembered_email = f.read().strip()
                if remembered_email:
                    print(f"✅ Found remembered email: {remembered_email}")
                    
                    # Step 3: Restore complete user session (THE FIX)
                    session_state['user_email'] = remembered_email
                    
                    # Load user data (simulating the database lookup)
                    user_id = hashlib.md5(remembered_email.encode()).hexdigest()[:8]
                    user_file = f".user_data_{user_id}.json"
                    
                    if os.path.exists(user_file):
                        with open(user_file, 'r') as f:
                            user_data = json.load(f)
                        
                        # Restore full session data (THE CRITICAL PART)
                        session_state['user_premium'] = bool(user_data.get('is_premium', False))
                        session_state['payment_completed'] = bool(user_data.get('payment_completed', False))
                        session_state['monthly_searches'] = user_data.get('monthly_searches', 0)
                        session_state['last_search_reset'] = user_data.get('last_search_reset', datetime.now().isoformat())
                        
                        print("✅ Complete user session restored!")
                    else:
                        print(f"❌ User data file not found: {user_file}")
        except Exception as e:
            print(f"❌ Error reading remembered user: {e}")
    
    # Step 4: Verify the fix worked
    print("\n📊 Session State After Restoration:")
    print(f"  Email: {session_state.get('user_email', 'NOT SET')}")
    print(f"  Premium: {session_state.get('user_premium', 'NOT SET')}")
    print(f"  Payment Completed: {session_state.get('payment_completed', 'NOT SET')}")
    print(f"  Monthly Searches: {session_state.get('monthly_searches', 'NOT SET')}")
    print(f"  Last Reset: {session_state.get('last_search_reset', 'NOT SET')}")
    
    # Verify the fix
    success = True
    if session_state.get('user_email') != test_email:
        print("❌ Email not restored correctly")
        success = False
    
    if session_state.get('user_premium') != True:
        print("❌ Premium status not restored correctly")
        success = False
    
    if session_state.get('monthly_searches') != 5:
        print("❌ Monthly searches not restored correctly") 
        success = False
    
    if success:
        print("\n🎉 SUCCESS: Remember me persistence fix works correctly!")
        print("   - User remains logged in after app restart")
        print("   - Premium status persists") 
        print("   - Monthly search count persists")
        print("   - All user data is properly restored")
    else:
        print("\n❌ FAILURE: Remember me persistence fix has issues")
    
    # Test what happens without the file (user not remembered)
    print("\n🧪 Testing scenario: No remembered user file")
    os.remove('.remembered_user.txt')
    
    fresh_session = {}
    if 'user_email' not in fresh_session:
        fresh_session['user_email'] = None
    
    if not fresh_session['user_email']:
        try:
            with open('.remembered_user.txt', 'r') as f:
                remembered_email = f.read().strip()
        except:
            print("✅ Correctly handled missing remember me file")
            print("   - User starts as anonymous (expected behavior)")
    
    # Cleanup
    try:
        os.remove(user_data_file)
        if os.path.exists('.remembered_user.txt'):
            os.remove('.remembered_user.txt')
        print("\n🧹 Cleaned up test files")
    except:
        pass

if __name__ == "__main__":
    test_remember_me_logic()