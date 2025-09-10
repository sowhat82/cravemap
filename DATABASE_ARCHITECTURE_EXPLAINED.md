# 🗄️ CraveMap Database Architecture Explained

## **📍 Where is the Database Stored?**

### **Local Development**
- **File**: `cravemap.db` (SQLite file)
- **Location**: Same directory as your app (`c:\Users\alvin\OneDrive\Code\GPT Agents\CraveMap\`)
- **Type**: SQLite database (single file)

### **When Deployed to Streamlit Cloud**
- **File**: `cravemap.db` (SQLite file) 
- **Location**: Streamlit Cloud server filesystem
- **Type**: Still SQLite, but running on cloud infrastructure
- **Persistence**: Files persist between app restarts on Streamlit Cloud

## **🏗️ Database Architecture**

### **Current Implementation: SQLite + Wrapper Functions**
```
Your App Structure:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CraveMap.py   │────│   database.py    │────│  cravemap.db    │
│                 │    │                  │    │                 │
│ load_user_data()│────│ CraveMapDB class │────│ SQLite Database │
│ save_user_data()│    │ - get_user()     │    │ - users table   │
│                 │    │ - save_user()    │    │ - support_tckts │
│                 │    │ - get_stats()    │    │ - rate_limits   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **Database Tables**
```sql
users:
- user_id (PRIMARY KEY, email hash)
- email 
- is_premium (boolean)
- payment_completed (boolean)
- monthly_searches (integer)
- premium_since (datetime)
- trial_active (boolean) 
- trial_start_date, trial_end_date
- trial_used (boolean - prevents re-activation)

support_tickets:
- id, user_id, user_email, subject, message, status

rate_limits:
- user_id, current_count, reset_date, last_request
```

## **💾 How Data Persistence Works**

### **CRUD Operations**
```python
# CREATE/UPDATE
save_user_data(user_id, {
    'email': 'user@example.com',
    'is_premium': True,
    'trial_active': True,
    'trial_used': True
})

# READ
user_data = load_user_data(user_id)
# Returns: {'email': '...', 'is_premium': True, ...}

# UPDATE (increment search count)
db.update_search_count(user_id, 1)

# READ (get stats)
stats = db.get_stats()
# Returns: {'total_users': 150, 'premium_users': 12, ...}
```

### **Data Flow Example: Trial Activation**
```
1. User enters "trial7days" → CraveMap.py
2. CraveMap calls save_user_data() → database.py
3. database.py executes SQL INSERT/UPDATE → cravemap.db
4. SQLite writes to disk → Data persisted
5. Future app loads read from cravemap.db → Data retrieved
```

## **☁️ Cloud Deployment Reality**

### **When You Deploy to Streamlit Cloud:**
1. **Your code** (CraveMap.py, database.py) runs on Streamlit's servers
2. **SQLite file** (cravemap.db) is created on the server filesystem
3. **Data persists** between app restarts (Streamlit Cloud preserves files)
4. **All users** connect to the same database instance

### **It's NOT a separate cloud database service like:**
- ❌ AWS RDS
- ❌ Google Cloud SQL  
- ❌ MongoDB Atlas
- ❌ Firebase

### **It IS:**
- ✅ SQLite file running on Streamlit Cloud servers
- ✅ Single file database with your app
- ✅ Automatic backups via your backup system
- ✅ Fast local file I/O (same server)

## **🔄 How Users Share the Same Database**

### **Multi-User Architecture**
```
User A (Browser) ──┐
                   │
User B (Browser) ──┼──→ Streamlit Cloud Server
                   │    ├── CraveMap.py (app code)
User C (Browser) ──┘    ├── database.py (DB wrapper)
                        └── cravemap.db (shared SQLite file)
```

### **Concurrent Access**
- ✅ SQLite handles multiple concurrent reads
- ✅ Database locks prevent data corruption
- ✅ Each user gets their own session state
- ✅ User data separated by unique user_id (email hash)

## **📈 Advantages of Current Setup**

### **Pros:**
- ✅ **Simple**: No external database setup needed
- ✅ **Fast**: Local file I/O is very quick
- ✅ **Free**: No database hosting costs
- ✅ **Backup-friendly**: Single file to backup
- ✅ **Development**: Easy to test locally

### **Cons:**
- ❌ **Scalability**: Limited to single server
- ❌ **High availability**: No automatic failover
- ❌ **Geographic distribution**: Single location only

## **🚀 Current Status: Perfect for Your Stage**

For a food discovery app with trial system:
- ✅ **Handles hundreds of users easily**
- ✅ **Reliable data persistence**  
- ✅ **Fast user experience**
- ✅ **Simple maintenance**
- ✅ **Cost effective**

**Your database IS on a live cloud server (Streamlit Cloud) and handles full CRUD operations for all users sharing the same SQLite file.** 🎯

---

*When you need to scale beyond thousands of users, you can migrate to PostgreSQL/MySQL, but SQLite on Streamlit Cloud is perfect for your current needs.*
