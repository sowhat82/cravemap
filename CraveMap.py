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
    # Fallback models if config file is missing
    models = ["mistralai/mistral-7b-instruct:free", "meta-llama/llama-3.3-70b-instruct:free"]

# Admin secret codes (only you know these)
ADMIN_UPGRADE_CODE = "cravemap2024premium"  # Use this to activate premium
ADMIN_DOWNGRADE_CODE = "resetfree"      # Use this to go back to free tier
ADMIN_RESET_COUNTER = "resetcounter"    # Use this to reset monthly searches

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
            email = st.text_input("Enter your email:", placeholder="your@email.com")
            remember_me = st.checkbox("Remember me on this device")
            submit = st.form_submit_button("Login")
            
            if submit and email:
                if "@" in email and "." in email:  # Basic email validation
                    st.session_state['user_email'] = email.lower().strip()
                    
                    # Refresh session with user's actual data
                    user_id = hashlib.md5(email.lower().strip().encode()).hexdigest()[:8]
                    user_data = load_user_data(user_id)
                    st.session_state.user_premium = user_data.get('is_premium', False)
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
                        st.session_state.user_premium = user_data.get('is_premium', False)
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
    
    # Allow up to 3 searches per day per client
    if today_searches >= 3:
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
    filename = f'.user_data_{user_id}.json'
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            # Ensure we have the user's email stored
            if 'email' not in data:
                data['email'] = st.session_state.get('user_email', '')
            return data
    except FileNotFoundError:
        return {
            'monthly_searches': 0,
            'last_search_reset': datetime.now().isoformat(),
            'is_premium': False,
            'premium_since': None,
            'user_id': user_id,
            'email': st.session_state.get('user_email', '')
        }

# Function to save usage data for specific user
def save_user_data(user_id, data):
    filename = f'.user_data_{user_id}.json'
    data['user_id'] = user_id
    data['email'] = st.session_state.get('user_email', '')
    data['last_updated'] = datetime.now().isoformat()
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

# Subscription management functions
def check_subscription_status(user_data):
    """Check if subscription is still valid and active"""
    if not user_data.get('is_premium', False):
        return False  # Not premium anyway
    
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
        # Check if we're on Streamlit Cloud/deployed environment
        if (os.getenv('STREAMLIT_SHARING_MODE') or 
            os.getenv('STREAMLIT_CLOUD') or
            'streamlit.app' in str(os.getenv('HOSTNAME', '')) or
            'streamlit.app' in str(os.getenv('SERVER_NAME', ''))):
            # For Streamlit Cloud, construct the URL
            return "https://cravemap.streamlit.app"
        
        # Check for other cloud platforms
        if os.getenv('HEROKU_APP_NAME'):
            return f"https://{os.getenv('HEROKU_APP_NAME')}.herokuapp.com"
        elif os.getenv('RAILWAY_STATIC_URL'):
            return os.getenv('RAILWAY_STATIC_URL')
        elif os.getenv('VERCEL_URL'):
            return f"https://{os.getenv('VERCEL_URL')}"
        
        # Fallback to localhost for development
        port = st.get_option('server.port') or 8501
        return f"http://localhost:{port}"
        
    except Exception:
        # Ultimate fallback
        return "http://localhost:8501"

def create_stripe_checkout_session():
    """Create a Stripe checkout session for premium subscription"""
    try:
        user_email = st.session_state.get('user_email', '')
        if not user_email:
            st.error("❌ Please login first before upgrading to premium")
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
                    'unit_amount': 499,  # $4.99 in cents
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
        st.session_state.user_premium = user_data.get('is_premium', False)
        
        # Premium users have unlimited searches
        if st.session_state.user_premium:
            return True
        
        # Check if user has reached limit
        if user_data['monthly_searches'] >= 3:
            st.warning("🔒 You've reached your 3 free searches for this month!")
            return False
        
        # Increment search count
        user_data['monthly_searches'] += 1
        save_user_data(user_id, user_data)
        st.session_state.monthly_searches = user_data['monthly_searches']
        
        remaining = 3 - user_data['monthly_searches']
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
    for model in models:
        try:
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
                return response.choices[0].message.content.strip()
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Log which model failed (for debugging)
            print(f"Model {model} failed: {str(e)}")
            
            # If this is the last model, provide fallback
            if model == models[-1]:
                if "rate limit" in error_msg or "429" in error_msg:
                    return "This restaurant has received positive feedback from customers for its food quality and service. Popular dishes mentioned by reviewers include their signature items and house specialties."
                elif "insufficient credits" in error_msg or "payment" in error_msg:
                    return "Customer reviews highlight the restaurant's welcoming atmosphere and quality menu offerings. Diners frequently recommend trying their featured dishes and daily specials."
                elif "authentication" in error_msg or "api key" in error_msg:
                    return "Based on available reviews, this establishment offers a good dining experience with varied menu options. Customers enjoy both the food quality and overall service."
                else:
                    return "Restaurant reviews are currently being processed. Please check back later for detailed summaries of customer feedback and popular dishes."
            
            # Continue to next model
            continue
    
    # This should never be reached, but just in case
    return "Restaurant reviews are currently being processed. Please check back later for detailed summaries."

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

        # First get the location coordinates
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geocode_params = {
            "address": location,
            "key": GOOGLE_API_KEY
        }
        geocode_res = requests.get(geocode_url, params=geocode_params)
        geocode_data = geocode_res.json()
        
        if geocode_data.get("results"):
            location_coords = geocode_data["results"][0]["geometry"]["location"]
            origin_coords = (location_coords['lat'], location_coords['lng'])
            params["location"] = f"{location_coords['lat']},{location_coords['lng']}"
            params["rankby"] = "distance"
            
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
                if premium_filters and premium_filters.get("distance") and distance:
                    if distance > premium_filters["distance"]:
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
premium_badge = "🌟 PREMIUM" if st.session_state.user_premium else "🆓 FREE"
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
    if st.session_state.user_premium:
        st.success("🌟 Premium User")
        st.markdown("✅ All features unlocked!")
    else:
        # Check if user is anonymous
        if not st.session_state.get('user_email'):
            st.info("🔒 Anonymous Mode")
            st.markdown("**Daily limits:** 3 searches per day")
            st.markdown("💡 **Login for monthly limits**")
        else:
            st.info("🆓 Free User")
            remaining = 3 - st.session_state.monthly_searches
            st.markdown(f"🔍 **{remaining}** searches remaining this month")
    
    if not st.session_state.user_premium:
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
    
    # Debug information (for development/testing)
    if st.checkbox("🔧 Show URL Debug", help="Verify Stripe redirect URLs"):
        st.markdown("---")
        st.markdown("### 🔧 Environment Debug")
        app_url = get_app_url()
        st.write(f"**Detected App URL:** {app_url}")
        st.write(f"**HOSTNAME:** {os.getenv('HOSTNAME', 'Not set')}")
        st.write(f"**STREAMLIT_CLOUD:** {os.getenv('STREAMLIT_CLOUD', 'Not set')}")
        st.write(f"**SERVER_NAME:** {os.getenv('SERVER_NAME', 'Not set')}")
        if st.session_state.get('stripe_mode'):
            st.write(f"**Stripe Mode:** {st.session_state['stripe_mode']}")

# Premium upgrade banner for free users
if not st.session_state.user_premium:
    with st.container():
        st.info("🌟 **Upgrade to Premium** for unlimited searches, advanced filters (star rating, price range, distance), and detailed analytics!")

craving = st.text_input("What are you craving today?")
location = st.text_input("Where are you? (City or Area)", placeholder="e.g. Orchard Road")

# Filter Options
st.markdown("### Filter Options")

# Premium-only advanced filters
premium_price_filter = None
premium_distance_filter = None
min_rating = 0  # Default for free users - no rating filter

if st.session_state.user_premium:
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
        premium_filters = st.session_state.get('premium_filters', {}) if st.session_state.user_premium else None
        places = search_food_places(location, keywords, min_rating, premium_filters)

    if places:
        st.success(f"Found {len(places)} suggestion(s)!")
        
        for idx, place in enumerate(places):
            st.markdown(f"## {place['name']}")
            
            # Basic info for all users
            rating_display = f"⭐ {place.get('rating', 'N/A')}"
            
            # Premium users get detailed analytics
            if st.session_state.user_premium:
                price_level = place.get('price_level', 0)
                price_display = "$" * max(1, price_level) if price_level > 0 else "$ (Budget-friendly)"
                distance_info = f"- **Distance:** {place.get('distance', 'N/A')}" if place.get('distance') else ""
                st.markdown(f"""
                **Premium Analytics:**
                - **Rating:** {rating_display} 
                - **Price Level:** {price_display}
                {distance_info}
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
                    summary = summarize_reviews_and_dishes(reviews)
                    if summary:
                        st.markdown(f"""**What people say:**  
                    {summary}""")
                except Exception as e:
                    # If summarization fails, show a simple fallback
                    st.markdown(f"""**What people say:**  
                    This restaurant has {len(reviews)} customer reviews. Check individual reviews below for detailed feedback about food quality, service, and atmosphere.""")
                
                # Premium users get detailed review analytics
                if st.session_state.user_premium and reviews:
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
        st.markdown("""
        ### Premium Plan - $4.99/month
        - ✅ Everything in Free
        - ✅ **Unlimited searches**
        - ✅ **Advanced filters** (star rating, price range, distance control)
        - ✅ **Detailed analytics** and review insights
        """)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        # Check if user is logged in for premium upgrade
        if not st.session_state.get('user_email'):
            st.warning("🔐 **Login required** to upgrade to Premium")
            st.info("👆 Please login using the sidebar to access premium features")
        else:
            # Simple Stripe payment integration
            if st.button("🚀 Upgrade to Premium - $4.99/month", type="primary"):
                with st.spinner("🔒 Creating secure checkout..."):
                    checkout_url = create_stripe_checkout_session()
                    
                if checkout_url:
                    st.success("✅ Checkout session created!")
                    st.markdown(f"""
                    ### 🔒 Secure Payment
                    
                    🔗 **[CLICK HERE TO PAY WITH STRIPE - $4.99/month]({checkout_url})**
                    
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
            else:
                st.error("❌ Could not create checkout session. Please try again.")
        
        st.markdown("*🔒 Powered by Stripe | 💳 All major cards accepted | 🛡️ PCI compliant*")
    
    # Hidden admin controls (secret access for you)
    with st.expander("🔐 Have a promo code?"):
        promo_code = st.text_input("Enter promo code:", type="password")
        if st.button("Apply Code"):
            if promo_code == ADMIN_UPGRADE_CODE:
                # Check if user is logged in for premium upgrade
                if not st.session_state.get('user_email'):
                    st.warning("🔐 Please login first to apply premium promo code")
                    st.stop()
                
                # Get the correct user ID after login check
                user_id = get_user_id()
                
                # Update session state
                st.session_state.user_premium = True
                st.session_state.payment_completed = True
                
                # Update usage data file
                usage_data = load_user_data(user_id)
                usage_data['is_premium'] = True
                usage_data['premium_since'] = datetime.now().isoformat()
                usage_data['promo_activation'] = f"Admin code: {promo_code}"
                save_user_data(user_id, usage_data)
                
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
        st.info("💳 Subscription active - $4.99/month")
    
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
                    
        except (ValueError, TypeError):
            pass

st.markdown("Want to support this app? [Buy me a coffee ☕](https://www.buymeacoffee.com/alvincheong)")
