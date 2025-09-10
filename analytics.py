# Simple analytics tracking for CraveMap
import json
from datetime import datetime
import os

def log_search_event(location, cuisine_type, user_type="anonymous"):
    """Log search events for basic analytics"""
    try:
        analytics_file = ".analytics.json"
        
        # Load existing data
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"total_searches": 0, "searches_by_date": {}, "popular_cuisines": {}}
        
        # Update analytics
        today = datetime.now().strftime("%Y-%m-%d")
        data["total_searches"] += 1
        data["searches_by_date"][today] = data["searches_by_date"].get(today, 0) + 1
        data["popular_cuisines"][cuisine_type] = data["popular_cuisines"].get(cuisine_type, 0) + 1
        
        # Save updated data
        with open(analytics_file, 'w') as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        # Don't break the app if analytics fail
        pass

def get_analytics_summary():
    """Get basic analytics for admin view"""
    try:
        with open(".analytics.json", 'r') as f:
            return json.load(f)
    except:
        return {"total_searches": 0, "searches_by_date": {}, "popular_cuisines": {}}
