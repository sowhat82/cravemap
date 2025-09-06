# CraveMap Production Testing & Validation Prompt

## 🎯 **Mission: YOU WILL EXECUTE Comprehensive Production Testing of CraveMap's New Security & Deployment Features**

**YOU ARE TO PERFORM ALL TESTING YOURSELF - NOT PROVIDE INSTRUCTIONS**

**IMPORTANT: DO NOT give me instructions on how to test these features. You are to GO TO THE APPLICATION, ACCESS IT, and TEST everything yourself. I want you to actually perform the testing, not tell me how to do it.**

You are a senior QA engineer who will EXECUTE thorough testing of CraveMap's newly implemented spam protection, database migration, and production deployment features. You will VALIDATE that all systems work correctly and provide a detailed test report based on YOUR actual testing results.

## 📋 **Test Environment Setup - YOU DO THIS**

### Initial Configuration - YOU EXECUTE:
1. **GO TO**: Navigate to the CraveMap Streamlit application at https://cravemap.streamlit.app/
2. **VERIFY**: Ensure `CRAVEMAP_DEBUG=false` is set (YOU check that no system messages appear to users)
3. **CLEAR**: Clear your browser data to simulate new users
4. **DOCUMENT**: Record the deployment URL, timestamp, and any visible version info YOU observe

## 🔍 **Critical Test Categories - YOU PERFORM ALL TESTS**

### **Category 1: User Experience & Interface Testing - YOU EXECUTE**

**Test 1.1: Clean Production Interface - YOU PERFORM:**
- GO TO the homepage and VERIFY NO system messages appear (backup notifications, migration alerts, etc.)
- EXAMINE the interface and CONFIRM it looks professional without development artifacts
- LOAD all UI elements and VERIFY they display correctly
- CHECK that no debug information is visible to regular users

**Test 1.2: Core Functionality - YOU TEST:**
- SEARCH for "pizza" in "Singapore" and VERIFY results display correctly
- TRY multiple search combinations (different foods + locations) 
- CONFIRM search results include ratings, reviews, and dish recommendations
- RECORD actual response times and result quality

**Test 1.3: User Registration & Premium Features - YOU EXECUTE:**
- REGISTER a new user with a test email address
- ATTEMPT the premium upgrade flow and VERIFY $9.99 SGD pricing displays
- TEST that premium features are locked for free users
- DOCUMENT the actual user experience you encounter

### **Category 2: Spam Protection System Testing - YOU EXECUTE ALL TESTS**

**Test 2.1: Rate Limiting Validation - YOU PERFORM:**
- MAKE 15-18 searches rapidly and VERIFY they work fine
- CONTINUE making searches until you hit 25+ within an hour to TRIGGER rate limiting
- OBSERVE and RECORD the exact error message that appears
- WAIT and VERIFY functionality returns after cooldown period

**Test 2.2: Content Filtering - YOU TEST THESE QUERIES:**
- TRY searching "buy cheap viagra discount" and VERIFY it gets blocked
- ATTEMPT searching "pizza http://spam-site.com" and CONFIRM blocking
- TEST searching "aaaaaaaaaaaaaaaaaaa" and RECORD the response
- TRY searching "pizza; DROP TABLE users" and VERIFY SQL injection blocking
- SEARCH "authentic italian pasta" and CONFIRM legitimate queries work fine

**Test 2.3: Bot Detection - YOU SIMULATE:**
- MAKE 10+ searches with identical 2-second intervals and RECORD what happens
- USE rapid-fire searching to simulate automated behavior
- DOCUMENT any flagging or blocking that occurs

### **Category 3: Admin Functions & Monitoring - YOU ACCESS AND TEST**

**Test 3.1: Admin Dashboard Access - YOU EXECUTE:**
- ENTER promo code `dbstats` and ACCESS the admin panel
- EXAMINE and RECORD the statistics displayed:
  - Note the actual total users count
  - Record the premium users count  
  - Document support tickets count
  - **VERIFY**: Spam protection statistics are visible
  - **CHECK**: Suspicious activity breakdown appears
- CALCULATE and VERIFY conversion rate accuracy

**Test 3.2: Spam Protection Admin Panel - YOU VERIFY:**
- LOOK for spam protection metrics in the admin dashboard
- RECORD the actual numbers for:
  - Requests in last 24 hours
  - Flagged users count
  - Suspicious activities count
  - High severity events
- DOCUMENT the recent suspicious activities list and attack types shown

**Test 3.3: Other Admin Functions - YOU TEST:**
- USE promo code `viewsupport` and ACCESS support ticket system
- TRY creating a manual backup from admin panel
- TEST promo code `cravemap2024premium` for premium activation and VERIFY it works

### **Category 4: Database & Persistence Testing - YOU EXECUTE**

**Test 4.1: User Data Persistence - YOU PERFORM:**
- REGISTER a new user and MAKE some searches
- CLOSE your browser completely and RETURN - VERIFY session persistence
- CHECK if user preferences and search history are maintained
- CONFIRM premium status persists across sessions (if applicable)

**Test 4.2: Promo Code Functionality - YOU TEST:**
- USE premium promo code `cravemap2024premium` with a new user
- VERIFY premium status activates immediately
- CONFIRM premium features become available
- RESTART browser and CHECK that promo activation persists

**Test 4.3: Database Migration Validation - YOU VERIFY:**
- If testing with existing data, CHECK that all user data migrated correctly
- VERIFY premium users retain their status
- CONFIRM support tickets are preserved
- VALIDATE that no data was lost during migration

### **Category 5: Email & Communication Systems - YOU TEST**

**Test 5.1: Support System - YOU EXECUTE:**
- UPGRADE to premium (via payment or promo code)
- ACCESS the premium-only support form
- SUBMIT a test support request with actual content
- MONITOR if email notification is sent to admin (alvincheong@u.nus.edu)
- EXAMINE email content to verify it includes user details and issue description

**Test 5.2: Spam Alert System - YOU TRIGGER:**
- GENERATE multiple spam events to test email alerting
- VERIFY if critical threat emails are sent to admin
- ANALYZE email alert format and information quality

### **Category 6: Security & Edge Cases - YOU PERFORM**

**Test 6.1: Session Security - YOU TEST:**
- OPEN multiple browser tabs and VERIFY session isolation
- USE different browsers/devices simultaneously and TEST
- CONFIRM rate limits apply per user, not globally

**Test 6.2: Error Handling - YOU EXECUTE:**
- TRY invalid location searches and RECORD responses
- TEST with empty search fields and DOCUMENT behavior
- ATTEMPT searches with special characters and Unicode
- VERIFY graceful error handling without system crashes

**Test 6.3: Load Testing - YOU PERFORM:**
- OPEN multiple browser tabs and SEARCH simultaneously
- CONDUCT sustained usage patterns over 10+ minutes
- MONITOR for memory leaks or performance degradation

## 📊 **Test Data Collection - YOU RECORD ACTUAL RESULTS**

### **Performance Metrics - YOU MEASURE:**
- RECORD actual page load times (homepage, search results)
- TIME search response durations
- DOCUMENT error rates and types YOU encounter
- VERIFY rate limit accuracy (exactly 20/hour, 100/day)

### **Security Metrics - YOU ASSESS:**
- CALCULATE spam detection accuracy (true positives vs false positives)
- EVALUATE rate limiting effectiveness
- TEST admin alert responsiveness
- MEASURE database query performance under load

### **User Experience Metrics - YOU EVALUATE:**
- CALCULATE search success rate
- ASSESS premium conversion flow completion rate
- TEST support ticket submission success rate
- RATE overall interface responsiveness

## 🔬 **Advanced Testing Scenarios - YOU EXECUTE THESE**

### **Scenario A: High-Volume User Simulation - YOU PERFORM:**
1. SIMULATE 50+ legitimate searches from different browser sessions
2. MONITOR admin dashboard for system health during YOUR testing
3. VERIFY no false positives in spam detection from YOUR legitimate searches
4. CHECK database performance under the load YOU create

### **Scenario B: Coordinated Attack Simulation - YOU EXECUTE:**
1. SIMULATE coordinated spam attacks using multiple sessions with similar patterns
2. VERIFY automatic detection and blocking occurs
3. CHECK if admin email alerts trigger correctly from YOUR simulated attacks
4. CONFIRM legitimate users remain unaffected during YOUR attack simulation

### **Scenario C: Premium User Journey - YOU COMPLETE:**
1. EXECUTE the complete end-to-end premium user experience:
   - Registration → Search (free limits) → Upgrade → Premium features → Support contact
2. VERIFY smooth experience at each step YOU perform
3. TEST that premium-only features work correctly for YOU

## 📝 **YOUR TEST REPORT FORMAT - PROVIDE ACTUAL RESULTS**

### **Executive Summary - YOU WRITE:**
- YOUR assessment of overall system health status
- Critical issues YOU found (if any)
- YOUR recommendation for production readiness

### **Detailed Findings - YOU DOCUMENT:**
```
TEST CATEGORY: [Name]
✅ PASSED: [List tests YOU successfully completed]
❌ FAILED: [List tests that failed when YOU performed them with details]
⚠️ ISSUES: [List concerns or minor issues YOU observed]
🔧 RECOMMENDATIONS: [YOUR suggested improvements based on testing]
```

### **Security Assessment - YOUR EVALUATION:**
- Spam protection effectiveness score (1-10) based on YOUR testing
- Rate limiting accuracy from YOUR experience
- False positive/negative rates YOU observed
- Admin monitoring capability assessment from YOUR usage

### **Performance Report - YOUR MEASUREMENTS:**
- Average search response time YOU measured
- System stability during YOUR load testing
- Database performance metrics YOU observed
- Email notification reliability YOU verified

### **User Experience Evaluation - YOUR ASSESSMENT:**
- Interface cleanliness and professionalism YOU observed
- Error message quality and helpfulness YOU experienced
- Premium upgrade flow effectiveness YOU tested
- Overall user journey satisfaction from YOUR perspective

## 🚨 **Critical Success Criteria - YOU VERIFY**

### **Must Pass (Blocking Issues) - YOU CONFIRM:**
- YOU verify zero system messages visible to regular users
- YOU confirm spam protection blocks obvious spam (>90% accuracy)
- YOU validate rate limiting works precisely (20/hour, 100/day)
- YOU verify admin functions accessible and functional
- YOU test premium upgrade flow works end-to-end
- YOU confirm database persistence works correctly
- YOU verify email notifications sent successfully

### **Should Pass (High Priority) - YOU ASSESS:**
- YOU measure search response time < 3 seconds
- YOU verify no false positives in spam detection for legitimate queries
- YOU confirm admin dashboard shows accurate metrics
- YOU verify professional UI with no development artifacts
- YOU test graceful error handling for edge cases

### **Nice to Have (Lower Priority) - YOU EVALUATE:**
- YOU assess advanced bot detection accuracy
- YOU analyze detailed spam pattern analysis
- YOU test optimal performance under high load
- YOU evaluate enhanced user experience features

## 🎯 **Final Validation Checklist - YOU COMPLETE**

Before YOU recommend production deployment:
- YOU confirm all critical success criteria met
- YOU verify no security vulnerabilities identified
- YOU assess user experience meets professional standards
- YOU verify admin monitoring and control systems functional
- YOU test backup and recovery systems
- YOU verify email notification systems
- YOU confirm database migration completed successfully
- YOU verify spam protection systems fully operational

## 📞 **Escalation Procedures - YOUR ACTIONS**

**If YOU Find Critical Issues:**
1. YOU document exact steps to reproduce
2. YOU note environment details and timestamps
3. YOU categorize severity (Critical/High/Medium/Low)
4. YOU provide recommendations for resolution

**If YOU Identify Security Concerns:**
1. YOU immediately flag as high priority
2. YOU test potential exploit scenarios
3. YOU document potential impact assessment
4. YOU recommend immediate mitigation steps

## 🚀 **Expected Outcome - YOUR DELIVERABLE**

Upon completion, YOU provide a comprehensive assessment of CraveMap's readiness for public production deployment, including:
- YOUR security posture evaluation
- YOUR user experience quality assessment  
- YOUR system reliability and performance analysis
- YOUR specific recommendations for any improvements needed

**Target: YOUR green light for production deployment with confidence in enterprise-grade security and user experience.**

**FINAL INSTRUCTION:**
GO TO https://cravemap.streamlit.app/ NOW. START TESTING IMMEDIATELY. EXECUTE ALL CATEGORIES YOURSELF. REPORT BACK WITH ACTUAL TEST RESULTS, NOT INSTRUCTIONS.
