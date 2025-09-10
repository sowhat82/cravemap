from urllib import response
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

# Set page config
st.set_page_config(
    page_title="CraveMap: Find Food by Craving",
    page_icon="🍕"
)

# Load environment variables from .env file (for local development)
load_dotenv()

# Admin secret codes (only you know these)
ADMIN_UPGRADE_CODE = "cravemap2024premium"  # Use this to activate premium
ADMIN_DOWNGRADE_CODE = "resetfree"      # Use this to go back to free tier
ADMIN_RESET_COUNTER = "resetcounter"    # Use this to reset monthly searches

# Generate unique user ID for this session
def get_user_id():
    if 'user_id' not in st.session_state:
        # Create unique ID based on session + timestamp
        import uuid
        st.session_state['user_id'] = str(uuid.uuid4())[:8]
    return st.session_state['user_id']

# Function to load usage data for specific user
def load_user_data(user_id):
    filename = f'.user_data_{user_id}.json'
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'monthly_searches': 0,
            'last_search_reset': datetime.now().isoformat(),
            'is_premium': False,
            'premium_since': None,
            'user_id': user_id
        }

# Function to save usage data for specific user
def save_user_data(user_id, data):
    filename = f'.user_data_{user_id}.json'
    data['user_id'] = user_id
    with open(filename, 'w') as f:
        json.dump(data, f)

# Get current user ID and load their data
current_user_id = get_user_id()
usage_data = load_user_data(current_user_id)

# Initialize session state
if 'user_premium' not in st.session_state:
    st.session_state.user_premium = usage_data.get('is_premium', False)
if 'payment_completed' not in st.session_state:
    st.session_state.payment_completed = False

st.session_state.monthly_searches = usage_data['monthly_searches']
st.session_state.last_search_reset = usage_data['last_search_reset']

# Updated: Premium monetization features added

# Load API keys
try:
    # Force load .env file and override existing env vars
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # Get keys from environment
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    if not OPENROUTER_API_KEY:
        st.error("OpenRouter API key not found in .env file")
        OPENROUTER_API_KEY = ""  # Set empty string to prevent None errors
    if not GOOGLE_API_KEY:
        st.error("Google API key not found in .env file")
        GOOGLE_API_KEY = ""  # Set empty string to prevent None errors
        
    # Auto-detect environment for Stripe configuration
    def detect_environment():
        """Automatically detect if we're in test or live environment"""
        # Check for manual override first (THIS IS THE EASIEST FIX)
        override = st.secrets.get("STRIPE_MODE_OVERRIDE", None)
        if override:
            return override.lower()
            
        # Auto-detect based on context
        try:
            # Check for Streamlit Cloud deployment
            # Streamlit Cloud sets these environment variables
            if (os.getenv('STREAMLIT_SHARING_MODE') or 
                os.getenv('STREAMLIT_CLOUD') or
                'streamlit.app' in str(os.getenv('HOSTNAME', '')) or
                'streamlit.app' in str(os.getenv('SERVER_NAME', '')) or
                'share.streamlit.io' in str(os.getenv('HOSTNAME', ''))):
                return "live"
            
            # Check for other cloud platforms
            if (os.getenv('DYNO') or  # Heroku
                os.getenv('RAILWAY_ENVIRONMENT') or  # Railway
                os.getenv('VERCEL') or  # Vercel
                os.getenv('RENDER') or  # Render
                os.getenv('PYTHONPATH')):  # Many cloud platforms set this
                return "live"
            
            # Check if running on localhost/development
            if hasattr(st, 'get_option'):
                try:
                    server_port = st.get_option('server.port')
                    if server_port and (8501 <= server_port <= 8510):  # Typical Streamlit dev ports
                        return "test"
                except:
                    pass
            
            # Check URL context (if available)
            try:
                import streamlit.web.cli as cli
                if 'localhost' in str(cli) or '127.0.0.1' in str(cli):
                    return "test"
            except:
                pass
            
            # Check if we're explicitly in development mode
            if os.getenv('STREAMLIT_ENV') == 'development':
                return "test"
            
            # If we have live Stripe keys but no test keys, assume live
            if (st.secrets.get("STRIPE_LIVE_SECRET_KEY") and 
                not st.secrets.get("STRIPE_TEST_SECRET_KEY")):
                return "live"
                
        except Exception:
            pass
            
        # If unsure, check for .env file (indicates local development)
        if os.path.exists('.env'):
            return "test"
            
        # Final fallback - if we're here, likely deployed
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
    
    # Debug info (remove after testing)
    if st.sidebar.checkbox("Show Environment Debug"):
        st.sidebar.write(f"Detected mode: {stripe_mode}")
        st.sidebar.write(f"HOSTNAME: {os.getenv('HOSTNAME', 'Not set')}")
        st.sidebar.write(f"SERVER_NAME: {os.getenv('SERVER_NAME', 'Not set')}")
        st.sidebar.write(f"STREAMLIT_SHARING_MODE: {os.getenv('STREAMLIT_SHARING_MODE', 'Not set')}")
        st.sidebar.write(f"STREAMLIT_CLOUD: {os.getenv('STREAMLIT_CLOUD', 'Not set')}")
        st.sidebar.write(f"PYTHONPATH exists: {bool(os.getenv('PYTHONPATH'))}")
        st.sidebar.write(f".env exists: {os.path.exists('.env')}")
        # Show first/last few chars of API key for debugging
        if STRIPE_SECRET_KEY:
            st.sidebar.write(f"Stripe key: {STRIPE_SECRET_KEY[:8]}...{STRIPE_SECRET_KEY[-4:]}")
        else:
            st.sidebar.write("No Stripe key found!")
    
    # Configure Stripe
    stripe.api_key = STRIPE_SECRET_KEY
    
    # Store the mode for later use
    st.session_state['stripe_mode'] = stripe_mode
        
except Exception as e:
    st.error(f"❌ Error loading API keys: {e}")
    st.stop()

# Stripe functions
def create_stripe_checkout_session():
    """Create a Stripe checkout session for premium subscription"""
    try:
        # Create checkout session without requiring login
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',  # Set mode to subscription for recurring payments
            line_items=[{
                'price_data': {
                    'currency': 'sgd',
                    'product_data': {
                        'name': 'CraveMap Premium',
                        'description': 'Unlimited searches, advanced filters (star rating, price range, distance), and detailed analytics',
                    },
                    'unit_amount': 499,  # $4.99 in cents
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            success_url=f"{st.get_option('server.baseUrlPath') or 'http://localhost:' + str(st.get_option('server.port'))}/?payment_success=true",
            cancel_url=f"{st.get_option('server.baseUrlPath') or 'http://localhost:' + str(st.get_option('server.port'))}"
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
            # Update session state
            st.session_state.user_premium = True
            st.session_state.payment_completed = True
            
            # Update usage data file with premium status
            usage_data = load_user_data(current_user_id)
            usage_data['is_premium'] = True
            usage_data['premium_since'] = datetime.now().isoformat()
            save_user_data(current_user_id, usage_data)
            
            # Clear URL parameters and show success message
            st.query_params.clear()
            st.balloons()
            st.success("🎉 Payment successful! Welcome to Premium!")
            st.rerun()
        elif 'payment_cancelled' in query_params and query_params['payment_cancelled'] == 'true':
            st.query_params.clear()
            st.warning("Payment was cancelled. You can try again anytime!")
            
    except Exception as e:
        st.error(f"Error checking payment status: {str(e)}")

# Check payment status when app loads
check_payment_status()

# User management system
def hash_email(email):
    """Create a hash of email for user identification"""
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]

def check_search_limits():
    """Check and update search limits. Returns True if search is allowed."""
    now = datetime.now()
    
    # Reset monthly searches if it's a new month
    if (st.session_state.last_search_reset is None or 
        datetime.fromisoformat(st.session_state.last_search_reset).month != now.month):
        st.session_state.monthly_searches = 0
        st.session_state.last_search_reset = now.isoformat()
        # Save reset data
        save_usage_data({
            'monthly_searches': st.session_state.monthly_searches,
            'last_search_reset': st.session_state.last_search_reset
        })
    
    # Premium users have unlimited searches
    if st.session_state.user_premium:
        return True
    
    # Free users get 3 searches per month
    if st.session_state.monthly_searches >= 3:
        st.warning("🔒 You've reached your 3 free searches for this month!")
        show_upgrade_prompt()
        return False
    
    # Increment search count
    st.session_state.monthly_searches += 1
    # Save updated search count
    save_usage_data({
        'monthly_searches': st.session_state.monthly_searches,
        'last_search_reset': st.session_state.last_search_reset
    })
    
    remaining = 3 - st.session_state.monthly_searches
    if remaining > 0:
        st.info(f"ℹ️ You have {remaining} free {'search' if remaining == 1 else 'searches'} remaining this month.")
    
    # Set a flag to rerun after search completes
    st.session_state.needs_rerun = True
    return True
    
    # Force refresh to update the sidebar counter
    st.rerun()
    
    return True

def show_upgrade_prompt():
    """Show premium upgrade prompt"""
    st.markdown("""
    ### 🌟 Ready to unlock unlimited searches?
    
    **Premium Benefits:**
    - ♾️ **Unlimited searches** per month
    - 🎯 **Advanced filters** (star rating, price range, distance control)
    - 📊 **Detailed analytics** and review insights
    
    Upgrade now for just $4.99/month!
    """)
    
    if not st.session_state.user_authenticated:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Login/Signup for Premium"):
                show_login_form()
                st.stop()
    else:
        if st.button("🚀 Upgrade to Premium - $4.99/month"):
            checkout_url = create_stripe_checkout_session()
            if checkout_url:
                st.markdown(f"[Click here to complete your upgrade]({checkout_url})")

def load_user_data():
    """Load user database from JSON file"""
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data(users):
    """Save user database to JSON file"""
    with open('users.json', 'w') as f:
        json.dump(users, f, indent=2)

def create_stripe_customer(email, name=""):
    """Create a Stripe customer"""
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name or email.split('@')[0],
            metadata={'source': 'cravemap_app'}
        )
        return customer.id
    except Exception as e:
        st.error(f"Error creating Stripe customer: {e}")
        return None

def check_stripe_subscription(customer_id):
    """Check if customer has active subscription"""
    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status='active',
            limit=1
        )
        return len(subscriptions.data) > 0
    except Exception as e:
        st.error(f"Error checking subscription: {e}")
        return False

def get_user_subscription_status(email):
    """Get user's current subscription status"""
    users = load_user_data()
    user_id = hash_email(email)
    
    if user_id not in users:
        return False, None
    
    user_data = users[user_id]
    customer_id = user_data.get('stripe_customer_id')
    
    if not customer_id:
        return False, None
    
    # Check with Stripe for active subscription
    is_premium = check_stripe_subscription(customer_id)
    
    # Update local data
    users[user_id]['is_premium'] = is_premium
    users[user_id]['last_checked'] = datetime.now().isoformat()
    save_user_data(users)
    
    return is_premium, customer_id

def register_user(email):
    """Register a new user"""
    users = load_user_data()
    user_id = hash_email(email)
    
    if user_id in users:
        return users[user_id]
    
    # Create Stripe customer
    customer_id = create_stripe_customer(email)
    
    if not customer_id:
        return None
    
    # Save user data
    user_data = {
        'email': email,
        'stripe_customer_id': customer_id,
        'is_premium': False,
        'created_at': datetime.now().isoformat(),
        'last_checked': datetime.now().isoformat()
    }
    
    users[user_id] = user_data
    save_user_data(users)
    
    return user_data

# Initialize session state
if 'user_premium' not in st.session_state:
    st.session_state.user_premium = False

if not OPENROUTER_API_KEY or not GOOGLE_API_KEY:
    st.error("❌ API keys not found! Please check your .env file or Streamlit secrets.")
    st.stop()

# AdSense: Verification meta tag injection
components.html("""
<script>
// Remove old AdSense verification - switching to premium model
console.log('Switched to premium monetization model');
</script>
""", height=0)

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://cravemap.streamlit.app",  # Required for OpenRouter
        "X-Title": "CraveMap"  # Required for OpenRouter
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
    review_texts = [r['text'] for r in reviews if 'text' in r]
    if not review_texts:
        return "No reviews available."
        
    joined = "\n".join(review_texts)
    prompt = f"""
    Based on the following Google reviews, summarize what people like about the restaurant in 2 sentences, and list the top 1-2 most frequently mentioned dishes:

    {joined}
    """

    try:
        response = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",  # Free tier model with good performance
            messages=[
                {"role": "system", "content": "You are an expert at summarizing restaurant reviews and identifying popular dishes. Be concise but informative."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content.strip()
            
        raise Exception("No valid response from AI model")
            
    except Exception as e:
        st.error(f"Error summarizing reviews: {str(e)}")
        raise e  # Re-raise to show the actual error

def get_place_photos(photo_metadata):
    photo_urls = []
    for p in photo_metadata[:5]:  # Limit to 5 photos
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
    
    # Enhanced query for premium users with cuisine filter
    for keyword in keywords:
        base_query = f"{keyword} in {location}"
        
        # Add price filter keywords
        if premium_filters and premium_filters.get("price") and premium_filters["price"] != "Any":
            if "Budget" in premium_filters["price"]:
                base_query += " cheap affordable"
            elif "Mid-range" in premium_filters["price"]:
                base_query += " moderate price"
            elif "Fine dining" in premium_filters["price"]:
                base_query += " fine dining upscale"
        
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
            # Add location parameter for radius search
            params["location"] = f"{location_coords['lat']},{location_coords['lng']}"
            params["rankby"] = "distance"  # This ensures results are sorted by distance
        res = requests.get(url, params=params)
        data = res.json()

        if "results" in data:
            for place in data["results"][:15]:  # Get more results for better filtering
                rating = place.get("rating")
                price_level = place.get("price_level", 0)  # 0-4 scale
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
                
                # Apply premium price filter
                if premium_filters and premium_filters.get("price") and premium_filters["price"] != "Any":
                    if "Budget" in premium_filters["price"] and price_level > 2:
                        continue
                    elif "Mid-range" in premium_filters["price"] and (price_level < 2 or price_level > 3):
                        continue
                    elif "Fine dining" in premium_filters["price"] and price_level < 3:
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
st.set_page_config(page_title="CraveMap 🍜", page_icon="🍴")

# Authentication check and UI
def show_login_form():
    """Show login/signup form"""
    st.markdown("### 🔐 Welcome to CraveMap Premium")
    st.markdown("Please enter your email to continue:")
    
    email = st.text_input("📧 Email Address", placeholder="your.email@example.com")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔑 Login / Sign Up", type="primary"):
            if email and "@" in email:
                with st.spinner("🔄 Setting up your account..."):
                    user_data = register_user(email)
                    
                if user_data:
                    st.session_state.user_email = email
                    st.session_state.user_authenticated = True
                    
                    # Check subscription status
                    is_premium, _ = get_user_subscription_status(email)
                    st.session_state.user_premium = is_premium
                    
                    st.success(f"✅ Welcome{'back' if is_premium else ''}! {email}")
                    if is_premium:
                        st.balloons()
                        st.info("🌟 Premium account detected!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Could not create account. Please try again.")
            else:
                st.error("❌ Please enter a valid email address.")
    
    with col2:
        if st.button("ℹ️ Reset App"):
            st.session_state.user_premium = False
            st.session_state.payment_completed = False
            # Reset search counter
            save_usage_data({
                'monthly_searches': 0,
                'last_search_reset': datetime.now().isoformat()
            })
            st.info("🔄 App reset to free tier")
            st.rerun()

# Show premium status in header
premium_badge = "🌟 PREMIUM" if st.session_state.user_premium else "🆓 FREE"
st.markdown(f"**Status:** {premium_badge}")

# Initialize the usage data file if it doesn't exist
if not os.path.exists('.usage_data.json'):
    save_usage_data({
        'monthly_searches': 0,
        'last_search_reset': datetime.now().isoformat()
    })
    st.rerun()

st.title("CraveMap: Find Food by Craving")
st.markdown("Type in what you're craving and get real nearby suggestions!")

# Sidebar with user status and premium features
with st.sidebar:
    st.markdown("### 👤 User Status")
    if st.session_state.user_premium:
        st.success("🌟 Premium User")
        st.markdown("✅ All features unlocked!")
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
        if st.button("🚀 Upgrade Now - $4.99/month", key="sidebar_upgrade"):
            checkout_url = create_stripe_checkout_session()
            if checkout_url:
                st.markdown(f"[Click here to complete your upgrade]({checkout_url})")
            st.success("Payment successful!")
            st.rerun()

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
    
    premium_price_filter = st.selectbox(
        "Price Range:",
        options=["Any", "$-$$ (Budget)", "$$-$$$ (Mid-range)", "$$$-$$$$ (Fine dining)"],
        index=0
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
    "price": premium_price_filter,
    "distance": premium_distance_filter
}

if 'needs_rerun' not in st.session_state:
    st.session_state.needs_rerun = False

if st.button("Find Food") and craving:
    # Check search limits for free users
    if not check_search_limits():
        st.stop()
    
    # Analytics: Track search events
    st.markdown(f"""
    <script>
    gtag('event', 'search', {{
        'search_term': '{craving.strip()}',
        'location': '{location}',
        'min_rating': {min_rating}
    }});
    </script>
    """, unsafe_allow_html=True)
    
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
        # Analytics: Track successful searches
        st.markdown(f"""
        <script>
        gtag('event', 'search_results', {{
            'results_count': {len(places)},
            'search_term': '{craving.strip()}'
        }});
        </script>
        """, unsafe_allow_html=True)
        
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
                summary = summarize_reviews_and_dishes(reviews)
                if summary:
                    st.markdown(f"""**What people say:**  
                {summary}""")
                
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
            
        # Rerun if needed to update the search counter
        if st.session_state.needs_rerun:
            st.session_state.needs_rerun = False
            st.rerun()

st.write("")  # Add some spacing

# Premium upgrade section
if not st.session_state.user_premium:  # Only show upgrade section for free users
    st.markdown("## 🌟 Upgrade to CraveMap Premium")

if not st.session_state.user_premium:
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
                # Update session state
                st.session_state.user_premium = True
                st.session_state.payment_completed = True
                
                # Update usage data file
                usage_data = load_usage_data()
                usage_data['is_premium'] = True
                usage_data['premium_since'] = datetime.now().isoformat()
                save_usage_data(usage_data)
                
                st.success("🎉 Admin code applied! Premium activated!")
                st.rerun()
            elif promo_code == ADMIN_DOWNGRADE_CODE:
                # Update session state
                st.session_state.user_premium = False
                st.session_state.payment_completed = False
                
                # Update usage data file
                usage_data = load_usage_data()
                usage_data['is_premium'] = False
                usage_data['premium_since'] = None
                save_usage_data(usage_data)
                
                st.info("Reset to free tier")
                st.rerun()
            elif promo_code == ADMIN_RESET_COUNTER:
                st.session_state.monthly_searches = 0
                save_usage_data({
                    'monthly_searches': 0,
                    'last_search_reset': st.session_state.last_search_reset
                })
                st.success("🔄 Search counter reset to 0!")
                st.rerun()
            elif promo_code:
                st.error("Invalid promo code")
else:
    st.success("🎉 You're a Premium user! Enjoy unlimited features!")
    if st.session_state.payment_completed:
        st.info("💳 Subscription active - $4.99/month")
    
    # Hidden admin downgrade (disguised as settings)
    with st.expander("⚙️ Account Settings"):
        st.write("Manage your subscription")
        if st.text_input("Admin action:", type="password") == ADMIN_DOWNGRADE_CODE:
            if st.button("Execute"):
                st.session_state.user_premium = False
                st.session_state.payment_completed = False
                st.info("Account reset")
                st.rerun()

st.markdown("Want to support this app? [Buy me a coffee ☕](https://www.buymeacoffee.com/alvincheong)")
