# CraveMap Deployment Checklist

## 🚨 BEFORE EVERY DEPLOYMENT - Run This Checklist!

### 1. **Critical Feature Testing** (Manual - 2 minutes)
- [ ] Login with email works
- [ ] Apply promo code `cravemap2024premium` - should show premium status immediately
- [ ] Apply promo code `resetfree` - should remove premium status
- [ ] Apply promo code `resetcounter` - should reset search counter to 0
- [ ] Verify premium users see "Premium user" message
- [ ] Verify free users see search limit warnings

### 2. **Automated Regression Tests** (30 seconds)
```bash
python regression_tests.py
```
**MUST PASS** - Do not deploy if any tests fail!

### 3. **Database Backup Check** (30 seconds)
```bash
python -c "from backup_manager import simple_file_backup; print('Backup:', simple_file_backup())"
```
Should create a backup file.

### 4. **Admin Panel Check** (1 minute)
- [ ] Use promo code `dbstats` - should show user statistics
- [ ] Use promo code `viewsupport` - should show support tickets
- [ ] Use promo code `backup` - should create backup file

### 5. **Core Functionality** (2 minutes)
- [ ] Search for "spicy noodles" - should return results
- [ ] Submit support ticket (premium users only)
- [ ] Verify Stripe payment flow works (test mode)

## 🔧 **If ANY Test Fails:**

1. **DO NOT DEPLOY**
2. **Fix the issue first**
3. **Re-run all tests**
4. **Only deploy when everything passes**

## 📋 **Pre-Deployment Commands**

```bash
# Run regression tests
python regression_tests.py

# Create backup
python -c "from backup_manager import simple_file_backup; simple_file_backup()"

# Check app starts without errors
streamlit run CraveMap.py &
sleep 10
curl -f http://localhost:8501 || echo "App failed to start!"
```

## 🚀 **Deployment Process**

1. ✅ **All tests pass**
2. ✅ **Manual testing complete**
3. ✅ **Backup created**
4. 🚀 **Deploy to Streamlit Cloud:**
   ```bash
   git add .
   git commit -m "Deploy: All tests passing"
   git push origin main
   ```

## 🐛 **Common Issues & Fixes**

### Promo Code Not Working
- **Issue**: Boolean conversion from SQLite integer
- **Fix**: Ensure all `user_data.get('is_premium')` uses `bool()` conversion
- **Test**: `python regression_tests.py`

### Database Lost on Streamlit Cloud
- **Issue**: Free tier doesn't guarantee file persistence
- **Fix**: Restore from backup using `BACKUP_GUIDE.md`
- **Prevention**: Daily backups in `backup_manager.py`

### Session State Not Persisting
- **Issue**: Premium status disappears after page refresh
- **Fix**: Check `load_user_data()` and boolean conversion
- **Test**: Manual login → promo code → refresh page

## 📊 **Success Metrics**

After deployment, verify:
- [ ] No error messages in Streamlit Cloud logs
- [ ] Users can successfully use promo codes
- [ ] Database operations are working
- [ ] Email notifications are sent for support tickets

---

**Remember**: It's better to delay deployment than to break user experience!

**Last Updated**: September 5, 2025
