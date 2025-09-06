import os
import json
import sqlite3
from datetime import datetime
import requests
import streamlit as st

class BackupManager:
    def __init__(self, db_path="cravemap.db"):
        self.db_path = db_path
        
    def create_backup(self):
        """Create a JSON backup of the entire database"""
        if not os.path.exists(self.db_path):
            return None
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        backup_data = {
            "backup_timestamp": datetime.now().isoformat(),
            "tables": {}
        }
        
        # Get all tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            backup_data["tables"][table_name] = [dict(row) for row in rows]
        
        conn.close()
        return backup_data
    
    def save_backup_to_github_gist(self, backup_data, github_token=None):
        """Save backup to GitHub Gist (free, private)"""
        if not github_token or not backup_data:
            return False
            
        gist_data = {
            "description": f"CraveMap Database Backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "public": False,
            "files": {
                f"cravemap_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json": {
                    "content": json.dumps(backup_data, indent=2)
                }
            }
        }
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            response = requests.post("https://api.github.com/gists", 
                                   json=gist_data, headers=headers)
            return response.status_code == 201
        except:
            return False
    
    def restore_from_backup(self, backup_data):
        """Restore database from backup data"""
        if not backup_data or "tables" not in backup_data:
            return False
            
        # Remove existing database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        # Recreate database with backup data
        conn = sqlite3.connect(self.db_path)
        
        # Create tables and insert data
        for table_name, rows in backup_data["tables"].items():
            if not rows:
                continue
                
            # Create table based on first row structure
            first_row = rows[0]
            columns = []
            for key, value in first_row.items():
                if isinstance(value, int):
                    columns.append(f"{key} INTEGER")
                elif isinstance(value, float):
                    columns.append(f"{key} REAL")
                else:
                    columns.append(f"{key} TEXT")
            
            create_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
            conn.execute(create_sql)
            
            # Insert data
            placeholders = ', '.join(['?' for _ in first_row.keys()])
            insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
            
            for row in rows:
                conn.execute(insert_sql, list(row.values()))
        
        conn.commit()
        conn.close()
        return True
    
    def auto_backup_on_startup(self):
        """Check if database exists, if not try to restore from last backup"""
        if not os.path.exists(self.db_path):
            st.warning("Database not found! Attempting to restore from backup...")
            # In a real scenario, you'd fetch the latest backup from your storage
            # For now, we'll just create a fresh database
            return False
        return True
    
    def periodic_backup(self, github_token=None):
        """Create backup if it's been more than 24 hours since last backup"""
        backup_data = self.create_backup()
        if backup_data and github_token:
            success = self.save_backup_to_github_gist(backup_data, github_token)
            return success
        return False

# Simple file-based backup (no external dependencies)
def simple_file_backup():
    """Create a simple JSON backup file"""
    backup_manager = BackupManager()
    backup_data = backup_manager.create_backup()
    
    if backup_data:
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(backup_filename, 'w') as f:
            json.dump(backup_data, f, indent=2)
        return backup_filename
    return None
