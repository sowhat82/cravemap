# CraveMap Spam & Abuse Prevention Guide

## 🛡️ Multi-Layer Protection System

### 1. Rate Limiting
- **Hourly Limit**: 20 searches per hour for anonymous users
- **Daily Limit**: 100 searches per day for free users
- **Premium Users**: Higher limits (500/day)
- **Fingerprinting**: Uses IP + User Agent + Session ID

### 2. Content Filtering
- **Commercial Spam**: Detects buy/sell/cheap/discount patterns
- **Repetitive Patterns**: Blocks excessive character repetition
- **URL/Email Injection**: Prevents promotional links
- **Excessive Length**: Limits query length to prevent abuse
- **SQL Injection**: Blocks database attack attempts

### 3. Behavioral Analysis
- **Bot Detection**: Identifies regular timing patterns
- **Excessive Flags**: Auto-blocks users with multiple violations
- **Coordination Detection**: Spots coordinated attack patterns

### 4. Real-time Monitoring
- **Automated Alerts**: Email notifications for critical threats
- **Admin Dashboard**: Real-time statistics via `dbstats` promo code
- **Daily Reports**: Comprehensive security summaries

## 📊 Monitoring Dashboard

Access admin panel with promo code: `dbstats`

**Key Metrics to Watch:**
- Requests per hour/day
- Flagged users count
- Suspicious activity types
- High severity events

**Alert Thresholds:**
- 🔴 **Critical**: >10 high-severity events in 24h
- 🟡 **Warning**: >5 flagged users or >50 suspicious activities
- 🟢 **Normal**: Below warning thresholds

## 🚨 Incident Response Plan

### Immediate Actions (< 5 minutes)
1. Check admin dashboard for threat details
2. Identify attack pattern from activity breakdown
3. Review flagged users and their activities

### Short-term Response (< 1 hour)
1. Adjust rate limits if needed:
   ```python
   # In spam_protection.py, modify these values:
   if search_1h >= 10:  # Reduce from 20 to 10
   if search_24h >= 50:  # Reduce from 100 to 50
   ```

2. Add new spam patterns:
   ```python
   # Add to suspicious_patterns in check_spam_patterns()
   (r'new_pattern_here', 'description'),
   ```

3. Block specific patterns in database:
   ```sql
   INSERT INTO blocked_patterns (pattern_type, pattern_value, reason)
   VALUES ('keyword', 'spam_word', 'Manual block due to abuse');
   ```

### Long-term Response (< 24 hours)
1. Analyze attack trends
2. Update detection algorithms
3. Consider implementing CAPTCHA for flagged users
4. Review and adjust alert thresholds

## 🔧 Configuration Options

### Rate Limits (in spam_protection.py)
```python
# Hourly limits
if search_1h >= 20:  # Adjust this number

# Daily limits  
if search_24h >= 100:  # Adjust this number

# Alert thresholds
if stats['high_severity_24h'] > 10:  # Adjust threshold
```

### Email Alerts (in spam_monitoring.py)
```python
self.alert_cooldown = 3600  # 1 hour between alerts
self.admin_email = "your-admin@email.com"
```

## 📈 Scaling Considerations

### High Traffic (>1000 users/day)
1. **Database Optimization**:
   - Add indexes on fingerprint and timestamp columns
   - Consider Redis for rate limiting

2. **Advanced Protection**:
   - Implement CAPTCHA challenges
   - Add IP geolocation blocking
   - Machine learning anomaly detection

3. **Infrastructure**:
   - CDN with DDoS protection
   - Load balancing for multiple instances

### Enterprise Level (>10,000 users/day)
1. **External Services**:
   - CloudFlare bot protection
   - AWS WAF integration
   - Third-party fraud detection

2. **Monitoring**:
   - Real-time alerting systems
   - Security information and event management (SIEM)
   - Automated incident response

## 🛠️ Maintenance Tasks

### Daily (Automated)
- [x] Clean up old data (>30 days)
- [x] Generate security reports
- [x] Send critical alerts

### Weekly (Manual)
1. Review flagged users
2. Analyze attack patterns
3. Update spam detection rules
4. Check alert accuracy

### Monthly (Strategic)
1. Security audit
2. Performance optimization
3. Update response procedures
4. Review rate limit effectiveness

## 🚀 Deployment Checklist

Before going public:

- [x] **Spam Protection**: Implemented and tested
- [x] **Rate Limiting**: Configured appropriately
- [x] **Email Alerts**: Working and tested
- [x] **Admin Dashboard**: Accessible and functional
- [x] **Database**: Optimized with proper indexes
- [x] **Backup System**: Automated and verified

### Production Environment Setup
1. Set environment variables:
   ```
   CRAVEMAP_ADMIN_EMAIL=your-admin@email.com
   SMTP_PASSWORD=your-app-password
   ```

2. Enable logging:
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

3. Set up monitoring cron job:
   ```bash
   # Run every hour
   0 * * * * cd /path/to/cravemap && python spam_monitoring.py
   ```

## 📞 Emergency Contacts

**Critical Issues**: Check admin dashboard first
**Email Alerts**: Configured to send to your admin email
**Backup Access**: Use backup files if database is compromised

## 🔍 Common Attack Patterns

1. **Credential Stuffing**: Multiple login attempts
2. **Search Spam**: Repetitive or commercial queries  
3. **Resource Exhaustion**: High-frequency requests
4. **Data Scraping**: Systematic data extraction
5. **Injection Attacks**: SQL/XSS attempts

Each pattern is automatically detected and flagged by the system.

---

**Last Updated**: September 2025
**Version**: 1.0
**System Status**: ✅ Active Protection Enabled
