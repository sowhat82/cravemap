import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from spam_protection import SpamProtection
import json

class SpamMonitoringSystem:
    """Real-time monitoring and alerting for spam/abuse"""
    
    def __init__(self):
        self.spam_protection = SpamProtection()
        self.last_alert_time = {}
        self.alert_cooldown = 3600  # 1 hour between similar alerts
        
        # Email configuration
        self.admin_email = "alvincheong@u.nus.edu"
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.smtp_user = "alvinandsamantha@gmail.com"
        self.smtp_password = "eyxn fzqe reed ksyg"  # App password
    
    def check_for_threats(self):
        """Check for various types of threats and send alerts"""
        threats = []
        
        # Check for high-frequency attacks
        stats = self.spam_protection.get_admin_stats()
        
        # Alert conditions
        if stats['high_severity_24h'] > 10:
            threats.append({
                'type': 'high_severity_spike',
                'message': f"High severity activities: {stats['high_severity_24h']} in last 24h",
                'severity': 'critical'
            })
        
        if stats['flagged_users'] > 5:
            threats.append({
                'type': 'multiple_flagged_users',
                'message': f"Multiple users flagged: {stats['flagged_users']} total",
                'severity': 'warning'
            })
        
        if stats['suspicious_activities_24h'] > 50:
            threats.append({
                'type': 'activity_spike',
                'message': f"Suspicious activity spike: {stats['suspicious_activities_24h']} activities",
                'severity': 'warning'
            })
        
        # Check for coordinated attacks (same activity type happening frequently)
        for activity in stats['activity_breakdown']:
            if activity['count'] > 20:  # Same type of suspicious activity > 20 times
                threats.append({
                    'type': 'coordinated_attack',
                    'message': f"Potential coordinated attack: {activity['activity_type']} occurred {activity['count']} times",
                    'severity': 'critical'
                })
        
        # Send alerts for new threats
        for threat in threats:
            self.send_alert_if_needed(threat)
        
        return threats
    
    def send_alert_if_needed(self, threat):
        """Send alert email if cooldown period has passed"""
        alert_key = f"{threat['type']}_{threat['severity']}"
        now = time.time()
        
        # Check cooldown
        if alert_key in self.last_alert_time:
            if now - self.last_alert_time[alert_key] < self.alert_cooldown:
                return False  # Still in cooldown
        
        # Send alert
        success = self.send_alert_email(threat)
        if success:
            self.last_alert_time[alert_key] = now
        
        return success
    
    def send_alert_email(self, threat):
        """Send alert email to admin"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.admin_email
            msg['Subject'] = f"🚨 CraveMap Security Alert - {threat['severity'].upper()}"
            
            body = f"""
Security Alert for CraveMap

Threat Type: {threat['type']}
Severity: {threat['severity'].upper()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Details:
{threat['message']}

Please review the admin dashboard (use promo code 'dbstats') for more details.

This is an automated alert from CraveMap's security monitoring system.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Failed to send alert email: {str(e)}")
            return False
    
    def generate_daily_report(self):
        """Generate daily security report"""
        stats = self.spam_protection.get_admin_stats()
        
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'summary': {
                'total_requests': stats['total_requests_24h'],
                'flagged_users': stats['flagged_users'],
                'suspicious_activities': stats['suspicious_activities_24h'],
                'high_severity_events': stats['high_severity_24h']
            },
            'activity_breakdown': stats['activity_breakdown'],
            'risk_level': self.calculate_risk_level(stats)
        }
        
        return report
    
    def calculate_risk_level(self, stats):
        """Calculate overall risk level based on stats"""
        risk_score = 0
        
        # Factor in various metrics
        risk_score += stats['high_severity_24h'] * 3
        risk_score += stats['flagged_users'] * 2
        risk_score += min(stats['suspicious_activities_24h'] / 10, 10)  # Cap at 10
        
        if risk_score >= 20:
            return "HIGH"
        elif risk_score >= 10:
            return "MEDIUM"
        else:
            return "LOW"
    
    def cleanup_old_alerts(self):
        """Clean up old alert timestamps"""
        cutoff = time.time() - (24 * 3600)  # 24 hours ago
        
        # Remove old alert timestamps
        self.last_alert_time = {
            k: v for k, v in self.last_alert_time.items() 
            if v > cutoff
        }
    
    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        # Check for threats
        threats = self.check_for_threats()
        
        # Clean up old data
        self.spam_protection.cleanup_old_data()
        self.cleanup_old_alerts()
        
        # Generate daily report if it's a new day
        report = self.generate_daily_report()
        
        return {
            'threats_detected': len(threats),
            'threats': threats,
            'daily_report': report
        }

# For manual testing and scheduled runs
if __name__ == "__main__":
    monitor = SpamMonitoringSystem()
    result = monitor.run_monitoring_cycle()
    
    print("Monitoring Results:")
    print(f"Threats detected: {result['threats_detected']}")
    
    if result['threats']:
        print("\nThreats:")
        for threat in result['threats']:
            print(f"- {threat['type']}: {threat['message']}")
    
    print(f"\nRisk Level: {result['daily_report']['risk_level']}")
    print(f"Total Requests (24h): {result['daily_report']['summary']['total_requests']}")
