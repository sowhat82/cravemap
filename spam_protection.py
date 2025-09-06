import sqlite3
import time
from datetime import datetime, timedelta
import hashlib
import json
from collections import defaultdict

class SpamProtection:
    """Advanced spam protection and monitoring system"""
    
    def __init__(self, db_path="cravemap.db"):
        self.db_path = db_path
        self.init_tables()
        
    def init_tables(self):
        """Initialize spam protection tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Rate limiting table (enhanced)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits_advanced (
                    fingerprint TEXT PRIMARY KEY,
                    search_count_1h INTEGER DEFAULT 0,
                    search_count_24h INTEGER DEFAULT 0,
                    last_request TEXT,
                    first_request_today TEXT,
                    is_flagged BOOLEAN DEFAULT 0,
                    flag_reason TEXT,
                    created_at TEXT
                )
            ''')
            
            # Suspicious activity log
            conn.execute('''
                CREATE TABLE IF NOT EXISTS suspicious_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT,
                    activity_type TEXT,
                    details TEXT,
                    severity TEXT,
                    timestamp TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            ''')
            
            # Blocked patterns
            conn.execute('''
                CREATE TABLE IF NOT EXISTS blocked_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT,
                    pattern_value TEXT,
                    reason TEXT,
                    created_at TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            conn.commit()
    
    def generate_fingerprint(self, ip, user_agent, additional_data=None):
        """Generate unique fingerprint for rate limiting"""
        fingerprint_data = f"{ip}:{user_agent}"
        if additional_data:
            fingerprint_data += f":{additional_data}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
    
    def check_rate_limits(self, fingerprint, ip, user_agent):
        """Enhanced rate limiting with multiple time windows"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get current limits
            row = conn.execute(
                "SELECT * FROM rate_limits_advanced WHERE fingerprint = ?",
                (fingerprint,)
            ).fetchone()
            
            if row:
                last_request = datetime.fromisoformat(row['last_request'])
                
                # Reset counters if needed
                search_1h = row['search_count_1h'] if last_request > hour_ago else 0
                search_24h = row['search_count_24h'] if last_request > day_ago else 0
                
                # Check limits
                if search_1h >= 20:  # 20 searches per hour
                    self.log_suspicious_activity(
                        fingerprint, "rate_limit_exceeded_1h", 
                        f"Exceeded hourly limit: {search_1h}", "high", ip, user_agent
                    )
                    return False, "Too many requests in the last hour. Please try again later."
                
                if search_24h >= 100:  # 100 searches per day for anonymous
                    self.log_suspicious_activity(
                        fingerprint, "rate_limit_exceeded_24h", 
                        f"Exceeded daily limit: {search_24h}", "medium", ip, user_agent
                    )
                    return False, "Daily limit exceeded. Please create an account for higher limits."
                
                # Update counters
                conn.execute('''
                    UPDATE rate_limits_advanced 
                    SET search_count_1h = ?, search_count_24h = ?, last_request = ?
                    WHERE fingerprint = ?
                ''', (search_1h + 1, search_24h + 1, now.isoformat(), fingerprint))
                
            else:
                # First request
                conn.execute('''
                    INSERT INTO rate_limits_advanced 
                    (fingerprint, search_count_1h, search_count_24h, last_request, first_request_today, created_at)
                    VALUES (?, 1, 1, ?, ?, ?)
                ''', (fingerprint, now.isoformat(), now.isoformat(), now.isoformat()))
            
            conn.commit()
            return True, None
    
    def check_spam_patterns(self, query, fingerprint, ip, user_agent):
        """Check for spam patterns in search queries"""
        suspicious_patterns = [
            # Commercial spam
            (r'(?i)(buy|sell|cheap|discount|offer|deal)', 'commercial_spam'),
            # Repetitive patterns
            (r'(.)\1{10,}', 'repetitive_chars'),  # Same char repeated 10+ times
            # URLs or emails
            (r'(?i)(http|www\.|\.com|@.*\.)', 'contains_url_email'),
            # Excessive length
            (r'.{200,}', 'excessive_length'),
            # SQL injection attempts
            (r'(?i)(union|select|drop|insert|delete|script)', 'sql_injection_attempt'),
        ]
        
        for pattern, reason in suspicious_patterns:
            import re
            if re.search(pattern, query):
                self.log_suspicious_activity(
                    fingerprint, "spam_pattern_detected", 
                    f"Pattern: {reason}, Query: {query[:100]}", "medium", ip, user_agent
                )
                
                # Block different types of spam
                if reason in ['sql_injection_attempt', 'repetitive_chars', 'commercial_spam']:
                    return False, "Invalid search query. Please try a different search."
                elif reason in ['contains_url_email', 'excessive_length']:
                    return False, "Search query contains invalid content. Please try a different search."
        
        return True, None
    
    def detect_bot_behavior(self, fingerprint, ip, user_agent):
        """Detect automated/bot behavior"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Check request patterns in last hour
            hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            
            activities = conn.execute('''
                SELECT COUNT(*) as count, MIN(timestamp) as first, MAX(timestamp) as last
                FROM suspicious_activity 
                WHERE fingerprint = ? AND timestamp > ?
            ''', (fingerprint, hour_ago)).fetchone()
            
            if activities['count'] > 10:  # More than 10 suspicious activities in an hour
                self.flag_user(fingerprint, "excessive_suspicious_activity", ip, user_agent)
                return False, "Automated behavior detected. Please contact support if you're a human user."
            
            # Check for very regular timing (bot-like)
            recent_requests = conn.execute('''
                SELECT timestamp FROM suspicious_activity 
                WHERE fingerprint = ? AND timestamp > ?
                ORDER BY timestamp DESC LIMIT 5
            ''', (fingerprint, hour_ago)).fetchall()
            
            if len(recent_requests) >= 5:
                intervals = []
                for i in range(1, len(recent_requests)):
                    t1 = datetime.fromisoformat(recent_requests[i-1]['timestamp'])
                    t2 = datetime.fromisoformat(recent_requests[i]['timestamp'])
                    intervals.append(abs((t1 - t2).total_seconds()))
                
                # If all intervals are very similar (within 2 seconds), likely bot
                if all(abs(interval - intervals[0]) < 2 for interval in intervals):
                    self.flag_user(fingerprint, "regular_timing_pattern", ip, user_agent)
                    return False, "Automated behavior detected."
        
        return True, None
    
    def log_suspicious_activity(self, fingerprint, activity_type, details, severity, ip, user_agent):
        """Log suspicious activity for monitoring"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO suspicious_activity 
                (fingerprint, activity_type, details, severity, timestamp, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fingerprint, activity_type, details, severity, 
                  datetime.now().isoformat(), ip, user_agent))
            conn.commit()
    
    def flag_user(self, fingerprint, reason, ip, user_agent):
        """Flag a user for review"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE rate_limits_advanced 
                SET is_flagged = 1, flag_reason = ?
                WHERE fingerprint = ?
            ''', (reason, fingerprint))
            
            self.log_suspicious_activity(
                fingerprint, "user_flagged", f"Reason: {reason}", "high", ip, user_agent
            )
            conn.commit()
    
    def is_flagged(self, fingerprint):
        """Check if user is flagged"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT is_flagged, flag_reason FROM rate_limits_advanced WHERE fingerprint = ?",
                (fingerprint,)
            ).fetchone()
            
            if row and row[0]:
                return True, row[1]
            return False, None
    
    def get_admin_stats(self):
        """Get spam protection statistics for admin dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Last 24 hours stats
            day_ago = (datetime.now() - timedelta(days=1)).isoformat()
            
            stats = {
                'total_requests_24h': conn.execute(
                    "SELECT COUNT(*) FROM rate_limits_advanced WHERE last_request > ?", 
                    (day_ago,)
                ).fetchone()[0],
                
                'flagged_users': conn.execute(
                    "SELECT COUNT(*) FROM rate_limits_advanced WHERE is_flagged = 1"
                ).fetchone()[0],
                
                'suspicious_activities_24h': conn.execute(
                    "SELECT COUNT(*) FROM suspicious_activity WHERE timestamp > ?", 
                    (day_ago,)
                ).fetchone()[0],
                
                'high_severity_24h': conn.execute(
                    "SELECT COUNT(*) FROM suspicious_activity WHERE timestamp > ? AND severity = 'high'", 
                    (day_ago,)
                ).fetchone()[0]
            }
            
            # Recent suspicious activities
            recent_activities = conn.execute('''
                SELECT activity_type, COUNT(*) as count 
                FROM suspicious_activity 
                WHERE timestamp > ? 
                GROUP BY activity_type 
                ORDER BY count DESC
            ''', (day_ago,)).fetchall()
            
            stats['activity_breakdown'] = [dict(row) for row in recent_activities]
            
            return stats
    
    def cleanup_old_data(self, days=30):
        """Clean up old spam protection data"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Clean old suspicious activities
            deleted = conn.execute(
                "DELETE FROM suspicious_activity WHERE timestamp < ?", 
                (cutoff,)
            ).rowcount
            
            # Reset counters for old entries
            conn.execute('''
                UPDATE rate_limits_advanced 
                SET search_count_1h = 0, search_count_24h = 0 
                WHERE last_request < ?
            ''', (cutoff,))
            
            conn.commit()
            return deleted
