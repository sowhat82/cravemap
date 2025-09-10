import time
from spam_protection import SpamProtection
from spam_monitoring import SpamMonitoringSystem
import os
import tempfile

def test_spam_protection():
    """Test spam protection functionality"""
    # Use temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        spam_protection = SpamProtection(db_path)
        
        # Test 1: Normal usage should work
        fingerprint = spam_protection.generate_fingerprint("192.168.1.1", "Mozilla/5.0")
        
        # Should allow normal requests
        for i in range(5):
            result, msg = spam_protection.check_rate_limits(fingerprint, "192.168.1.1", "Mozilla/5.0")
            assert result == True, f"Normal request {i+1} should be allowed"
        
        print("✅ Test 1 passed: Normal usage works")
        
        # Test 2: Rate limiting should kick in
        # Simulate rapid requests to trigger hourly limit
        for i in range(16):  # Total will be 21 (5 + 16)
            spam_protection.check_rate_limits(fingerprint, "192.168.1.1", "Mozilla/5.0")
        
        # This should be blocked (22nd request)
        result, msg = spam_protection.check_rate_limits(fingerprint, "192.168.1.1", "Mozilla/5.0")
        assert result == False, "Rate limit should block excessive requests"
        assert "hour" in msg.lower(), "Error message should mention hourly limit"
        
        print("✅ Test 2 passed: Rate limiting works")
        
        # Test 3: Spam pattern detection
        test_patterns = [
            ("buy cheap viagra now!!!", False),  # Commercial spam
            ("aaaaaaaaaaaaaaaaaaa", False),      # Repetitive chars
            ("normal pizza search", True),       # Normal query
            ("http://spam-site.com", False),     # URL spam
            ("SELECT * FROM users", False),      # SQL injection
        ]
        
        for query, should_pass in test_patterns:
            result, msg = spam_protection.check_spam_patterns(query, fingerprint, "192.168.1.1", "Mozilla/5.0")
            if should_pass:
                assert result == True, f"Query '{query}' should be allowed"
            else:
                assert result == False, f"Query '{query}' should be blocked"
        
        print("✅ Test 3 passed: Spam pattern detection works")
        
        # Test 4: Admin statistics
        stats = spam_protection.get_admin_stats()
        assert 'total_requests_24h' in stats
        assert 'flagged_users' in stats
        assert 'suspicious_activities_24h' in stats
        
        print("✅ Test 4 passed: Admin statistics work")
        
        print("\n🎉 All spam protection tests passed!")
        
        # Properly close database connections
        del spam_protection
        
    finally:
        # Clean up temporary database
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except PermissionError:
            print(f"⚠️ Could not delete temp file {db_path} - it will be cleaned up later")

def test_monitoring_system():
    """Test monitoring and alerting system"""
    # Use temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create spam protection with test data
        spam_protection = SpamProtection(db_path)
        
        # Generate some test suspicious activities
        fingerprint = spam_protection.generate_fingerprint("test", "test")
        
        # Create high-severity activities
        for i in range(12):  # Above threshold of 10
            spam_protection.log_suspicious_activity(
                fingerprint, "rate_limit_exceeded_1h", "Test high severity", "high", "test", "test"
            )
        
        # Test monitoring system
        monitor = SpamMonitoringSystem()
        monitor.spam_protection = spam_protection  # Use our test instance
        
        # Check threat detection
        threats = monitor.check_for_threats()
        assert len(threats) > 0, "Should detect threats from test data"
        
        # Check risk calculation
        stats = spam_protection.get_admin_stats()
        risk_level = monitor.calculate_risk_level(stats)
        assert risk_level in ["LOW", "MEDIUM", "HIGH"], "Risk level should be valid"
        
        # Test daily report generation
        report = monitor.generate_daily_report()
        assert 'summary' in report
        assert 'risk_level' in report
        
        print("✅ Monitoring system tests passed!")
        
        # Properly close database connections
        del monitor
        del spam_protection
        
    finally:
        # Clean up
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except PermissionError:
            print(f"⚠️ Could not delete temp file {db_path} - it will be cleaned up later")

def manual_test_integration():
    """Manual test to verify integration with main app"""
    print("\n🔧 Manual Integration Test")
    print("1. Start your CraveMap app")
    print("2. Try making 25+ searches rapidly (should be rate limited)")
    print("3. Try searching for 'buy cheap viagra' (should be blocked)")
    print("4. Use promo code 'dbstats' to see spam protection stats")
    print("5. Check that suspicious activities are logged")

if __name__ == "__main__":
    print("🧪 Testing CraveMap Spam Protection System\n")
    
    print("Running automated tests...")
    test_spam_protection()
    test_monitoring_system()
    
    print("\n" + "="*50)
    manual_test_integration()
    
    print(f"\n✅ All tests completed! System ready for production.")
    print("\n📋 Next steps:")
    print("1. Deploy with spam protection enabled")
    print("2. Monitor admin dashboard regularly")
    print("3. Review SPAM_PREVENTION_GUIDE.md for ongoing maintenance")
