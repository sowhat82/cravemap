"""
Database module for CraveMap - SQLite implementation
Handles user data, premium subscriptions, and support tickets
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from contextlib import contextmanager
import os

class CraveMapDB:
    def __init__(self, db_path="cravemap.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            # Users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT,
                    is_premium BOOLEAN DEFAULT FALSE,
                    payment_completed BOOLEAN DEFAULT FALSE,
                    stripe_customer_id TEXT,
                    monthly_searches INTEGER DEFAULT 0,
                    last_search_reset TEXT,
                    premium_since TEXT,
                    promo_activation TEXT,
                    created_at TEXT,
                    last_updated TEXT
                )
            ''')
            
            # Support tickets table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    user_email TEXT,
                    support_type TEXT,
                    subject TEXT,
                    message TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Rate limits table (for additional tracking)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id TEXT PRIMARY KEY,
                    current_count INTEGER DEFAULT 0,
                    reset_date TEXT,
                    last_request TEXT
                )
            ''')
            
            # Migration log (track data migrations)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT,
                    executed_at TEXT
                )
            ''')
            
            conn.commit()
            
        # Add new columns if they don't exist (migration for existing databases)
        try:
            with self.get_connection() as conn:
                # Check if new columns exist
                cursor = conn.execute("PRAGMA table_info(users)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'premium_since' not in columns:
                    conn.execute('ALTER TABLE users ADD COLUMN premium_since TEXT')
                    print("✅ Added premium_since column")
                
                if 'promo_activation' not in columns:
                    conn.execute('ALTER TABLE users ADD COLUMN promo_activation TEXT')
                    print("✅ Added promo_activation column")
                
                conn.commit()
        except Exception as e:
            print(f"Migration note: {e}")
    
    def migrate_json_data(self):
        """Migrate existing JSON files to database"""
        import glob
        
        migration_name = "json_to_sqlite_migration"
        
        # Check if migration already run
        with self.get_connection() as conn:
            existing = conn.execute(
                "SELECT 1 FROM migrations WHERE migration_name = ?", 
                (migration_name,)
            ).fetchone()
            
            if existing:
                print("✅ Migration already completed")
                return
        
        print("🔄 Starting JSON to SQLite migration...")
        migrated_count = 0
        
        # Migrate user data files
        for filename in glob.glob('.user_data_*.json'):
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                user_id = data.get('user_id', filename.split('_')[-1].replace('.json', ''))
                self.save_user(
                    user_id=user_id,
                    email=data.get('email', ''),
                    is_premium=data.get('is_premium', False),
                    payment_completed=data.get('payment_completed', False),
                    stripe_customer_id=data.get('stripe_customer_id'),
                    monthly_searches=data.get('monthly_searches', 0),
                    last_search_reset=data.get('last_search_reset', datetime.now().isoformat())
                )
                migrated_count += 1
                print(f"✅ Migrated user: {user_id}")
                
            except Exception as e:
                print(f"❌ Failed to migrate {filename}: {e}")
        
        # Migrate support tickets
        try:
            if os.path.exists('.support_requests.json'):
                with open('.support_requests.json', 'r') as f:
                    tickets = json.load(f)
                
                for ticket_data in tickets:
                    self.save_support_ticket(
                        user_id=ticket_data.get('user_id', ''),
                        user_email=ticket_data.get('user_email', ''),
                        support_type=ticket_data.get('support_type', ''),
                        subject=ticket_data.get('subject', ''),
                        message=ticket_data.get('message', ''),
                        created_at=ticket_data.get('timestamp', datetime.now().isoformat())
                    )
                print("✅ Migrated support tickets")
        except Exception as e:
            print(f"❌ Failed to migrate support tickets: {e}")
        
        # Record migration
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO migrations (migration_name, executed_at) VALUES (?, ?)",
                (migration_name, datetime.now().isoformat())
            )
            conn.commit()
        
        print(f"🎉 Migration completed! Migrated {migrated_count} users")
    
    def save_user(self, user_id, email='', is_premium=False, payment_completed=False, 
                  stripe_customer_id=None, monthly_searches=0, last_search_reset=None,
                  premium_since=None, promo_activation=None):
        """Save or update user data"""
        if last_search_reset is None:
            last_search_reset = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, email, is_premium, payment_completed, stripe_customer_id, 
                 monthly_searches, last_search_reset, premium_since, promo_activation,
                 created_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 
                        COALESCE((SELECT created_at FROM users WHERE user_id = ?), ?), ?)
            ''', (user_id, email, is_premium, payment_completed, stripe_customer_id,
                  monthly_searches, last_search_reset, premium_since, promo_activation,
                  user_id, datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
    
    def get_user(self, user_id):
        """Get user data by ID"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            
            if row:
                return dict(row)
            else:
                # Return default user structure
                return {
                    'user_id': user_id,
                    'email': '',
                    'is_premium': False,
                    'payment_completed': False,
                    'stripe_customer_id': None,
                    'monthly_searches': 0,
                    'last_search_reset': datetime.now().isoformat(),
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
    
    def update_search_count(self, user_id, increment=1):
        """Update user's search count"""
        user = self.get_user(user_id)
        
        # Check if we need to reset monthly count
        last_reset = datetime.fromisoformat(user['last_search_reset'])
        now = datetime.now()
        
        if last_reset.month != now.month or last_reset.year != now.year:
            # Reset monthly count
            new_count = increment
            reset_time = now.isoformat()
        else:
            new_count = user['monthly_searches'] + increment
            reset_time = user['last_search_reset']
        
        self.save_user(
            user_id=user_id,
            email=user['email'],
            is_premium=user['is_premium'],
            payment_completed=user['payment_completed'],
            stripe_customer_id=user['stripe_customer_id'],
            monthly_searches=new_count,
            last_search_reset=reset_time
        )
        
        return new_count
    
    def save_support_ticket(self, user_id, user_email, support_type, subject, message, created_at=None):
        """Save support ticket"""
        if created_at is None:
            created_at = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO support_tickets 
                (user_id, user_email, support_type, subject, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, user_email, support_type, subject, message, created_at))
            conn.commit()
    
    def get_support_tickets(self, limit=50):
        """Get recent support tickets"""
        with self.get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM support_tickets 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,)).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_all_users(self):
        """Get all users (for admin purposes)"""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]
    
    def update_subscription_status(self, user_id, is_premium, payment_completed, stripe_customer_id=None):
        """Update user's subscription status"""
        user = self.get_user(user_id)
        self.save_user(
            user_id=user_id,
            email=user['email'],
            is_premium=is_premium,
            payment_completed=payment_completed,
            stripe_customer_id=stripe_customer_id,
            monthly_searches=user['monthly_searches'],
            last_search_reset=user['last_search_reset']
        )
    
    def backup_to_json(self, backup_dir="backups"):
        """Create JSON backup of all data"""
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Backup users
        users = self.get_all_users()
        with open(f"{backup_dir}/users_backup_{timestamp}.json", 'w') as f:
            json.dump(users, f, indent=2)
        
        # Backup support tickets
        tickets = self.get_support_tickets(limit=1000)
        with open(f"{backup_dir}/support_tickets_backup_{timestamp}.json", 'w') as f:
            json.dump(tickets, f, indent=2)
        
        print(f"✅ Backup created in {backup_dir}/")
    
    def get_stats(self):
        """Get database statistics"""
        with self.get_connection() as conn:
            stats = {}
            
            # User stats
            stats['total_users'] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            stats['premium_users'] = conn.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
            stats['paid_users'] = conn.execute("SELECT COUNT(*) FROM users WHERE payment_completed = 1").fetchone()[0]
            
            # Support ticket stats
            stats['total_tickets'] = conn.execute("SELECT COUNT(*) FROM support_tickets").fetchone()[0]
            stats['open_tickets'] = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE status = 'open'").fetchone()[0]
            
            return stats

# Global database instance
db = CraveMapDB()

# Run migration on import
if __name__ == "__main__":
    print("🗄️ Initializing CraveMap database...")
    db.migrate_json_data()
    stats = db.get_stats()
    print(f"📊 Database Stats: {stats}")
else:
    # Auto-migrate when imported
    try:
        db.migrate_json_data()
    except Exception as e:
        print(f"⚠️ Auto-migration failed: {e}")
