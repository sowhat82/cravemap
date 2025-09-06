# CraveMap Database Backup & Recovery Guide

## 🎯 The Cheapest Solution - File Backups

Your CraveMap app now automatically backs up your database to protect against Streamlit Cloud data loss.

## How It Works

### Automatic Backups
- **Daily**: App creates a backup every 24 hours automatically
- **On Startup**: Creates initial backup if none exists
- **File Format**: JSON files named `backup_YYYYMMDD_HHMM.json`
- **Location**: Same directory as your app files

### Manual Backups
- **Admin Code**: Use promo code `backup` in your app
- **Button**: Available in `dbstats` admin panel
- **Terminal**: Run `python -c "from backup_manager import simple_file_backup; simple_file_backup()"`

## Recovery Process

### If Database Gets Lost on Streamlit Cloud:

1. **Download Latest Backup**: 
   - Get the newest `backup_YYYYMMDD_HHMM.json` from your local development
   - Or create one locally if you have the database file

2. **Add to GitHub Repo**:
   ```
   git add backup_YYYYMMDD_HHMM.json
   git commit -m "Add database backup for recovery"
   git push
   ```

3. **Recovery Code** (add to your app temporarily):
   ```python
   # Add this to your CraveMap.py temporarily for recovery
   if st.button("🚨 EMERGENCY RESTORE"):
       from backup_manager import BackupManager
       import json
       
       # Load backup file
       backup_files = [f for f in os.listdir('.') if f.startswith('backup_') and f.endswith('.json')]
       if backup_files:
           latest_backup = max(backup_files, key=lambda x: os.path.getctime(x))
           with open(latest_backup, 'r') as f:
               backup_data = json.load(f)
           
           backup_manager = BackupManager()
           success = backup_manager.restore_from_backup(backup_data)
           
           if success:
               st.success("✅ Database restored successfully!")
               st.experimental_rerun()
           else:
               st.error("❌ Restore failed")
   ```

4. **Deploy Recovery**: Push the recovery code, use the restore button, then remove the recovery code

## Backup Contents

Your backups include:
- ✅ All user accounts and emails
- ✅ Premium subscription status
- ✅ Search usage counters
- ✅ Support tickets
- ✅ Payment information
- ✅ All timestamps and metadata

## Cost: $0 💰

This solution costs absolutely nothing:
- Uses local file storage
- No external services required  
- Compatible with any hosting platform
- Easy to understand and maintain

## Next Steps

1. **Test Recovery**: Try the restore process once in development
2. **Regular Downloads**: Occasionally download backup files from production
3. **Monitor**: Check admin panel for backup status

## Future Upgrades (If Needed)

If you want to upgrade later (when making money):
- **Dropbox/Google Drive**: Auto-upload backups to cloud storage
- **GitHub Gists**: Private backup storage using GitHub API
- **External Database**: PostgreSQL/MySQL for guaranteed persistence

For now, this file-based solution gives you 99% data safety at $0 cost!
