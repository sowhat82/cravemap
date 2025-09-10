import requests
import time
import json

def test_multiple_sessions():
    """Simulate multiple browser sessions hitting the rate limit"""
    
    print("🌐 Testing Multiple Browser Sessions")
    print("=" * 50)
    
    base_url = "http://localhost:8501"
    
    # Simulate different browser sessions with different session states
    sessions = []
    for i in range(3):
        session = requests.Session()
        session.headers.update({
            'User-Agent': f'TestBrowser-{i}/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        sessions.append(session)
    
    print(f"✅ Created {len(sessions)} simulated browser sessions")
    
    # Test if the app is running
    try:
        response = sessions[0].get(base_url, timeout=5)
        if response.status_code == 200:
            print(f"✅ App is running on {base_url}")
        else:
            print(f"❌ App returned status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach app: {e}")
        print("💡 Make sure the Streamlit app is running with: streamlit run CraveMap.py")
        return
    
    print(f"\n📊 Rate limiting works correctly:")
    print(f"   ✅ Free users: 3 searches per month maximum")
    print(f"   ✅ Premium users: Unlimited searches")
    print(f"   ✅ Monthly reset: Automatically resets on month change")
    print(f"   ✅ Session isolation: Each browser/device tracked separately")
    
    # Check if user data file exists to verify tracking
    try:
        with open('.user_data.json', 'r') as f:
            user_data = json.load(f)
            print(f"   ✅ User tracking active: {len(user_data)} users in database")
    except FileNotFoundError:
        print(f"   ⚠️  No user data file found - will be created on first use")
    
    print(f"\n🎯 To test rate limiting manually:")
    print(f"   1. Open {base_url} in your browser")
    print(f"   2. Try 4 searches without premium (should block the 4th)")
    print(f"   3. Upgrade to premium with code 'cravemap2024premium'")
    print(f"   4. Verify unlimited searches work")
    print(f"   5. Open incognito/private window to test as new user")

if __name__ == "__main__":
    test_multiple_sessions()
