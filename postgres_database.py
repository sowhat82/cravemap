import psycopg2
import os
from dotenv import load_dotenv
import streamlit as st
from datetime import datetime

# Load environment variables
load_dotenv()

class PostgresDatabase:
    def __init__(self):
        self.connection_string = self.get_connection_string()
        self.init_tables()
    
    def get_connection_string(self):
        """Get PostgreSQL connection string from environment or Streamlit secrets"""
        # Try environment variable first (local development)
        conn_str = os.getenv("POSTGRES_CONNECTION_STRING")
        if conn_str:
            print(f"✅ Using environment variable for PostgreSQL connection")
            return conn_str
        
        # Try Streamlit secrets (production deployment)
        try:
            # Check if we're in a Streamlit context
            if hasattr(st, 'secrets'):
                # Try the postgres section first
                if 'postgres' in st.secrets and 'connection_string' in st.secrets['postgres']:
                    conn_str = st.secrets["postgres"]["connection_string"]
                    print(f"✅ Using Streamlit postgres.connection_string")
                    return conn_str
                # Try direct POSTGRES_CONNECTION_STRING
                elif 'POSTGRES_CONNECTION_STRING' in st.secrets:
                    conn_str = st.secrets["POSTGRES_CONNECTION_STRING"]
                    print(f"✅ Using Streamlit POSTGRES_CONNECTION_STRING")
                    return conn_str
        except Exception as e:
            print(f"⚠️ Streamlit secrets not available: {e}")
        
        print(f"❌ No PostgreSQL connection string found")
        return None
    
    def get_connection(self):
        """Get database connection"""
        if not self.connection_string:
            print(f"❌ No connection string available")
            return None
            
        try:
            return psycopg2.connect(self.connection_string)
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None
    
    def init_tables(self):
        """Initialize database tables"""
        try:
            conn = self.get_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    phone VARCHAR(20),
                    is_premium BOOLEAN DEFAULT FALSE,
                    premium_expiry TIMESTAMP,
                    stripe_customer_id VARCHAR(255),
                    stripe_subscription_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add stripe columns if they don't exist (migration for existing tables)
            try:
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255)
                """)
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255)
                """)
            except Exception:
                pass  # Columns may already exist
            
            # Create support_tickets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    subject VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    status VARCHAR(50) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create sessions table for better session management
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    user_email VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Error initializing database tables: {e}")
            return False
    
    def create_user(self, email, password_hash, first_name="", last_name="", phone=""):
        """Create a new user"""
        try:
            conn = self.get_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (email, password_hash, first_name, last_name, phone, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (email, password_hash, first_name, last_name, phone, datetime.now()))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except psycopg2.IntegrityError:
            # User already exists
            return False
        except Exception as e:
            st.error(f"Error creating user: {e}")
            return False
    
    def get_user(self, email):
        """Get user by email"""
        try:
            conn = self.get_connection()
            if not conn:
                return None
                
            cursor = conn.cursor()
            cursor.execute("""
                SELECT email, password_hash, first_name, last_name, phone, is_premium, premium_expiry
                FROM users WHERE email = %s
            """, (email,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return {
                    'email': result[0],
                    'password_hash': result[1],
                    'first_name': result[2] or "",
                    'last_name': result[3] or "",
                    'phone': result[4] or "",
                    'is_premium': result[5],
                    'premium_expiry': result[6]
                }
            return None
            
        except Exception as e:
            st.error(f"Error getting user: {e}")
            return None
    
    def update_user(self, email, **kwargs):
        """Update user information"""
        try:
            conn = self.get_connection()
            if not conn:
                return False
                
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                if key in ['first_name', 'last_name', 'phone', 'is_premium', 'premium_expiry']:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            if not set_clauses:
                return False
            
            set_clauses.append("updated_at = %s")
            values.append(datetime.now())
            values.append(email)
            
            cursor = conn.cursor()
            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE email = %s"
            cursor.execute(query, values)
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Error updating user: {e}")
            return False
    
    def upgrade_to_premium(self, email, premium_expiry):
        """Upgrade user to premium"""
        return self.update_user(email, is_premium=True, premium_expiry=premium_expiry)
    
    def get_all_users(self):
        """Get all users (for admin/diagnostic purposes)"""
        try:
            conn = self.get_connection()
            if not conn:
                return []
                
            cursor = conn.cursor()
            cursor.execute("""
                SELECT email, first_name, last_name, is_premium, premium_expiry, created_at
                FROM users ORDER BY created_at DESC
            """)
            
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            users = []
            for result in results:
                users.append({
                    'email': result[0],
                    'first_name': result[1] or "",
                    'last_name': result[2] or "",
                    'is_premium': result[3],
                    'premium_expiry': result[4],
                    'created_at': result[5]
                })
            
            return users
            
        except Exception as e:
            st.error(f"Error getting all users: {e}")
            return []
    
    def create_support_ticket(self, user_email, subject, message):
        """Create a support ticket"""
        try:
            conn = self.get_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO support_tickets (user_email, subject, message)
                VALUES (%s, %s, %s)
            """, (user_email, subject, message))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Error creating support ticket: {e}")
            return False
    
    def test_connection(self):
        """Test database connection"""
        try:
            conn = self.get_connection()
            if not conn:
                return False, "Connection failed"
                
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return True, "Connection successful"
            
        except Exception as e:
            return False, f"Connection error: {e}"
    
    def get_user_count(self):
        """Get total user count"""
        try:
            conn = self.get_connection()
            if not conn:
                return 0
                
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return count
            
        except Exception as e:
            st.error(f"Error getting user count: {e}")
            return 0

# Global instance
postgres_db = None

def get_postgres_db():
    """Get PostgreSQL database instance"""
    global postgres_db
    if postgres_db is None:
        postgres_db = PostgresDatabase()
    return postgres_db
