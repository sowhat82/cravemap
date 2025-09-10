import streamlit as st
import requests
import os
from openai import OpenAI
from dotenv import load_dotenv
import streamlit.components.v1 as components
import stripe
import json
import hashlib
from datetime import datetime, timedelta
import time
import uuid
from legal import PRIVACY_POLICY, TERMS_OF_SERVICE
import smtplib
from email.mime.text import MIMEText
from database import CraveMapDB
from backup_manager import BackupManager, simple_file_backup
from email.mime.multipart import MIMEMultipart
try:
    from database import db  # Import database instance
except Exception as db_error:
    # If database import fails, create a fallback
    st.error(f"Database initialization failed: {db_error}")
    db = None
from spam_protection import SpamProtection

# Initialize backup manager and spam protection
backup_manager = BackupManager()
spam_protection = SpamProtection()

def check_and_backup():
    """Check if backup is needed and create one (silent operation for production)"""
    try:
        # Check if it's been more than 24 hours since last backup
        backup_files = [f for f in os.listdir('.') if f.startswith('backup_') and f.endswith('.json')]
        
        if not backup_files:
            # No backup exists, create one (silent)
            backup_file = simple_file_backup()
            # Only show message in development/debug mode
            if os.getenv('CRAVEMAP_DEBUG', 'false').lower() == 'true':
                if backup_file:
                    st.success(f"✅ Initial backup created: {backup_file}")
        else:
            # Check if latest backup is older than 24 hours
            latest_backup = max(backup_files, key=lambda x: os.path.getctime(x))
            backup_age = time.time() - os.path.getctime(latest_backup)
            
            if backup_age > 86400:  # 24 hours in seconds
                backup_file = simple_file_backup()
                # Only show message in development/debug mode
                if os.getenv('CRAVEMAP_DEBUG', 'false').lower() == 'true':
                    if backup_file:
                        st.info(f"🔄 Daily backup created: {backup_file}")
    except Exception as e:
        # Only show backup errors if they're critical
        if "permission" in str(e).lower() or "disk" in str(e).lower():
            st.warning(f"⚠️ Backup system needs attention - please check storage space")

# Run backup check on app startup (only once per session)
if 'backup_checked' not in st.session_state:
    check_and_backup()
    st.session_state.backup_checked = True

# Pricing Configuration - Easy to change for future updates
PREMIUM_PRICE_SGD = 9.99  # Monthly subscription price in SGD
PREMIUM_PRICE_CENTS = int(PREMIUM_PRICE_SGD * 100)  # Price in cents for Stripe
PREMIUM_PRICE_DISPLAY = f"${PREMIUM_PRICE_SGD:.2f}"  # Formatted price for display

# Set page config
st.set_page_config(
    page_title="CraveMap: Find Food by Craving",
    page_icon="🍕"
)

# Load environment variables from .env file (for local development)
load_dotenv()

# Load models from external JSON file (models_config.json)
try:
    with open("models_config.json") as f:
        models = json.load(f).get("models", ["mistralai/mistral-7b-instruct:free"])
except:
    # Fallback to only working free models if config file is missing
    models = ["mistralai/mistral-7b-instruct:free", "meta-llama/llama-3.3-70b-instruct:free"]

# Admin secret codes (only you know these)
ADMIN_UPGRADE_CODE = "cravemap2024premium"  # Use this to activate premium
ADMIN_DOWNGRADE_CODE = "resetfree"      # Use this to go back to free tier
ADMIN_RESET_COUNTER = "resetcounter"    # Use this to reset monthly searches

# Trial system constants
TRIAL_CODE = "trial7days"              # 7-day trial code
TRIAL_DURATION_DAYS = 7                # Trial duration
TRIAL_DAILY_LIMIT = 20                 # Generous daily limit for trial users

def has_premium_access():
    """Check if user has premium access (either paid premium OR active trial)"""
    # Check regular premium status
    if st.session_state.get('user_premium', False):
        return True
    
    # Check if user has active trial
    if not st.session_state.get('user_email'):
        return False
    
    user_id = get_user_id()
    user_data = load_user_data(user_id)
    trial_status = check_trial_status(user_data)
    
    return trial_status['is_trial_active']

def check_trial_status(user_data):
    """Check if user is on active trial and return trial status"""
    if not user_data.get('trial_active'):
        return {'is_trial_active': False, 'days_remaining': 0, 'daily_searches': 0}
    
    trial_start = user_data.get('trial_start_date')
    if not trial_start:
        return {'is_trial_active': False, 'days_remaining': 0, 'daily_searches': 0}
    
    try:
        # Parse trial start date
        trial_start_date = datetime.fromisoformat(trial_start)
        now = datetime.now()
        days_elapsed = (now - trial_start_date).days
        
        # Check if trial is still active (expired)
        if days_elapsed >= TRIAL_DURATION_DAYS:
            return {'is_trial_active': False, 'days_remaining': 0, 'daily_searches': 0}
        
        # Count today's searches
        today_str = now.strftime('%Y-%m-%d')
        trial_searches = user_data.get('trial_daily_searches', {})
        daily_searches = trial_searches.get(today_str, 0)
        
        return {
            'is_trial_active': True,
            'days_remaining': TRIAL_DURATION_DAYS - days_elapsed,
            'daily_searches': daily_searches
        }
    except:
        return {'is_trial_active': False, 'days_remaining': 0, 'daily_searches': 0}

def increment_trial_search(user_id, user_data):
    """Increment daily trial search count"""
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    
    # Get current trial searches
    trial_searches = user_data.get('trial_daily_searches', {})
    trial_searches[today_str] = trial_searches.get(today_str, 0) + 1
    
    # Clean up old dates (keep only last 30 days)
    cutoff_date = now - timedelta(days=30)
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')
    trial_searches = {k: v for k, v in trial_searches.items() if k >= cutoff_str}
    
    # Update user data
    user_data['trial_daily_searches'] = trial_searches
    save_user_data(user_id, user_data)
    
    return trial_searches[today_str]

# User authentication system
def get_user_email():
    """Get user email through optional login"""
    if 'user_email' not in st.session_state:
        st.session_state['user_email'] = None
    
    # Check for remembered user first
    if not st.session_state['user_email']:
        try:
            with open('.remembered_user.txt', 'r') as f:
                remembered_email = f.read().strip()
                if remembered_email:
                    st.session_state['user_email'] = remembered_email
        except:
            pass
    
    return st.session_state['user_email']

def show_login_option():
    """Show optional login in sidebar"""
    if not st.session_state.get('user_email'):
        st.sidebar.markdown("### 🔐 Login (Optional)")
        st.sidebar.markdown("Login to access premium features & save your progress")
        
        with st.sidebar.form("login_form"):
            email = st.text_input("Enter your email:", placeholder="your@email.com", key="login_email", help="Enter your email to access premium features")
            remember_me = st.checkbox("Remember me on this device")
            submit = st.form_submit_button("Login")
            
            if submit and email:
                if "@" in email and "." in email:  # Basic email validation
                    st.session_state['user_email'] = email.lower().strip()
                    
                    # Refresh session with user's actual data
                    user_id = hashlib.md5(email.lower().strip().encode()).hexdigest()[:8]
                    user_data = load_user_data(user_id)
                    st.session_state.user_premium = bool(user_data.get('is_premium', False))
                    st.session_state.payment_completed = bool(user_data.get('payment_completed', False))
                    st.session_state.monthly_searches = user_data['monthly_searches']
                    st.session_state.last_search_reset = user_data['last_search_reset']
                    
                    # Remember user on this device if requested
                    if remember_me:
                        try:
                            with open('.remembered_user.txt', 'w') as f:
                                f.write(email.lower().strip())
                        except:
                            pass
                    
                    premium_status = "Premium" if st.session_state.user_premium else "Free"
                    st.success(f"Welcome back, {email}! ({premium_status} account)")
                    st.rerun()
                else:
                    st.error("Please enter a valid email address")
        
        # Check for remembered user display
        try:
            with open('.remembered_user.txt', 'r') as f:
                remembered_email = f.read().strip()
                if remembered_email:
                    st.sidebar.info(f"Found saved login: {remembered_email}")
                    if st.sidebar.button("Use saved login"):
                        st.session_state['user_email'] = remembered_email
                        
                        # Refresh session with remembered user's data
                        user_id = hashlib.md5(remembered_email.encode()).hexdigest()[:8]
                        user_data = load_user_data(user_id)
                        st.session_state.user_premium = bool(user_data.get('is_premium', False))
                        st.session_state.payment_completed = bool(user_data.get('payment_completed', False))
                        st.session_state.monthly_searches = user_data['monthly_searches']
                        st.session_state.last_search_reset = user_data['last_search_reset']
                        
                        st.rerun()
        except:
            pass

def get_client_info():
    """Get client information for rate limiting"""
    # Try to get real IP address
    headers = {}
    try:
        if hasattr(st.context, 'headers'):
            headers = st.context.headers
    except:
        pass
    
    # Get IP (with fallbacks)
    client_ip = (
        headers.get('x-forwarded-for', '').split(',')[0].strip() or
        headers.get('x-real-ip', '') or
        headers.get('remote-addr', '') or
        'unknown'
    )
    
    # Get user agent for additional fingerprinting
    user_agent = headers.get('user-agent', 'unknown')
    
    return client_ip, user_agent

def get_rate_limit_key():
    """Generate a key for rate limiting that users cannot easily manipulate"""
    client_ip, user_agent = get_client_info()
    
    # For development/localhost, we'll use a combination approach
    if client_ip in ['unknown', '127.0.0.1', 'localhost']:
        # Use browser session + some harder-to-change elements
        if 'browser_session_key' not in st.session_state:
            # Generate based on streamlit session and user agent
            session_data = str(id(st.session_state)) + user_agent + str(time.time())[:8]
            st.session_state.browser_session_key = hashlib.md5(session_data.encode()).hexdigest()[:12]
        return f"local_{st.session_state.browser_session_key}"
    else:
        # Production: Use IP + User Agent hash
        combined = f"{client_ip}_{user_agent}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]

def get_current_daily_usage():
    """Get current daily usage without incrementing counter"""
    rate_limit_key = get_rate_limit_key()
    rate_limit_file = '.rate_limits.json'
    
    try:
        with open(rate_limit_file, 'r') as f:
            rate_data = json.load(f)
    except:
        return 0
    
    today = datetime.now().strftime('%Y-%m-%d')
    today_key = f"{rate_limit_key}_{today}"
    return rate_data.get(today_key, 0)

def check_global_rate_limits():
    """Check global rate limits using a server-side file that users cannot manipulate"""
    rate_limit_key = get_rate_limit_key()
    rate_limit_file = '.rate_limits.json'
    
    try:
        with open(rate_limit_file, 'r') as f:
            rate_data = json.load(f)
    except:
        rate_data = {}
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Clean old data (keep only today and yesterday)
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    rate_data = {k: v for k, v in rate_data.items() if k.endswith(today) or k.endswith(yesterday)}
    
    # Check today's usage for this client
    today_key = f"{rate_limit_key}_{today}"
    today_searches = rate_data.get(today_key, 0)
    
    # Allow up to 2 searches per day per client (reduced from 3 for conversion)
    if today_searches >= 2:
        return False, today_searches
    
    # Increment counter
    rate_data[today_key] = today_searches + 1
    
    # Save updated data
    try:
        with open(rate_limit_file, 'w') as f:
            json.dump(rate_data, f)
    except:
        pass
    
    return True, rate_data[today_key]

def get_user_id():
    """Get user ID - email-based for logged users, rate-limit-key for anonymous"""
    email = get_user_email()
    if email:
        # Logged in user - consistent ID from email
        return hashlib.md5(email.encode()).hexdigest()[:8]
    else:
        # Anonymous user - use rate limiting key (but still create individual user files)
        rate_key = get_rate_limit_key()
        return f"anon_{rate_key}"

# Function to load usage data for specific user
def load_user_data(user_id):
    """Load user data from database with fallback to JSON files"""
    try:
        if db is not None:
            return db.get_user(user_id)
        else:
            raise Exception("Database instance not available")
    except Exception as e:
        # Fallback to JSON file system if database fails
        try:
            filename = f".user_data_{user_id}.json"
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    return json.load(f)
            else:
                # Return default user structure
                return {
                    'user_id': user_id,
                    'email': st.session_state.get('user_email', ''),
                    'is_premium': False,
                    'payment_completed': False,
                    'stripe_customer_id': None,
                    'monthly_searches': 0,
                    'last_search_reset': datetime.now().isoformat(),
                    'premium_since': None,
                    'promo_activation': None
                }
        except Exception as file_error:
            # Return minimal default structure
            return {
                'user_id': user_id,
                'email': '',
                'is_premium': False,
                'payment_completed': False,
                'monthly_searches': 0,
                'last_search_reset': datetime.now().isoformat()
            }

# Function to save usage data for specific user
def save_user_data(user_id, data):
    """Save user data to database with fallback to JSON files"""
    try:
        if db is not None:
            db.save_user(
                user_id=user_id,
                email=data.get('email', st.session_state.get('user_email', '')),
                is_premium=data.get('is_premium', False),
                payment_completed=data.get('payment_completed', False),
                stripe_customer_id=data.get('stripe_customer_id'),
                monthly_searches=data.get('monthly_searches', 0),
                last_search_reset=data.get('last_search_reset', datetime.now().isoformat()),
                premium_since=data.get('premium_since'),
                promo_activation=data.get('promo_activation')
            )
        else:
            raise Exception("Database instance not available")
    except Exception as e:
        # Fallback to JSON file system if database fails
        try:
            filename = f".user_data_{user_id}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as file_error:
            st.error(f"File save failed: {str(file_error)}")

def send_support_email(support_data):
    """Send support ticket directly to admin email via Gmail relay"""
    try:
        # Get email credentials from secrets
        sender_email = st.secrets.get("SUPPORT_EMAIL", "cravemap.notifications@gmail.com")
        sender_password = st.secrets.get("SUPPORT_EMAIL_PASSWORD", "")
        admin_email = st.secrets.get("SUPPORT_RECIPIENT", "alvincheong@u.nus.edu")  # Where tickets go
        
        if not sender_password:
            # If no email credentials, save locally only
            print("No Gmail app password configured - saving locally only")
            return False
        
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = admin_email
        msg['Subject'] = f"CraveMap Support: {support_data['support_type']} - {support_data['subject']}"
        msg['Reply-To'] = support_data['user_email']  # User can reply directly
        
        # Email body
        body = f"""
New CraveMap Support Request

Support Type: {support_data['support_type']}
Subject: {support_data['subject']}
User Email: {support_data['user_email']}
User ID: {support_data['user_id']}
Timestamp: {support_data['timestamp']}

Message:
{support_data['message']}

---
Reply directly to this email to respond to the user.
This email was sent via Gmail relay from your CraveMap application.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email using Gmail
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, admin_email, text)
        server.quit()
        
        print("Email sent successfully via Gmail relay")
        return True
        
    except Exception as e:
        # If email fails, still save locally
        print(f"Gmail relay failed: {e}")
        return False

# Subscription management functions
def check_subscription_status(user_data):
    """Check if subscription is still valid and active"""
    if not user_data.get('is_premium', False):
        return False  # Not premium anyway
    
    # Check if this is a promo code activation (admin override)
    promo_activation = user_data.get('promo_activation', '')
    if 'Admin code:' in promo_activation:
        return True  # Promo code activations don't expire
    
    # Check if subscription has expired
    premium_since = user_data.get('premium_since')
    if not premium_since:
        return False
    
    try:
        premium_date = datetime.fromisoformat(premium_since)
        # Check if it's been more than 35 days (monthly + 5 day grace period)
        days_since_premium = (datetime.now() - premium_date).days
        
        if days_since_premium > 35:
            return False  # Subscription likely expired
            
        # If we have a Stripe subscription ID, check with Stripe
        stripe_subscription_id = user_data.get('stripe_subscription_id')
        if stripe_subscription_id:
            try:
                # Check subscription status with Stripe
                subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                if subscription.status not in ['active', 'trialing']:
                    return False  # Subscription is cancelled/past_due/etc
            except stripe.error.StripeError:
                # If we can't reach Stripe or subscription doesn't exist
                # Fall back to date-based check (already done above)
                pass
        
        return True  # Subscription appears valid
        
    except (ValueError, TypeError):
        return False  # Invalid date format

def revoke_premium_access(user_id, reason="subscription_expired"):
    """Revoke premium access for a user"""
    user_data = load_user_data(user_id)
    user_data['is_premium'] = False
    user_data['premium_revoked'] = datetime.now().isoformat()
    user_data['revocation_reason'] = reason
    user_data['premium_since'] = None  # Clear premium start date
    save_user_data(user_id, user_data)
    
    # Update session state if this is the current user
    current_id = get_user_id()
    if user_id == current_id:
        st.session_state.user_premium = False

def validate_subscription_for_user(user_data, user_id):
    """Validate subscription and revoke if necessary"""
    if user_data.get('is_premium', False):
        if not check_subscription_status(user_data):
            revoke_premium_access(user_id, "subscription_validation_failed")
            return False  # Premium revoked
    return user_data.get('is_premium', False)  # Return current status

def handle_stripe_webhook_simulation():
    """Simulate webhook handling by checking URL parameters for webhook events"""
    try:
        query_params = st.query_params
        
        # Check for subscription status updates (would come from actual webhooks in production)
        if 'subscription_canceled' in query_params:
            subscription_id = query_params.get('subscription_id', '')
            if subscription_id:
                # Find user with this subscription and revoke access
                import glob
                for filename in glob.glob('.user_data_*.json'):
                    if not filename.startswith('.user_data_anon_'):
                        try:
                            with open(filename, 'r') as f:
                                user_data = json.load(f)
                            if user_data.get('stripe_subscription_id') == subscription_id:
                                revoke_premium_access(user_data['user_id'], "stripe_webhook_canceled")
                                break
                        except:
                            continue
                st.query_params.clear()
                
        elif 'subscription_updated' in query_params:
            # Handle subscription updates (reactivation, etc.)
            subscription_id = query_params.get('subscription_id', '')
            status = query_params.get('status', '')
            if subscription_id and status:
                import glob
                for filename in glob.glob('.user_data_*.json'):
                    if not filename.startswith('.user_data_anon_'):
                        try:
                            with open(filename, 'r') as f:
                                user_data = json.load(f)
                            if user_data.get('stripe_subscription_id') == subscription_id:
                                if status in ['active', 'trialing']:
                                    # Reactivate premium
                                    user_data['is_premium'] = True
                                    user_data['premium_since'] = datetime.now().isoformat()
                                else:
                                    # Deactivate premium
                                    revoke_premium_access(user_data['user_id'], f"stripe_status_{status}")
                                save_user_data(user_data['user_id'], user_data)
                                break
                        except:
                            continue
                st.query_params.clear()
                
    except Exception:
        # Silently handle any webhook simulation errors
        pass

def auto_check_all_subscriptions():
    """Automatically check all premium subscriptions in background"""
    try:
        # Only run this check occasionally to avoid performance issues
        # Check if we've run this recently
        try:
            with open('.last_subscription_check.txt', 'r') as f:
                last_check = datetime.fromisoformat(f.read().strip())
                # Only check every 6 hours to avoid overloading
                if (datetime.now() - last_check).total_seconds() < 21600:  # 6 hours
                    return
        except (FileNotFoundError, ValueError):
            pass  # File doesn't exist or invalid format, proceed with check
        
        import glob
        checked = 0
        revoked = 0
        
        # Check all user data files
        for filename in glob.glob('.user_data_*.json'):
            if not filename.startswith('.user_data_anon_'):  # Skip anonymous users
                try:
                    with open(filename, 'r') as f:
                        user_data = json.load(f)
                    user_id = user_data.get('user_id', '')
                    if user_data.get('is_premium', False):
                        checked += 1
                        if not check_subscription_status(user_data):
                            revoke_premium_access(user_id, "automatic_subscription_check")
                            revoked += 1
                except:
                    continue  # Skip files we can't read
        
        # Update the last check time
        with open('.last_subscription_check.txt', 'w') as f:
            f.write(datetime.now().isoformat())
            
        # Log the results (only if any revocations happened)
        if revoked > 0:
            with open('.subscription_log.txt', 'a') as f:
                f.write(f"{datetime.now().isoformat()}: Checked {checked} users, revoked {revoked} expired subscriptions\n")
                
    except Exception:
        # Silently fail - don't break the app if subscription checks fail
        pass

# Get current user ID and load their data
current_user_id = get_user_id()
usage_data = load_user_data(current_user_id)

# Initialize session state with proper premium status
def initialize_user_session():
    """Properly initialize user session with correct premium status"""
    user_id = get_user_id()
    user_data = load_user_data(user_id)
    
    # Always refresh premium status from file data
    if user_id.startswith('anon_'):
        st.session_state.user_premium = False
    else:
        # Validate subscription before setting premium status
        st.session_state.user_premium = validate_subscription_for_user(user_data, user_id)
        # Reload data in case it was modified by validation
        user_data = load_user_data(user_id)
    
    st.session_state.monthly_searches = user_data['monthly_searches']
    st.session_state.last_search_reset = user_data['last_search_reset']
    
    if 'payment_completed' not in st.session_state:
        st.session_state.payment_completed = False

# Initialize the session
initialize_user_session()

# Handle webhook-like events for subscription management
handle_stripe_webhook_simulation()

# Automatically check all subscriptions in background (hands-off maintenance)
auto_check_all_subscriptions()

# Show optional login in sidebar
show_login_option()

# Load API keys
try:
    # Get keys from Streamlit secrets first, fallback to environment
    OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if not OPENROUTER_API_KEY:
        st.error("OpenRouter API key not found")
        st.stop()
    if not GOOGLE_API_KEY:
        st.error("Google API key not found")
        st.stop()
        
    # Auto-detect environment for Stripe configuration
    def detect_environment():
        """Automatically detect if we're in test or live environment"""
        # Check for manual override first
        override = st.secrets.get("STRIPE_MODE_OVERRIDE", None)
        if override:
            return override.lower()
            
        # Check for Streamlit Cloud deployment
        if (os.getenv('STREAMLIT_SHARING_MODE') or 
            'streamlit.app' in str(os.getenv('HOSTNAME', ''))):
            return "live"
        
        # Check if running locally
        if os.path.exists('.env'):
            return "test"
            
        # Default to live for safety
        return "live"
    
    stripe_mode = detect_environment()
    
    # Store in session state for later use
    st.session_state['stripe_mode'] = stripe_mode
    
    if stripe_mode == "live":
        STRIPE_SECRET_KEY = st.secrets.get("STRIPE_LIVE_SECRET_KEY", "")
        STRIPE_PUBLISHABLE_KEY = st.secrets.get("STRIPE_LIVE_PUBLISHABLE_KEY", "")
        # No banner for live mode - looks professional
    else:
        STRIPE_SECRET_KEY = st.secrets.get("STRIPE_TEST_SECRET_KEY", "")
        STRIPE_PUBLISHABLE_KEY = st.secrets.get("STRIPE_TEST_PUBLISHABLE_KEY", "")
        st.sidebar.success("🟡 **TEST MODE** - No real charges")
    
    # Configure Stripe
    stripe.api_key = STRIPE_SECRET_KEY
        
except Exception as e:
    st.error(f"❌ Error loading API keys: {e}")
    st.stop()

# Stripe functions
def get_app_url():
    """Detect the correct app URL for both local and deployed environments"""
    try:
        # First check for manual override in secrets/environment
        manual_override = st.secrets.get("APP_URL_OVERRIDE") or os.getenv("APP_URL_OVERRIDE")
        if manual_override:
            print(f"🔧 Using manual URL override: {manual_override}")
            return manual_override
        
        # Debug: Check environment variables
        hostname = os.getenv('HOSTNAME', '')
        server_name = os.getenv('SERVER_NAME', '')
        
        # Check if we're on Streamlit Cloud/deployed environment
        # More comprehensive detection for Streamlit Cloud
        if (os.getenv('STREAMLIT_SHARING_MODE') or 
            os.getenv('STREAMLIT_CLOUD') or
            'streamlit.app' in hostname.lower() or
            'streamlit.app' in server_name.lower() or
            os.getenv('STREAMLIT_DEPLOYMENT_MODE') == 'cloud'):
            # For Streamlit Cloud, construct the URL
            detected_url = "https://cravemap.streamlit.app"
            print(f"🌐 Detected Streamlit Cloud deployment: {detected_url}")
            return detected_url
        
        # Check for other cloud platforms
        if os.getenv('HEROKU_APP_NAME'):
            detected_url = f"https://{os.getenv('HEROKU_APP_NAME')}.herokuapp.com"
            print(f"🌐 Detected Heroku deployment: {detected_url}")
            return detected_url
        elif os.getenv('RAILWAY_STATIC_URL'):
            detected_url = os.getenv('RAILWAY_STATIC_URL')
            print(f"🌐 Detected Railway deployment: {detected_url}")
            return detected_url
        elif os.getenv('VERCEL_URL'):
            detected_url = f"https://{os.getenv('VERCEL_URL')}"
            print(f"🌐 Detected Vercel deployment: {detected_url}")
            return detected_url
        
        # If none of the above, assume local development
        port = st.get_option('server.port') or 8501
        detected_url = f"http://localhost:{port}"
        print(f"🖥️ Detected local development: {detected_url}")
        return detected_url
        
    except Exception as e:
        # Ultimate fallback
        print(f"❌ URL detection failed: {e}, using localhost fallback")
        return "http://localhost:8501"

def create_stripe_checkout_session():
    """Create a Stripe checkout session for premium subscription"""
    try:
        user_email = st.session_state.get('user_email', '')
        if not user_email:
            return None  # Don't show error here, handle it in the UI
        
        # Check if Stripe is properly configured
        if not stripe.api_key:
            st.error("❌ Payment system not configured. Please contact support.")
            return None
        
        app_url = get_app_url()
            
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            customer_email=user_email,  # Pre-fill customer email
            line_items=[{
                'price_data': {
                    'currency': 'sgd',
                    'product_data': {
                        'name': 'CraveMap Premium',
                        'description': 'Unlimited searches, advanced filters, and detailed analytics',
                    },
                    'unit_amount': PREMIUM_PRICE_CENTS,  # Price in cents (SGD)
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            success_url=f"{app_url}/?payment_success=true&email={user_email}",
            cancel_url=f"{app_url}"
        )
        return checkout_session.url
    except stripe.error.InvalidRequestError as e:
        st.error(f"❌ Payment configuration error: {str(e)}")
        return None
    except stripe.error.AuthenticationError as e:
        st.error("❌ Payment system authentication failed. Please contact support.")
        return None
    except Exception as e:
        st.error(f"❌ Error creating checkout session: {str(e)}")
        return None

def check_payment_status():
    """Check if payment was successful from URL parameters"""
    try:
        query_params = st.query_params
        
        if 'payment_success' in query_params and query_params['payment_success'] == 'true':
            # Get email from URL if provided
            payment_email = query_params.get('email', [''])[0] if isinstance(query_params.get('email'), list) else query_params.get('email', '')
            
            if payment_email:
                # Auto-login the user with the payment email
                st.session_state['user_email'] = payment_email.lower().strip()
                
                # Get the correct user ID for this email
                user_id = hashlib.md5(payment_email.lower().strip().encode()).hexdigest()[:8]
                
                # Update session state
                st.session_state.user_premium = True
                st.session_state.payment_completed = True
                
                # Try to find the subscription ID from recent Stripe subscriptions
                stripe_subscription_id = None
                try:
                    # Search for recent subscriptions for this customer email
                    customers = stripe.Customer.list(email=payment_email.lower().strip(), limit=1)
                    if customers.data:
                        customer = customers.data[0]
                        subscriptions = stripe.Subscription.list(customer=customer.id, limit=1)
                        if subscriptions.data:
                            stripe_subscription_id = subscriptions.data[0].id
                except stripe.error.StripeError:
                    # If we can't get the subscription ID, that's okay
                    pass
                
                # Update usage data file with premium status for the correct user
                usage_data = load_user_data(user_id)
                usage_data['is_premium'] = True
                usage_data['premium_since'] = datetime.now().isoformat()
                usage_data['payment_email'] = payment_email.lower().strip()
                if stripe_subscription_id:
                    usage_data['stripe_subscription_id'] = stripe_subscription_id
                save_user_data(user_id, usage_data)
                
                # Remember this user on device
                try:
                    with open('.remembered_user.txt', 'w') as f:
                        f.write(payment_email.lower().strip())
                except:
                    pass
                
                # Clear URL parameters and show success message
                st.query_params.clear()
                st.balloons()
                st.success(f"🎉 Payment successful! Welcome to Premium, {payment_email}!")
                st.rerun()
            else:
                # Fallback for anonymous users (shouldn't happen with new flow)
                st.error("❌ Payment completed but no email found. Please contact support.")
                
    except Exception as e:
        st.error(f"Error checking payment status: {str(e)}")

# Check payment status when app loads
check_payment_status()

def check_search_limits():
    """Check search limits with robust rate limiting for anonymous users"""
    email = get_user_email()
    
    if email:
        # Logged-in user: Use normal file-based tracking
        user_id = get_user_id()
        user_data = load_user_data(user_id)
        
        # Check monthly reset
        now = datetime.now()
        last_reset = datetime.fromisoformat(user_data['last_search_reset'])
        
        if now.month != last_reset.month or now.year != last_reset.year:
            user_data['monthly_searches'] = 0
            user_data['last_search_reset'] = now.isoformat()
            save_user_data(user_id, user_data)
        
        # Sync session state
        st.session_state.monthly_searches = user_data['monthly_searches']
        st.session_state.last_search_reset = user_data['last_search_reset']
        st.session_state.user_premium = bool(user_data.get('is_premium', False))
        st.session_state.payment_completed = bool(user_data.get('payment_completed', False))
        
        # Premium users have unlimited searches
        if st.session_state.user_premium:
            return True
        
        # Check if user is on trial
        trial_status = check_trial_status(user_data)
        if trial_status['is_trial_active']:
            # Check daily limit for trial users
            daily_searches = trial_status['daily_searches']
            if daily_searches >= TRIAL_DAILY_LIMIT:
                st.warning(f"🔒 You've reached your daily trial limit of {TRIAL_DAILY_LIMIT} searches! Try again tomorrow.")
                return False
            else:
                # Increment trial search count
                new_daily_count = increment_trial_search(user_id, user_data)
                days_left = trial_status['days_remaining']
                remaining_today = TRIAL_DAILY_LIMIT - new_daily_count
                st.info(f"🎯 Trial Mode: {new_daily_count}/{TRIAL_DAILY_LIMIT} searches today | {days_left} days remaining")
                return True
        
        # Check if user has reached monthly limit
        if user_data['monthly_searches'] >= 5:
            st.warning("🔒 You've reached your 5 free searches for this month!")
            return False
        
        # Increment search count using database method with fallback
        try:
            if db is not None:
                new_count = db.update_search_count(user_id, 1)
            else:
                # Fallback: manually update the count
                user_data['monthly_searches'] += 1
                save_user_data(user_id, user_data)
                new_count = user_data['monthly_searches']
        except Exception as e:
            # Fallback: manually update the count
            user_data['monthly_searches'] += 1
            save_user_data(user_id, user_data)
            new_count = user_data['monthly_searches']
        
        st.session_state.monthly_searches = new_count
        
        remaining = 5 - new_count
        if remaining > 0:
            st.info(f"ℹ️ You have {remaining} free {'search' if remaining == 1 else 'searches'} remaining this month.")
        
        return True
    
    else:
        # Anonymous user: Use server-side rate limiting that can't be bypassed
        can_search, search_count = check_global_rate_limits()
        
        if not can_search:
            st.error("� **Daily limit reached!** You've used all 3 free searches today from this device/network.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("**🆓 Create Account:** Get monthly limits instead of daily limits")
            with col2:
                st.info("**🌟 Go Premium:** Unlimited searches + advanced features")
            
            st.caption("💡 Limits reset daily at midnight. Create an account for better monthly tracking!")
            return False
        
        remaining = 3 - search_count
        if remaining > 0:
            st.info(f"ℹ️ Anonymous mode: {remaining} free {'search' if remaining == 1 else 'searches'} remaining today.")
            st.caption("💡 Create an account to get monthly limits instead of daily limits!")
        
        return True

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://cravemap.streamlit.app",
        "X-Title": "CraveMap"
    }
)

def get_place_details(place_id):
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,reviews,photos",
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    return response.json()

def summarize_reviews_and_dishes(reviews):
    """Summarize reviews and extract dishes with robust model fallback"""
    review_texts = [r['text'] for r in reviews if 'text' in r]
    if not review_texts:
        return "No reviews available."
        
    joined = "\n".join(review_texts)
    prompt = f"""
    Based on the following Google reviews, summarize what people like about the restaurant in 2 sentences, and list the top 1-2 most frequently mentioned dishes:

    {joined}
    """

    # Try each model in order until one succeeds
    for i, model in enumerate(models, 1):
        try:
            # Show progress for debugging (won't be visible to users due to spinner)
            print(f"Trying model {i}/{len(models)}: {model}")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert at summarizing restaurant reviews and identifying popular dishes. Be concise but informative."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            if hasattr(response, "choices") and response.choices:
                print(f"✅ Success with model: {model}")
                return response.choices[0].message.content.strip()
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Log which model failed (for debugging)
            print(f"❌ Model {model} failed: {str(e)}")
            
            # If this is the last model, provide fallback
            if model == models[-1]:
                if "rate limit" in error_msg or "429" in error_msg:
                    return "⚡ AI summary temporarily unavailable due to high demand. This restaurant has received positive feedback from customers for its food quality and service. Popular dishes mentioned by reviewers include their signature items and house specialties."
                elif "insufficient credits" in error_msg or "payment" in error_msg:
                    return "⚡ AI summary temporarily unavailable. Customer reviews highlight the restaurant's welcoming atmosphere and quality menu offerings. Diners frequently recommend trying their featured dishes and daily specials."
                elif "authentication" in error_msg or "api key" in error_msg:
                    return "⚡ AI summary temporarily unavailable. Based on available reviews, this establishment offers a good dining experience with varied menu options. Customers enjoy both the food quality and overall service."
                else:
                    return "⚡ AI summary currently being processed. Please check back later for detailed summaries of customer feedback and popular dishes."
            
            # Continue to next model
            continue
    
    # This should never be reached, but just in case
    return "⚡ Restaurant reviews are currently being processed. Please check back later for detailed summaries."

def get_place_photos(photo_metadata):
    photo_urls = []
    for p in photo_metadata[:5]:
        ref = p.get("photo_reference")
        if ref:
            url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={GOOGLE_API_KEY}"
            photo_urls.append(url)
    return photo_urls

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers using the Haversine formula"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance

def search_food_places(location, keywords, min_rating=0, premium_filters=None):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    places = []
    origin_coords = None
    
    for keyword in keywords:
        base_query = f"{keyword} in {location}"
        
        # Initialize basic params
        params = {
            "query": base_query,
            "key": GOOGLE_API_KEY
        }

        # First get the location coordinates using Places API instead of Geocoding API
        # This avoids the need for separate Geocoding API authorization
        geocode_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        geocode_params = {
            "input": location,
            "inputtype": "textquery",
            "fields": "geometry",
            "key": GOOGLE_API_KEY
        }
        geocode_res = requests.get(geocode_url, params=geocode_params)
        geocode_data = geocode_res.json()
        
        if geocode_data.get("candidates") and len(geocode_data["candidates"]) > 0:
            location_coords = geocode_data["candidates"][0]["geometry"]["location"]
            origin_coords = (location_coords['lat'], location_coords['lng'])
            params["location"] = f"{location_coords['lat']},{location_coords['lng']}"
            
            # Handle distance filtering properly for Google Places API
            if premium_filters and premium_filters.get("distance"):
                # Use radius instead of rankby when distance filter is active
                radius_meters = int(premium_filters["distance"] * 1000)  # Convert km to meters
                params["radius"] = min(radius_meters, 50000)  # Google Places max radius is 50km
            else:
                # Use rankby=distance for general proximity when no specific distance filter
                params["rankby"] = "distance"
        else:
            # Failed to find location, continue without distance filtering
            pass
            
        res = requests.get(url, params=params)
        data = res.json()

        if "results" in data:
            for place in data["results"][:15]:
                rating = place.get("rating")
                price_level = place.get("price_level", 0)
                geometry = place.get("geometry", {}).get("location", {})
                
                # Calculate distance if we have origin coordinates
                distance = None
                if origin_coords and geometry.get("lat") and geometry.get("lng"):
                    distance = calculate_distance(
                        origin_coords[0], origin_coords[1],
                        geometry["lat"], geometry["lng"]
                    )
                
                # Apply distance filter for premium users
                if premium_filters and premium_filters.get("distance") and distance is not None:
                    max_distance = premium_filters["distance"]
                    if distance > max_distance:
                        # Skip places that are too far
                        continue
                
                # Apply rating filter
                if rating is not None and rating < min_rating:
                    continue
                elif rating is None and min_rating > 0:
                    continue
                
                place_info = {
                    "name": place.get("name"),
                    "place_id": place.get("place_id"),
                    "rating": rating,
                    "price_level": price_level,
                    "address": place.get("formatted_address"),
                    "url": f"https://www.google.com/maps/search/?api=1&query={place.get('name').replace(' ', '+')}"
                }
                
                # Add distance information if available
                if distance is not None:
                    place_info["distance"] = f"{distance:.1f} km"
                
                places.append(place_info)
    
    # Limit to top 3 results after filtering
    return places[:3]

# --- Streamlit UI ---

# Show premium status in header
if has_premium_access():
    if st.session_state.user_premium:
        premium_badge = "🌟 PREMIUM"
    else:
        premium_badge = "🎯 TRIAL"
else:
    premium_badge = "🆓 FREE"
user_email = st.session_state.get('user_email', '')

if user_email:
    # Logged in user
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Status:** {premium_badge} | **User:** {user_email}")
    with col2:
        if st.button("🚪 Logout"):
            # Clear session
            st.session_state.clear()
            # Remove remembered user file
            try:
                os.remove('.remembered_user.txt')
            except:
                pass
            st.rerun()
else:
    # Anonymous user
    st.markdown(f"**Status:** {premium_badge} | **Mode:** Anonymous (Login for premium features)")

st.title("CraveMap: Find Food by Craving")
st.markdown("Type in what you're craving and get real nearby suggestions!")

# Sidebar with user status
with st.sidebar:
    st.markdown("### 👤 User Status")
    if has_premium_access():
        if st.session_state.user_premium:
            st.success("🌟 Premium User")
            st.markdown("✅ All features unlocked!")
        else:
            # Must be trial user
            user_id = get_user_id()
            user_data = load_user_data(user_id)
            trial_status = check_trial_status(user_data)
            days_left = trial_status['days_remaining']
            st.success("🎯 Trial User")
            st.markdown(f"✅ Premium features active!")
            st.markdown(f"⏰ {days_left} days remaining")
    else:
        # Check if user is anonymous
        if not st.session_state.get('user_email'):
            st.info("🔒 Anonymous Mode")
            
            # Get current daily usage for anonymous users (without incrementing)
            current_searches = get_current_daily_usage()
            remaining_daily = max(0, 2 - current_searches)
            
            if remaining_daily > 0:
                st.markdown(f"🔍 **{remaining_daily}** searches remaining today")
            else:
                st.markdown("🔍 **0** searches remaining today")
                st.markdown("⏰ **Resets at midnight**")
            
            st.markdown("💡 **Login for 5 monthly searches!**")
        else:
            st.info("🆓 Free User")
            remaining = 5 - st.session_state.monthly_searches
            st.markdown(f"🔍 **{remaining}** searches remaining this month")
    
    if not has_premium_access():
        st.markdown("---")
        st.markdown("### 🚀 Upgrade Benefits")
        st.markdown("""
        - 🔍 Unlimited searches
        - 🎯 Advanced filters (star rating, price range, distance control)
        - 📊 Detailed analytics and review insights
        """)
        
        # Extra warning for anonymous users
        if not st.session_state.get('user_email'):
            st.markdown("---")
            st.markdown("### ⚠️ Anonymous Limitations")
            st.markdown("""
            - Search counts may reset on page refresh
            - No cross-device sync
            - Limited session persistence
            
            **🔐 Login recommended for proper free tier experience**
            """)
    
    # Support section
    st.markdown("---")
    st.markdown("### 💬 Support")
    if st.session_state.user_premium:
        st.markdown("""
        **🌟 Premium Support:**
        ✅ Priority technical support
        ✅ Billing assistance  
        ✅ Feature requests
        
        *Use the contact form below for support*
        """)
    else:
        st.markdown("""
        **Support available for Premium users**
        
        🔒 *Upgrade to access priority support*
        """)
    
    # Debug information (development/testing only - completely hidden in production)
    app_url = get_app_url()
    is_local = "localhost" in app_url or "127.0.0.1" in app_url
    is_production = "streamlit.app" in app_url or os.getenv('STREAMLIT_CLOUD') == 'true'
    
    # Only show debug in local development, never in production
    if is_local and not is_production and st.checkbox("🔧 Show URL Debug", help="Verify Stripe redirect URLs"):
        st.markdown("---")
        st.markdown("### 🔧 Environment Debug")
        st.write(f"**Detected App URL:** {app_url}")
        st.write(f"**HOSTNAME:** {os.getenv('HOSTNAME', 'Not set')}")
        st.write(f"**STREAMLIT_CLOUD:** {os.getenv('STREAMLIT_CLOUD', 'Not set')}")
        st.write(f"**SERVER_NAME:** {os.getenv('SERVER_NAME', 'Not set')}")
        if st.session_state.get('stripe_mode'):
            st.write(f"**Stripe Mode:** {st.session_state['stripe_mode']}")

# Premium upgrade banner for free users (but not trial users)
if not has_premium_access():
    with st.container():
        st.info("🌟 **Upgrade to Premium** for unlimited searches, advanced filters (star rating, price range, distance), and detailed analytics!")

craving = st.text_input("What are you craving today?", key="search_craving", help="Type your food craving (e.g., pizza, sushi, burgers)")
location = st.text_input("Where are you? (City or Area)", placeholder="e.g. Orchard Road", key="search_location", help="Enter your location or area")

# Filter Options
st.markdown("### Filter Options")

# Premium-only advanced filters
premium_price_filter = None
premium_distance_filter = None
min_rating = 0  # Default for free users - no rating filter

if has_premium_access():
    st.markdown("#### 🌟 Premium Filters")
    
    min_rating = st.selectbox(
        "Minimum Google Star Rating:",
        options=[4.5, 4.0, 3.5, 3.0, 0],
        index=4,
        format_func=lambda x: "Any rating" if x == 0 else f"{x}+ stars"
    )
    
    premium_distance_filter = st.slider(
        "Maximum Distance (km):",
        min_value=0.5,
        max_value=10.0,
        value=5.0,
        step=0.5
    )
else:
    st.info("🔒 **Premium Feature:** Unlock advanced filters including star rating, price range, and distance controls with Premium!")

# Store premium filters in session state for use in search
st.session_state.premium_filters = {
    "distance": premium_distance_filter
}

if st.button("Find Food") and craving:
    # Get client information for spam protection
    try:
        import streamlit.web.server.server as server
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        
        # Get IP and user agent (streamlit doesn't expose these directly)
        # Use session info as fallback
        ctx = get_script_run_ctx()
        session_id = ctx.session_id if ctx else "unknown"
        user_agent = st.get_option("browser.gatherUsageStats") or "streamlit-app"
        
        # Generate fingerprint for this user
        fingerprint = spam_protection.generate_fingerprint(
            session_id, str(user_agent), st.session_state.user_email or "anonymous"
        )
        
        # Check if user is flagged
        is_flagged, flag_reason = spam_protection.is_flagged(fingerprint)
        if is_flagged:
            st.error(f"🚫 Access restricted: {flag_reason}. Please contact support if you believe this is an error.")
            st.stop()
        
        # Check rate limits
        rate_ok, rate_msg = spam_protection.check_rate_limits(fingerprint, session_id, str(user_agent))
        if not rate_ok:
            st.error(f"⏰ {rate_msg}")
            st.stop()
        
        # Check for spam patterns
        spam_ok, spam_msg = spam_protection.check_spam_patterns(craving, fingerprint, session_id, str(user_agent))
        if not spam_ok:
            st.error(f"🚫 {spam_msg}")
            st.stop()
        
        # Check for bot behavior
        bot_ok, bot_msg = spam_protection.detect_bot_behavior(fingerprint, session_id, str(user_agent))
        if not bot_ok:
            st.error(f"🤖 {bot_msg}")
            st.stop()
            
    except Exception as e:
        # If spam protection fails, log it but don't block the user
        st.warning("⚠️ Security check encountered an issue. Proceeding with search...")
    
    # Check search limits for free users  
    if not check_search_limits():
        st.stop()
    
    keywords = [craving.strip()]
    st.write(f"### Searching for: {craving.strip()}")
    
    # Show filter info
    if min_rating > 0:
        st.write(f"**Filter:** Showing places with {min_rating}+ star rating")

    with st.spinner("Searching for places..."):
        # Pass premium filters to search function
        premium_filters = st.session_state.get('premium_filters', {}) if has_premium_access() else None
        places = search_food_places(location, keywords, min_rating, premium_filters)

    if places:
        st.success(f"Found {len(places)} suggestion(s)!")
        
        for idx, place in enumerate(places):
            st.markdown(f"## {place['name']}")
            
            # Basic info for all users
            rating_display = f"⭐ {place.get('rating', 'N/A')}"
            
            # Premium users get detailed analytics including distance
            if has_premium_access():
                price_level = place.get('price_level', 0)
                price_display = "$" * max(1, price_level) if price_level > 0 else "$ (Budget-friendly)"
                st.markdown(f"""
                **Premium Analytics:**
                - **Rating:** {rating_display} 
                - **Price Level:** {price_display}
                - **Distance:** {place.get('distance', 'N/A')}
                - **Address:** {place['address']}
                - **Popularity Rank:** #{idx + 1} in search results
                """)
            else:
                st.markdown(f"{rating_display}\n\n📍 {place['address']}")
            
            st.markdown(f"[🔗 View on Google Maps]({place['url']})")

            # Get place details
            details = get_place_details(place['place_id'])
            result = details.get("result", {})

            if "reviews" in result:
                reviews = result["reviews"]
                try:
                    with st.spinner("🤖 Generating AI summary from reviews..."):
                        summary = summarize_reviews_and_dishes(reviews)
                    if summary:
                        st.markdown(f"""**What people say:**  
                    {summary}""")
                except Exception as e:
                    # If summarization fails, show a simple fallback
                    st.markdown(f"""**What people say:**  
                    This restaurant has {len(reviews)} customer reviews. Check individual reviews below for detailed feedback about food quality, service, and atmosphere.""")
                
                # Premium users get detailed review analytics
                if has_premium_access() and reviews:
                    with st.expander("📊 Premium Review Analytics"):
                        total_reviews = len(reviews)
                        avg_rating = sum(r.get('rating', 0) for r in reviews) / len(reviews) if reviews else 0
                        recent_reviews = [r for r in reviews if 'time' in r]
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Reviews", total_reviews)
                        with col2:
                            st.metric("Avg Rating", f"{avg_rating:.1f}⭐")
                        with col3:
                            st.metric("Recent Activity", f"{len(recent_reviews)} recent")
                        
                        # Sentiment analysis
                        positive_words = sum(1 for r in reviews if any(word in r.get('text', '').lower() 
                                           for word in ['great', 'excellent', 'amazing', 'love', 'perfect', 'delicious']))
                        sentiment_score = positive_words / len(reviews) * 100 if reviews else 0
                        st.progress(sentiment_score / 100)
                        st.write(f"Positive Sentiment: {sentiment_score:.0f}%")

            if "photos" in result:
                st.markdown("**Reviewer-uploaded photos (not dish-specific):**")
                photo_urls = get_place_photos(result["photos"])
                cols = st.columns(3)
                for idx_photo, url in enumerate(photo_urls):
                    with cols[idx_photo % 3]:
                        st.image(url, use_container_width=True)
            
            # Add some spacing between results
            st.write("")
    else:
        if min_rating > 0:
            st.warning(f"No places found with {min_rating}+ star rating. Try lowering the rating filter, rephrasing your craving, or changing your location.")
        else:
            st.warning("No matching places found. Try rephrasing your craving or changing your location.")

st.write("")

# Premium upgrade section
if not st.session_state.user_premium:
    st.markdown("## 🌟 Upgrade to CraveMap Premium")

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Free Plan
        - ✅ Basic restaurant search
        - ✅ 3 searches per month
        - ✅ Basic reviews and photos
        - ❌ Advanced filters
        - ❌ Detailed analytics
        """)
    
    with col2:
        st.markdown(f"""
        ### Premium Plan - {PREMIUM_PRICE_DISPLAY}/month
        - ✅ Everything in Free
        - ✅ **Unlimited searches**
        - ✅ **Advanced filters** (star rating, price range, distance control)
        - ✅ **Detailed analytics** and review insights
        """)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        # Check if user is logged in for premium upgrade
        user_email = st.session_state.get('user_email', '')
        if not user_email:
            st.warning("🔐 **Login required** to upgrade to Premium")
            st.info("👆 Please login using the sidebar to access premium features")
        else:
            # User is logged in, show upgrade button
            if st.button(f"🚀 Upgrade to Premium - {PREMIUM_PRICE_DISPLAY}/month", type="primary"):
                with st.spinner("🔒 Creating secure checkout..."):
                    checkout_url = create_stripe_checkout_session()
                    
                if checkout_url:
                    st.success("✅ Checkout session created!")
                    st.markdown(f"""
                    ### 🔒 Secure Payment
                    
                    🔗 **[CLICK HERE TO PAY WITH STRIPE - {PREMIUM_PRICE_DISPLAY}/month]({checkout_url})**
                    
                    You'll be redirected to Stripe's secure payment page to complete your purchase.
                    """)
                
                # Show test card details only in test mode
                if st.session_state.get('stripe_mode', 'test') == "test":
                    st.markdown("""
                    ℹ️ **Test Mode Card Details:**
                    - Card number: 4242 4242 4242 4242
                    - Expiry: Any future date (e.g., 12/25)
                    - CVC: Any 3 digits
                    - Name/Address: Any values
                    """)
                
                st.info("💡 **Tip:** After payment, return to this page to access your premium features.")
        
        st.markdown("*🔒 Powered by Stripe | 💳 All major cards accepted | 🛡️ PCI compliant*")
    
    # Admin diagnostic tool (activated by session state)
    if st.session_state.get('diagnostic_mode', False):
        st.markdown("---")
        st.markdown("### 🔍 User Search & Debug Tool")
        search_email = st.text_input("Enter email to search:", key="diagnostic_search_email", placeholder="e.g., user@example.com")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Search User", type="primary", key="diagnostic_search_btn"):
                if not search_email:
                    st.warning("Please enter an email address to search")
                else:
                    import glob
                    found = False
                    st.info(f"Searching for: {search_email}")
                    
                    for filename in glob.glob('.user_data_*.json'):
                        if 'anon' not in filename:
                            try:
                                with open(filename, 'r') as f:
                                    data = json.load(f)
                                if search_email.lower() in data.get('email', '').lower():
                                    st.success(f"✅ Found user in {filename}")
                                    
                                    # Show user data in organized way
                                    col_a, col_b = st.columns(2)
                                    with col_a:
                                        st.markdown("**📧 User Information:**")
                                        st.write(f"- Email: {data.get('email', 'N/A')}")
                                        st.write(f"- User ID: {data.get('user_id', 'N/A')}")
                                        st.write(f"- Premium Status: {'✅ Premium' if data.get('is_premium', False) else '❌ Free'}")
                                        st.write(f"- Premium Since: {data.get('premium_since', 'N/A')}")
                                    
                                    with col_b:
                                        st.markdown("**🔍 Validation Results:**")
                                        validation_result = check_subscription_status(data)
                                        st.write(f"- Subscription Valid: {'✅ Yes' if validation_result else '❌ No'}")
                                        st.write(f"- Has Promo Code: {'✅ Yes' if data.get('promo_activation') else '❌ No'}")
                                        if data.get('promo_activation'):
                                            st.write(f"- Promo Details: {data.get('promo_activation')}")
                                    
                                    # Show full data in expandable section
                                    with st.expander("📋 Full User Data (JSON)"):
                                        st.json(data)
                                    
                                    found = True
                                    break
                            except Exception as e:
                                continue
                    
                    if not found:
                        st.error(f"❌ User '{search_email}' not found in any user data files")
                        st.info("💡 Try checking for typos or different email variations")
        
        with col2:
            if st.button("❌ Close Diagnostic Tool", key="close_diagnostic"):
                st.session_state.diagnostic_mode = False
                st.rerun()
        
        st.markdown("---")
    
    # Hidden admin controls (secret access for you)
    with st.expander("🔐 Have a promo code?"):
        promo_code = st.text_input("Enter promo code:", key="promo_code_input", help="Enter your promotional code")
        if st.button("Apply Code"):
            if promo_code == ADMIN_UPGRADE_CODE:
                # Check if user is logged in for premium upgrade
                if not st.session_state.get('user_email'):
                    st.warning("🔐 Please login first to apply premium promo code")
                    st.stop()
                
                # Get the correct user ID after login check
                user_id = get_user_id()
                user_email = st.session_state.get('user_email', '')
                
                st.info(f"🔍 Upgrading user: {user_email} (ID: {user_id})")
                
                # Update session state
                st.session_state.user_premium = True
                st.session_state.payment_completed = True
                
                # Update usage data in database
                user_data = load_user_data(user_id)
                
                upgrade_data = {
                    'email': user_email,
                    'is_premium': True,
                    'payment_completed': True,
                    'monthly_searches': user_data.get('monthly_searches', 0),
                    'last_search_reset': user_data.get('last_search_reset', datetime.now().isoformat()),
                    'premium_since': datetime.now().isoformat(),
                    'promo_activation': f"Admin code: {promo_code}",
                    'user_id': user_id
                }
                
                # Save with detailed logging
                try:
                    save_user_data(user_id, upgrade_data)
                    st.success(f"✅ Data saved for user ID: {user_id}")
                    
                    # Immediately verify the save worked
                    verification_data = load_user_data(user_id)
                    if verification_data.get('is_premium'):
                        st.success("✅ Premium status verified in saved data")
                    else:
                        st.error("❌ Premium status NOT found in saved data - save failed!")
                        
                    # Log the save operation
                    with open('.upgrade_log.txt', 'a') as f:
                        f.write(f"{datetime.now().isoformat()}: Upgraded {user_email} (ID: {user_id}) to premium\n")
                        
                except Exception as e:
                    st.error(f"❌ Save failed: {str(e)}")
                
                st.success("🎉 Admin code applied! Premium activated!")
                st.rerun()
            elif promo_code == ADMIN_DOWNGRADE_CODE:
                # Get current user ID
                user_id = get_user_id()
                
                # Update session state
                st.session_state.user_premium = False
                st.session_state.payment_completed = False
                
                # Update usage data file
                usage_data = load_user_data(user_id)
                usage_data['is_premium'] = False
                usage_data['premium_since'] = None
                usage_data['downgrade_reason'] = f"Admin code: {promo_code}"
                save_user_data(user_id, usage_data)
                
                st.info("Reset to free tier")
                st.rerun()
            elif promo_code == TRIAL_CODE:
                # Check if user is logged in for trial activation
                if not st.session_state.get('user_email'):
                    st.warning("🔐 Please login first to activate trial")
                    st.stop()
                
                # Get the correct user ID after login check
                user_id = get_user_id()
                
                # Check if user already has an active trial or is premium
                usage_data = load_user_data(user_id)
                if usage_data.get('is_premium'):
                    st.info("🎉 You already have premium access!")
                    st.stop()
                
                # Check if user already used a trial
                if usage_data.get('trial_used'):
                    st.warning("⏰ You have already used your free trial")
                    st.stop()
                
                # Activate 7-day trial
                trial_start = datetime.now()
                trial_end = trial_start + timedelta(days=TRIAL_DURATION_DAYS)
                
                # Update session state
                st.session_state.trial_active = True
                st.session_state.trial_start_date = trial_start.isoformat()
                st.session_state.trial_end_date = trial_end.isoformat()
                st.session_state.trial_daily_searches = 0
                
                # Update usage data file
                save_user_data(user_id, {
                    'trial_active': True,
                    'trial_start_date': trial_start.isoformat(),
                    'trial_end_date': trial_end.isoformat(),
                    'trial_daily_searches': 0,
                    'trial_used': True,
                    'monthly_searches': usage_data.get('monthly_searches', 0),
                    'last_search_reset': usage_data.get('last_search_reset', datetime.now().isoformat()),
                    'is_premium': usage_data.get('is_premium', False),
                    'premium_since': usage_data.get('premium_since'),
                    'trial_activation': f"Trial activated: {trial_start.isoformat()}",
                    'user_id': user_id
                })
                
                st.success(f"🎉 7-day trial activated! You now have {TRIAL_DAILY_LIMIT} searches per day until {trial_end.strftime('%B %d, %Y')}")
                st.rerun()
            elif promo_code == ADMIN_RESET_COUNTER:
                # Get current user ID
                user_id = get_user_id()
                
                st.session_state.monthly_searches = 0
                save_user_data(user_id, {
                    'monthly_searches': 0,
                    'last_search_reset': st.session_state.last_search_reset,
                    'is_premium': st.session_state.user_premium,
                    'premium_since': usage_data.get('premium_since'),
                    'user_id': user_id
                })
                st.success("🔄 Search counter reset to 0!")
                st.rerun()
            elif promo_code == "viewlogs":
                # Admin function to view subscription logs
                try:
                    with open('.subscription_log.txt', 'r') as f:
                        logs = f.read()
                    if logs:
                        st.text_area("📋 Subscription Management Logs", logs, height=200)
                    else:
                        st.info("No subscription management logs yet")
                except FileNotFoundError:
                    st.info("No subscription management logs yet")
            elif promo_code == "finduser":
                # Admin function to find and debug user data
                st.session_state.diagnostic_mode = True
                st.rerun()
            elif promo_code == "finduserhelp":
                st.markdown("### 🔍 User Search Instructions")
                st.info("1. Enter 'finduser' as promo code and click Apply\n2. Then enter email address to search")
            elif promo_code == "testpersist":
                # Test file persistence in production
                import time
                test_data = {
                    "test_time": datetime.now().isoformat(),
                    "test_message": "File persistence test",
                    "app_restart_test": True
                }
                
                try:
                    # Write test file
                    with open('.persistence_test.json', 'w') as f:
                        json.dump(test_data, f, indent=2)
                    st.success("✅ Test file written successfully")
                    
                    # Try to read it back immediately
                    with open('.persistence_test.json', 'r') as f:
                        read_data = json.load(f)
                    st.success("✅ Test file read back successfully")
                    st.json(read_data)
                    
                    # Show current directory and files
                    import os
                    st.write(f"**Current directory:** {os.getcwd()}")
                    user_files = [f for f in os.listdir('.') if f.startswith('.user_data_')]
                    st.write(f"**User data files found:** {len(user_files)}")
                    for f in user_files[:5]:  # Show first 5
                        st.write(f"- {f}")
                        
                except Exception as e:
                    st.error(f"❌ File persistence test failed: {str(e)}")
            elif promo_code == "debuguser":
                # Alternative command for user debugging
                st.markdown("### 🔍 User Search & Debug Tool")
                search_email = st.text_input("Enter email to search:", key="debug_search_email", placeholder="e.g., user@example.com")
                
                if st.button("🔍 Search User Now", type="primary", key="debug_search_btn"):
                    if not search_email:
                        st.warning("Please enter an email address to search")
                    else:
                        import glob
                        found = False
                        st.info(f"Searching for: {search_email}")
                        
                        for filename in glob.glob('.user_data_*.json'):
                            if 'anon' not in filename:
                                try:
                                    with open(filename, 'r') as f:
                                        data = json.load(f)
                                    if search_email.lower() in data.get('email', '').lower():
                                        st.success(f"✅ Found user in {filename}")
                                        
                                        # Show user data in organized way
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.markdown("**📧 User Information:**")
                                            st.write(f"- Email: {data.get('email', 'N/A')}")
                                            st.write(f"- User ID: {data.get('user_id', 'N/A')}")
                                            st.write(f"- Premium Status: {'✅ Premium' if data.get('is_premium', False) else '❌ Free'}")
                                            st.write(f"- Premium Since: {data.get('premium_since', 'N/A')}")
                                        
                                        with col2:
                                            st.markdown("**🔍 Validation Results:**")
                                            validation_result = check_subscription_status(data)
                                            st.write(f"- Subscription Valid: {'✅ Yes' if validation_result else '❌ No'}")
                                            st.write(f"- Has Promo Code: {'✅ Yes' if data.get('promo_activation') else '❌ No'}")
                                            if data.get('promo_activation'):
                                                st.write(f"- Promo Details: {data.get('promo_activation')}")
                                        
                                        # Show full data in expandable section
                                        with st.expander("📋 Full User Data (JSON)"):
                                            st.json(data)
                                        
                                        found = True
                                        break
                                except Exception as e:
                                    continue
                        
                        if not found:
                            st.error(f"❌ User '{search_email}' not found in any user data files")
                            st.info("💡 Try checking for typos or different email variations")
            elif promo_code == "viewsupport":
                # Admin function to view support requests from database
                support_requests = db.get_support_tickets(limit=10)
                if support_requests:
                    st.markdown("### 📨 Support Requests")
                    for request in support_requests:
                        with st.expander(f"{request['support_type']}: {request['subject']} - {request['created_at'][:10]}"):
                            st.write(f"**User:** {request['user_email']}")
                            st.write(f"**Type:** {request['support_type']}")
                            st.write(f"**Time:** {request['created_at']}")
                            st.write(f"**Subject:** {request['subject']}")
                            st.write(f"**Message:** {request['message']}")
                            st.write(f"**User ID:** {request['user_id']}")
                            st.write(f"**Status:** {request['status']}")
                else:
                    st.info("No support requests yet")
            elif promo_code == "dbstats":
                # Admin function to view database statistics
                stats = db.get_stats()
                st.markdown("### 📊 Database Statistics")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Users", stats['total_users'])
                    st.metric("Premium Users", stats['premium_users'])
                with col2:
                    st.metric("Paid Users", stats['paid_users'])
                    st.metric("Support Tickets", stats['total_tickets'])
                
                # Show conversion rate
                if stats['total_users'] > 0:
                    conversion_rate = (stats['premium_users'] / stats['total_users']) * 100
                    st.metric("Conversion Rate", f"{conversion_rate:.1f}%")
                
                # Spam Protection Statistics
                st.markdown("### 🛡️ Spam Protection Stats")
                spam_stats = spam_protection.get_admin_stats()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Requests (24h)", spam_stats['total_requests_24h'])
                with col2:
                    st.metric("Flagged Users", spam_stats['flagged_users'])
                with col3:
                    st.metric("Suspicious Activities", spam_stats['suspicious_activities_24h'])
                with col4:
                    st.metric("High Severity", spam_stats['high_severity_24h'])
                
                # Activity breakdown
                if spam_stats['activity_breakdown']:
                    st.markdown("#### Recent Suspicious Activities")
                    for activity in spam_stats['activity_breakdown']:
                        st.write(f"• **{activity['activity_type']}**: {activity['count']} times")
                
                # Manual backup option
                if st.button("🔄 Create Manual Backup"):
                    backup_file = simple_file_backup()
                    if backup_file:
                        st.success(f"✅ Backup created: {backup_file}")
                    else:
                        st.error("❌ Backup failed")
            elif promo_code == "backup":
                # Quick backup command
                st.markdown("### 💾 Database Backup")
                backup_file = simple_file_backup()
                if backup_file:
                    st.success(f"✅ Backup created: {backup_file}")
                    # Show backup files
                    backup_files = [f for f in os.listdir('.') if f.startswith('backup_') and f.endswith('.json')]
                    if backup_files:
                        st.markdown("**Available Backups:**")
                        for backup in sorted(backup_files, reverse=True)[:5]:  # Show last 5 backups
                            backup_time = backup.replace('backup_', '').replace('.json', '')
                            st.write(f"- {backup} ({backup_time})")
                else:
                    st.error("❌ Backup failed")
            elif promo_code == "forcecheckall":
                # Force immediate subscription check (bypasses 6-hour limit)
                try:
                    import os
                    os.remove('.last_subscription_check.txt')
                except:
                    pass
                auto_check_all_subscriptions()
                st.success("🔍 Forced subscription check completed")
            elif promo_code:
                st.error("Invalid promo code")
else:
    st.success("🎉 You're a Premium user! Enjoy unlimited features!")
    if st.session_state.payment_completed:
        st.info(f"💳 Subscription active - {PREMIUM_PRICE_DISPLAY}/month")
    
    # Show subscription details for premium users
    user_data = load_user_data(get_user_id())
    if user_data.get('premium_since'):
        try:
            premium_date = datetime.fromisoformat(user_data['premium_since'])
            days_premium = (datetime.now() - premium_date).days
            
            with st.expander("📊 Subscription Details"):
                st.write(f"**Premium since:** {premium_date.strftime('%B %d, %Y')}")
                st.write(f"**Days active:** {days_premium}")
                
                if user_data.get('stripe_subscription_id'):
                    st.write(f"**Subscription ID:** {user_data['stripe_subscription_id'][:8]}...")
                    
                    # Check subscription status
                    try:
                        subscription = stripe.Subscription.retrieve(user_data['stripe_subscription_id'])
                        status_emoji = {"active": "✅", "trialing": "🆓", "past_due": "⚠️", "canceled": "❌"}.get(subscription.status, "❓")
                        st.write(f"**Status:** {status_emoji} {subscription.status.title()}")
                        
                        if subscription.status == "past_due":
                            st.warning("⚠️ Payment failed. Please update your payment method or your premium access may be revoked.")
                        elif subscription.status == "canceled":
                            st.error("❌ Subscription canceled. Premium access will be revoked soon.")
                            
                    except stripe.error.StripeError:
                        st.write("**Status:** ❓ Unable to verify with Stripe")
                else:
                    st.write("**Type:** Admin/Manual activation")
                
                # Premium Support Contact Form
                st.markdown("---")
                st.markdown("**💬 Premium Support:**")
                st.markdown("*Submit a support request below*")
                    
        except (ValueError, TypeError):
            pass

# Footer with legal links and contact
st.markdown("---")

if st.session_state.user_premium:
    # Premium users get 2 columns for legal links + dedicated support section
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 Privacy Policy"):
            with st.expander("Privacy Policy", expanded=True):
                st.markdown(PRIVACY_POLICY)

    with col2:
        if st.button("📜 Terms of Service"):
            with st.expander("Terms of Service", expanded=True):
                st.markdown(TERMS_OF_SERVICE)
    
    # Premium Support Form (always visible for premium users)
    st.markdown("### 💬 Premium Support")
    st.markdown("*Get priority support for technical issues, billing questions, and feature requests*")
    
    with st.form("premium_support_form", clear_on_submit=True):
        support_type = st.selectbox("Support Type", [
            "Technical Issue",
            "Billing Question", 
            "Feature Request",
            "Bug Report",
            "Other"
        ])
        
        subject = st.text_input("Subject", placeholder="Brief description of your issue")
        message = st.text_area("Message", placeholder="Please provide details about your request...", height=100)
        
        if st.form_submit_button("📤 Send Support Request"):
            if subject and message:
                print(f"Processing support request from: {st.session_state.get('user_email', 'Unknown')}")
                
                # Create support data
                support_data = {
                    "timestamp": datetime.now().isoformat(),
                    "user_email": st.session_state.get('user_email', 'Unknown'),
                    "user_id": get_user_id(),
                    "support_type": support_type,
                    "subject": subject,
                    "message": message
                }
                
                print(f"Support data created: {support_data}")
                
                # Try to send email first
                email_sent = send_support_email(support_data)
                print(f"Email sent result: {email_sent}")
                
                # Save to database (primary) and file (backup)
                try:
                    # Save to database
                    db.save_support_ticket(
                        user_id=support_data['user_id'],
                        user_email=support_data['user_email'],
                        support_type=support_data['support_type'],
                        subject=support_data['subject'],
                        message=support_data['message'],
                        created_at=support_data['timestamp']
                    )
                    print("Support request saved to database")
                    
                    # Also save to file as backup
                    support_file = ".support_requests.json"
                    if os.path.exists(support_file):
                        with open(support_file, 'r') as f:
                            requests_data = json.load(f)
                    else:
                        requests_data = []
                    
                    requests_data.append(support_data)
                    
                    with open(support_file, 'w') as f:
                        json.dump(requests_data, f, indent=2)
                    
                    print("Support request also saved to local file as backup")
                    
                    # Show success message
                    if email_sent:
                        st.success("✅ Support request sent successfully!")
                        st.info("📧 Your request has been emailed and you'll receive a response soon.")
                    else:
                        st.success("✅ Support request submitted successfully!")
                        st.info("📝 Your request has been logged and you'll receive a response soon.")
                        st.warning("⚠️ Email delivery failed, but your request was saved.")
                    
                except Exception as e:
                    print(f"Error saving support request: {e}")
                    if email_sent:
                        st.success("✅ Support request sent via email!")
                        st.info("📧 You'll receive a response soon.")
                    else:
                        st.error("❌ Error submitting request. Please try again.")
                        st.error(f"Error details: {str(e)}")
            else:
                st.error("Please fill in both subject and message fields.")
else:
    # Free users get 2 columns without contact support
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 Privacy Policy"):
            with st.expander("Privacy Policy", expanded=True):
                st.markdown(PRIVACY_POLICY)

    with col2:
        if st.button("📜 Terms of Service"):
            with st.expander("Terms of Service", expanded=True):
                st.markdown(TERMS_OF_SERVICE)

st.markdown("Want to support this app? [Buy me a coffee ☕](https://www.buymeacoffee.com/alvincheong)")
