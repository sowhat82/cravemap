import streamlit as st
import requests
import os
from datetime import datetime

# API Keys (will get from environment)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")

# Initialize session state
if 'rating_filter' not in st.session_state:
    st.session_state.rating_filter = 0.0

def generate_booking_options(restaurant_name, address=""):
    """Generate booking URLs for popular Singapore platforms"""
    
    # URL-encode restaurant name for search queries
    import urllib.parse
    encoded_name = urllib.parse.quote(restaurant_name)
    encoded_address = urllib.parse.quote(address) if address else ""
    
    return {
        "Chope": f"https://www.chope.co/singapore-restaurants?q={encoded_name}",
        "OpenRice": f"https://www.openrice.com/en/singapore/restaurants?what={encoded_name}",
        "Quandoo": f"https://www.quandoo.sg/en/table-reservation?destination=singapore&query={encoded_name}",
        "TableCheck": f"https://www.tablecheck.com/en/shops?q={encoded_name}&locale=en&country=singapore", 
        "Google Reservations": f"https://www.google.com/search?q={encoded_name}+{encoded_address}+singapore+reservation+booking"
    }

def create_booking_interface(place):
    """Create a comprehensive booking interface for a restaurant"""
    st.markdown("### 🍽️ **Make a Reservation**")
    
    # Generate booking options
    booking_options = generate_booking_options(place['name'], place.get('address', ''))
    
    st.markdown("#### 🔗 **Quick Booking Links**")
    st.markdown("*Click to book directly on these platforms:*")
    
    # Create booking buttons in columns - main booking options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.link_button("🍽️ Chope", booking_options["Chope"], use_container_width=True)
        st.link_button("🍚 OpenRice", booking_options["OpenRice"], use_container_width=True)
    
    with col2:
        st.link_button("🍴 Quandoo", booking_options['Quandoo'], use_container_width=True)
        st.link_button("📅 TableCheck", booking_options["TableCheck"], use_container_width=True)
    
    with col3:
        st.link_button("🔍 Google Search", booking_options['Google Reservations'], use_container_width=True)
        if st.button(f"📞 Call Restaurant", key=f"call_{place['place_id']}", use_container_width=True):
            st.info("💡 **Tip:** Call during business hours for the best availability!")
    
    # Booking assistance form in expander - everything in one form to prevent reruns
    with st.expander("📝 **Need Help Booking?** (We can assist you)"):
        st.markdown("*Fill out your preferences and we'll help make the reservation:*")
        
        # Put everything in a single form to prevent page reloads
        with st.form(key=f"assistance_form_{place['place_id']}"):
            st.markdown("**Reservation Details:**")
            
            # Date, time, and party size
            col1, col2, col3 = st.columns(3)
            
            with col1:
                booking_date = st.date_input("Preferred Date")
            
            with col2:
                booking_time = st.time_input("Preferred Time")
            
            with col3:
                party_size = st.selectbox("Party Size", options=[1, 2, 3, 4, 5, 6, 7, 8, "8+"], index=1)
            
            st.markdown("**Your Contact Information:**")
            
            # Contact information
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Your Name*")
                phone = st.text_input("Phone Number*")
            with col2:
                email = st.text_input("Email")
                special_requests = st.text_area("Special Requests\n(dietary restrictions, occasion, etc.)")
            
            # Submit button
            submitted = st.form_submit_button("📨 Request Booking Assistance", use_container_width=True)
            
            if submitted:
                if name and phone:
                    formatted_date = booking_date.strftime("%B %d, %Y") if booking_date else "Not specified"
                    formatted_time = booking_time.strftime("%I:%M %p") if booking_time else "Not specified"
                    
                    st.success(f"""
                    **✅ Booking Assistance Request Submitted!**
                    
                    **Restaurant:** {place['name']}  
                    **Date:** {formatted_date}  
                    **Time:** {formatted_time}  
                    **Party Size:** {party_size}  
                    **Contact:** {name} - {phone}  
                    **Email:** {email if email else 'Not provided'}  
                    **Special Requests:** {special_requests if special_requests else 'None'}  
                    
                    📧 **We'll contact the restaurant and get back to you within 2 hours!**
                    """)
                    
                else:
                    st.error("❌ Please fill in your name and phone number (required fields).")
    
    st.markdown("---")

def search_food_places(location, keywords, min_rating=0):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    places = []
    for keyword in keywords:
        params = {
            "query": f"{keyword} in {location}",
            "key": GOOGLE_API_KEY
        }
        res = requests.get(url, params=params)
        data = res.json()

        if "results" in data:
            for place in data["results"][:10]:  # Get more results to filter from
                rating = place.get("rating")
                # Filter by minimum rating if rating exists
                if rating is not None and rating >= min_rating:
                    places.append({
                        "name": place.get("name"),
                        "address": place.get("formatted_address"),
                        "rating": rating,
                        "price_level": place.get("price_level"),
                        "place_id": place.get("place_id"),
                        "photo_reference": place.get("photos", [{}])[0].get("photo_reference") if place.get("photos") else None
                    })
    
    # Sort by rating in descending order
    places.sort(key=lambda x: x["rating"], reverse=True)
    return places

def get_place_details(place_id):
    url = f"https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "reviews,website,formatted_phone_number,opening_hours,photos",
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    return response.json().get("result", {})

def get_ai_summary(reviews, restaurant_name):
    if not reviews or not OPENROUTER_API_KEY:
        return None
    
    review_texts = [review.get('text', '') for review in reviews[:5]]
    combined_reviews = "\n".join(review_texts)
    
    prompt = f"""Based on these customer reviews for {restaurant_name}, provide a concise summary focusing on:
1. Food quality and popular dishes
2. Service and atmosphere
3. Value for money
4. Any standout positives or concerns

Reviews:
{combined_reviews}

Please provide a balanced 2-3 sentence summary."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 200
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", 
                               headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    
    return None

def main():
    st.set_page_config(page_title="CraveMap", page_icon="🍽️", layout="wide")
    
    st.title("🍽️ CraveMap - Discover & Book Amazing Food")
    st.markdown("*Find the perfect restaurant and make reservations instantly*")
    
    if not GOOGLE_API_KEY:
        st.error("⚠️ Google API key not found. Please add it to your .env file or Streamlit secrets.")
        return
    
    # Search Interface
    col1, col2 = st.columns([3, 1])
    with col1:
        location = st.text_input("📍 Location", placeholder="Singapore", value="Singapore")
        food_types = st.text_input("🍜 What are you craving?", 
                                  placeholder="pasta, sushi, burgers, etc.",
                                  value="restaurant")
    
    with col2:
        # Star rating filter
        st.markdown("**⭐ Minimum Rating**")
        min_rating = st.slider("", 0.0, 5.0, st.session_state.rating_filter, 0.1, 
                              format="%.1f ⭐", key="rating_slider")
        st.session_state.rating_filter = min_rating
    
    # Search button
    if st.button("🔍 **Find Restaurants**", type="primary", use_container_width=True):
        if location and food_types:
            with st.spinner("🍴 Searching for delicious options..."):
                keywords = [kw.strip() for kw in food_types.split(",")]
                places = search_food_places(location, keywords, min_rating)
                
                if places:
                    st.success(f"🎉 Found {len(places)} restaurants with {min_rating}+ stars!")
                    
                    for place in places:
                        with st.container():
                            # Restaurant header
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"## 🍽️ **{place['name']}**")
                                if place.get('address'):
                                    st.markdown(f"📍 {place['address']}")
                            
                            with col2:
                                if place.get('rating'):
                                    rating_stars = "⭐" * int(place['rating'])
                                    st.markdown(f"### {rating_stars}")
                                    st.markdown(f"**{place['rating']}/5.0**")
                            
                            # Restaurant details and booking
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                # Get detailed information
                                details = get_place_details(place['place_id'])
                                
                                # AI Summary
                                if details.get('reviews'):
                                    ai_summary = get_ai_summary(details['reviews'], place['name'])
                                    if ai_summary:
                                        st.markdown("### 🤖 **AI Summary**")
                                        st.info(ai_summary)
                                
                                # Reviews
                                if details.get('reviews'):
                                    with st.expander("📝 **Customer Reviews**"):
                                        for review in details['reviews'][:3]:
                                            stars = "⭐" * review.get('rating', 0)
                                            st.markdown(f"**{stars}** - {review.get('author_name', 'Anonymous')}")
                                            st.markdown(f"*{review.get('text', '')[:200]}...*")
                                            st.markdown("---")
                            
                            with col2:
                                # Booking interface
                                create_booking_interface(place)
                                
                                # Additional info
                                if place.get('price_level'):
                                    price_symbols = "$" * place['price_level']
                                    st.markdown(f"**💰 Price Range:** {price_symbols}")
                                
                                # Website and phone
                                if details.get('website'):
                                    st.link_button("🌐 Website", details['website'], use_container_width=True)
                                
                                if details.get('formatted_phone_number'):
                                    st.markdown(f"📞 **Phone:** {details['formatted_phone_number']}")
                            
                            st.markdown("---")
                else:
                    st.warning(f"😕 No restaurants found with {min_rating}+ stars. Try different keywords or lower the rating filter.")
        else:
            st.error("Please enter both location and food preferences!")

if __name__ == "__main__":
    main()
