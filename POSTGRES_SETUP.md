# 🚀 CraveMap PostgreSQL Setup Guide

## Overview
This guide will help you set up a free Neon PostgreSQL database for persistent data storage in CraveMap, solving the premium user status persistence issue.

## ⏱️ Estimated Time: 15-20 minutes

---

## Step 1: Create Neon PostgreSQL Database (5 minutes)

### 1.1 Sign up for Neon (Free Tier)
1. Go to **https://neon.tech**
2. Click **"Sign Up"**
3. Sign up with GitHub, Google, or email
4. Choose the **Free Plan** (includes 512 MB storage, 1 database)

### 1.2 Create Your Database
1. After signing up, you'll be taken to the dashboard
2. Click **"Create Project"**
3. Choose these settings:
   - **Project Name**: `cravemap-production`
   - **Database Name**: `neondb` (default)
   - **Region**: Choose closest to your users (e.g., US East for global)
4. Click **"Create Project"**

### 1.3 Get Connection String
1. In your project dashboard, click **"Connection Details"**
2. Copy the **Connection String** (looks like this):
   ```
   postgresql://username:password@ep-xxxx-xxxx.us-east-2.aws.neon.tech/neondb
   ```
3. **Save this string** - you'll need it in the next step!

---

## Step 2: Configure Local Environment (2 minutes)

### 2.1 Update .env File
1. Open your `.env` file in the CraveMap folder
2. Replace the placeholder connection string:
   ```env
   # Replace this line:
   POSTGRES_CONNECTION_STRING=postgresql://username:password@hostname:5432/database_name
   
   # With your actual Neon connection string:
   POSTGRES_CONNECTION_STRING=postgresql://your-actual-connection-string-here
   ```

### Example:
```env
OPENROUTER_API_KEY=sk-or-v1-your-actual-openrouter-key-here
GOOGLE_API_KEY=your-actual-google-api-key-here
ADSENSE_CLIENT_ID=ca-pub-your-actual-adsense-id

# PostgreSQL Connection String for Local Development
POSTGRES_CONNECTION_STRING=postgresql://username:password@ep-xxxx-xxxx.us-east-2.aws.neon.tech/neondb
```

---

## Step 3: Test Local Setup (5 minutes)

### 3.1 Run Local Tests
```powershell
# Test PostgreSQL connection and features
python test_postgres.py
```

**Expected Output:**
```
🚀 CraveMap PostgreSQL Local Testing

🔗 Testing PostgreSQL Connection...
✅ Connection successful

👤 Testing User Operations...
📝 Creating test user: test_user@example.com
✅ User created successfully
🔍 Retrieving user: test_user@example.com
✅ User retrieved successfully
🌟 Testing premium upgrade for: test_user@example.com
✅ Premium upgrade successful
✅ Premium status verified

🔄 Testing Persistence (Simulating App Restart)...
📱 First 'session' - Creating premium user...
✅ claris_tan@hotmail.com upgraded to premium
🔄 Simulating app restart (new database connection)...
✅ User data persisted after 'restart'
🎉 PERSISTENCE TEST PASSED - Premium status maintained!

📊 TEST SUMMARY
✅ Connection Test: PASSED
✅ User Operations: PASSED
✅ Persistence Test: PASSED

🎉 ALL TESTS PASSED! PostgreSQL integration is working correctly.
```

### 3.2 Test with CraveMap Application
```powershell
# Run the main application
streamlit run CraveMap.py
```

**Test Steps:**
1. Go to **http://localhost:8501**
2. Login with `claris_tan@hotmail.com`
3. Use promo code: `cravemap2024premium`
4. Verify premium status is activated
5. **Stop the app** (Ctrl+C)
6. **Restart the app** (`streamlit run CraveMap.py`)
7. Login again with `claris_tan@hotmail.com`
8. **Verify premium status is still active** ✅

---

## Step 4: Migrate Existing Data (3 minutes)

### 4.1 Run Migration Script
```powershell
# Migrate existing SQLite data to PostgreSQL
python migrate_database.py migrate
```

**Expected Output:**
```
🚀 CraveMap Database Migration Tool

Starting migration from SQLite to PostgreSQL...
✅ PostgreSQL connection successful
✅ SQLite database found at cravemap.db
📊 Found 5 users in SQLite database
✅ Migrated PREMIUM user: claris_tan@hotmail.com
✅ Migrated user: other_user@example.com
...

📊 Migration Summary:
   Total users: 5
   ✅ Successfully migrated: 5
   ❌ Failed to migrate: 0

🔍 Verifying migration...
📊 PostgreSQL user count: 5
```

### 4.2 Test Specific User
```powershell
# Test that claris_tan@hotmail.com migrated correctly
python migrate_database.py test claris_tan@hotmail.com
```

---

## Step 5: Deploy to Production (5 minutes)

### 5.1 Add Secrets to Streamlit Cloud
1. Go to **https://share.streamlit.io**
2. Find your CraveMap app
3. Click **"Settings"** (gear icon)
4. Go to **"Secrets"**
5. Add this configuration:
   ```toml
   [postgres]
   connection_string = "postgresql://your-actual-connection-string-here"
   ```

### 5.2 Deploy Updated Code
```powershell
# Commit and push changes
git add .
git commit -m "Add PostgreSQL persistent storage support"
git push origin main
```

### 5.3 Test Production Deployment
1. Wait for Streamlit Cloud to redeploy (2-3 minutes)
2. Go to your production URL
3. Login with `claris_tan@hotmail.com`
4. Verify premium status
5. **Test persistence**: Restart the app by making a small change and pushing again

---

## ✅ Verification Checklist

- [ ] Neon PostgreSQL database created
- [ ] Connection string configured in `.env`
- [ ] Local tests all pass
- [ ] Premium upgrade works locally
- [ ] Premium status persists after local app restart
- [ ] Existing data migrated successfully
- [ ] Streamlit Cloud secrets configured
- [ ] Production deployment successful
- [ ] Premium status persists in production after restart

---

## 🚨 Troubleshooting

### Common Issues:

**1. Connection String Error:**
```
❌ PostgreSQL connection failed: connection failed
```
**Solution:** Double-check your connection string in `.env` file

**2. Permission Denied:**
```
❌ PostgreSQL connection failed: permission denied
```
**Solution:** Verify the username/password in your connection string

**3. Module Not Found:**
```
❌ ModuleNotFoundError: No module named 'psycopg2'
```
**Solution:** Run `pip install psycopg2-binary`

**4. Streamlit Secrets Error:**
```
❌ PostgreSQL initialization failed: 'postgres'
```
**Solution:** Make sure Streamlit Cloud secrets are configured correctly

---

## 📞 Need Help?

If you encounter any issues:
1. Check the error messages carefully
2. Verify your connection string format
3. Make sure Neon database is running (it auto-sleeps after inactivity)
4. Test locally first before deploying to production

---

## 🎉 Success!

Once all tests pass, your CraveMap application will have:
- ✅ Persistent user data storage
- ✅ Premium status that survives app restarts
- ✅ Reliable cloud database backup
- ✅ Scalable infrastructure for growth

**claris_tan@hotmail.com will never lose premium status again!** 🚀
