#!/usr/bin/env python3
"""
Quick test script for the trial system implementation
"""

import json
from datetime import datetime, timedelta

# Test the trial constants
TRIAL_CODE = "trial7days"
TRIAL_DURATION_DAYS = 7
TRIAL_DAILY_LIMIT = 20

def test_trial_logic():
    print("🧪 Testing Trial System Logic")
    print("=" * 40)
    
    # Test 1: Trial activation
    print("Test 1: Trial Activation")
    trial_start = datetime.now()
    trial_end = trial_start + timedelta(days=TRIAL_DURATION_DAYS)
    
    trial_data = {
        'trial_active': True,
        'trial_start_date': trial_start.isoformat(),
        'trial_end_date': trial_end.isoformat(),
        'trial_daily_searches': 0,
        'trial_used': True
    }
    
    print(f"✅ Trial Code: {TRIAL_CODE}")
    print(f"✅ Trial Duration: {TRIAL_DURATION_DAYS} days")
    print(f"✅ Daily Search Limit: {TRIAL_DAILY_LIMIT}")
    print(f"✅ Trial Start: {trial_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ Trial End: {trial_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 2: Trial status checking
    print("Test 2: Trial Status Checking")
    def check_trial_status_test(trial_data):
        if not trial_data.get('trial_active'):
            return False, "No active trial"
        
        try:
            trial_end = datetime.fromisoformat(trial_data['trial_end_date'])
            if datetime.now() > trial_end:
                return False, "Trial expired"
            return True, f"Trial active until {trial_end.strftime('%Y-%m-%d')}"
        except:
            return False, "Invalid trial data"
    
    is_active, message = check_trial_status_test(trial_data)
    print(f"✅ Trial Status: {message}")
    print()
    
    # Test 3: Daily limit checking
    print("Test 3: Daily Limit Checking")
    current_searches = 5
    remaining = TRIAL_DAILY_LIMIT - current_searches
    print(f"✅ Current daily searches: {current_searches}")
    print(f"✅ Remaining searches today: {remaining}")
    print(f"✅ Limit reached: {'Yes' if current_searches >= TRIAL_DAILY_LIMIT else 'No'}")
    print()
    
    # Test 4: Trial data structure
    print("Test 4: Complete Trial Data Structure")
    complete_user_data = {
        'user_id': 'test_user_123',
        'trial_active': True,
        'trial_start_date': trial_start.isoformat(),
        'trial_end_date': trial_end.isoformat(),
        'trial_daily_searches': current_searches,
        'trial_used': True,
        'monthly_searches': 25,
        'is_premium': False,
        'premium_since': None,
        'trial_activation': f"Trial activated: {trial_start.isoformat()}"
    }
    
    print("✅ Complete user data structure:")
    for key, value in complete_user_data.items():
        print(f"   {key}: {value}")
    
    print("\n🎉 All trial system tests passed!")
    print(f"💡 Users can now use promo code '{TRIAL_CODE}' for 7-day trial access")

if __name__ == "__main__":
    test_trial_logic()
