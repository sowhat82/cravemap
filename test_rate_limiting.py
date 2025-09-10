import streamlit as st
import json
import os
from datetime import datetime, timedelta
import uuid

def test_rate_limiting():
    """Test the rate limiting functionality"""
    
    # Simulate different user sessions
    test_users = [
        {"user_id": "test_user_1", "name": "Free User 1"},
        {"user_id": "test_user_2", "name": "Free User 2"},
        {"user_id": "test_user_3", "name": "Premium User"},
    ]
    
    print("🧪 Testing Rate Limiting System")
    print("=" * 50)
    
    # Load existing user data
    try:
        with open('.user_data.json', 'r') as f:
            all_user_data = json.load(f)
    except FileNotFoundError:
        all_user_data = {}
    
    for user in test_users:
        user_id = user["user_id"]
        name = user["name"]
        
        print(f"\n👤 Testing {name} ({user_id})")
        
        # Get or create user data
        if user_id not in all_user_data:
            all_user_data[user_id] = {
                'user_id': user_id,
                'email': f"{user_id}@test.com",
                'created_at': datetime.now().isoformat(),
                'is_premium': user_id == "test_user_3",  # Make user 3 premium
                'payment_completed': user_id == "test_user_3",
                'searches_this_month': 0,
                'last_search': None,
                'stripe_customer_id': None
            }
        
        user_data = all_user_data[user_id]
        
        # Test rate limiting logic
        is_premium = user_data.get('is_premium', False)
        searches_this_month = user_data.get('searches_this_month', 0)
        
        print(f"   Premium Status: {'✅ Premium' if is_premium else '❌ Free'}")
        print(f"   Searches This Month: {searches_this_month}")
        
        # Simulate searches
        if is_premium:
            print(f"   ✅ Premium user - unlimited searches allowed")
            for i in range(5):
                print(f"      Search {i+1}: ✅ Allowed")
        else:
            print(f"   Rate Limit Test (Free tier - 3 searches max):")
            for i in range(5):
                if searches_this_month + i < 3:
                    print(f"      Search {i+1}: ✅ Allowed ({searches_this_month + i + 1}/3)")
                else:
                    print(f"      Search {i+1}: ❌ BLOCKED - Rate limit exceeded")
        
        # Update search count for testing
        if not is_premium:
            user_data['searches_this_month'] = min(searches_this_month + 3, 5)
        
        all_user_data[user_id] = user_data
    
    # Save updated data
    with open('.user_data.json', 'w') as f:
        json.dump(all_user_data, f, indent=2)
    
    print(f"\n✅ Rate limiting test completed!")
    print(f"📁 Test user data saved to .user_data.json")
    
    # Test monthly reset logic
    print(f"\n🗓️ Testing Monthly Reset Logic")
    current_time = datetime.now()
    last_month = current_time - timedelta(days=32)
    
    print(f"   Current time: {current_time.strftime('%Y-%m-%d')}")
    print(f"   Simulated last search: {last_month.strftime('%Y-%m-%d')}")
    
    # Check if reset would occur
    if last_month.month != current_time.month or last_month.year != current_time.year:
        print(f"   ✅ Monthly reset would trigger - searches would be reset to 0")
    else:
        print(f"   ❌ No reset needed - same month")

if __name__ == "__main__":
    test_rate_limiting()
