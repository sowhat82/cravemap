## ChatGPT Agent Production Testing Prompt for CraveMap

**CRITICAL SAFETY RULES - READ FIRST:**
- NEVER submit the contact support form (it sends real emails)
- NEVER make real payments or enter real payment info
- ONLY use the provided promo codes for testing
- ONLY test free features and promo code upgrades
- If you see any payment forms, STOP immediately

**YOUR MISSION:**
Test my CraveMap app in production to verify non-payment features work correctly. The app is at: [YOUR_PRODUCTION_URL_HERE]

**WHAT TO TEST:**

### 1. Basic App Functionality
- [ ] App loads without errors
- [ ] Main interface displays properly
- [ ] Search form is visible and functional
- [ ] No debug elements visible (should be clean production UI)

### 2. Free Tier Rate Limiting
- [ ] Try 3 searches as a free user
- [ ] Verify 4th search is blocked with appropriate message
- [ ] Confirm rate limit message is user-friendly

### 3. Promo Code Testing (SAFE - NO PAYMENTS)
Test these promo codes in the "Have a promo code?" section:

**A. Premium Upgrade Test:**
- [ ] Enter promo code: `cravemap2024premium`
- [ ] Verify you get premium access
- [ ] Confirm unlimited searches work
- [ ] Check that "Contact Support" section appears
- [ ] DO NOT submit the contact form (just verify it's visible)

**B. Admin Code Test:**
- [ ] Enter promo code: `viewsupport` 
- [ ] Verify you can see support ticket history (if any)
- [ ] Check this admin feature works properly

**C. Reset Testing:**
- [ ] Use promo code: `resetfree` to downgrade
- [ ] Verify you're back to free tier (3 search limit)
- [ ] Use promo code: `resetcounter` to reset search count
- [ ] Verify search counter resets to 0

### 4. UI/UX Testing
- [ ] Check all navigation works smoothly
- [ ] Verify responsive design on different screen sizes
- [ ] Test that premium-only features are properly gated
- [ ] Confirm no sensitive information is exposed (API keys, emails, etc.)

### 5. Error Handling
- [ ] Test invalid promo codes (should show error)
- [ ] Test empty search submissions
- [ ] Verify error messages are user-friendly

**WHAT NOT TO TEST:**
❌ DO NOT test payment flows
❌ DO NOT submit contact support forms  
❌ DO NOT enter real payment information
❌ DO NOT stress test with excessive requests
❌ DO NOT test with fake/invalid data that could corrupt the database

**REPORTING:**
Please provide a detailed report covering:
1. ✅ What worked correctly
2. ❌ Any bugs or issues found
3. 💡 UX improvements suggestions
4. 🔒 Any security concerns noticed
5. 📊 Overall app performance and responsiveness

**EXAMPLE TESTING FLOW:**
1. Load app → Verify clean UI
2. Try 4 searches → Confirm rate limiting works
3. Use `cravemap2024premium` → Verify premium upgrade
4. Test unlimited searches → Confirm no limits
5. Use `resetfree` → Verify downgrade to free
6. Use `resetcounter` → Verify counter resets
7. Use `viewsupport` → Check admin features

**SUCCESS CRITERIA:**
- App loads and functions smoothly
- Rate limiting works correctly
- All promo codes function as expected
- No errors or crashes during testing
- UI is clean and professional (no debug elements)
- Premium features are properly gated

Remember: This is a PRODUCTION environment with real users. Be respectful, test efficiently, and report any issues you find. Focus on user experience and functionality, not stress testing or security penetration.

**EMERGENCY STOP CONDITIONS:**
If you encounter any of these, STOP testing immediately:
- Payment forms that aren't bypassed by promo codes
- Requests for real payment information
- Error messages indicating system problems
- Any indication you're affecting real user data

Thank you for helping ensure CraveMap works perfectly for real users! 🚀
