from urllib import response
import streamlit as st
import requests
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Load API keys - try .env first, then Streamlit secrets
try:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or st.secrets["OPENROUTER_API_KEY"]
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or st.secrets["GOOGLE_API_KEY"]
except:
    # Fallback to environment variables only
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    if not OPENROUTER_API_KEY or not GOOGLE_API_KEY:
        st.error("❌ API keys not found! Please check your .env file or Streamlit secrets.")
        st.stop()

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
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
    joined = "\n".join(review_texts)
    prompt = f"""
    Based on the following Google reviews, summarize what people like about the restaurant in 2 sentences, and list the top 1-2 most frequently mentioned dishes:

    {joined}
    """

    models = [
        "mistralai/mistral-7b-instruct:free",     # primary (free quota)
        "mistralai/mistral-7b-instruct",          # fallback (paid/credits)
        "mistralai/mixtral-8x7b-instruct"         # fallback (paid/credits)
        "openchat/openchat-3.5-0106:free",
        "gryphe/mythomax-l2-13b:free"
    ]

    for model in models:
#        st.write(f"🔍 Trying model: {model}")  # Always logs to UI

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You summarize reviews and extract top dishes."},
                    {"role": "user", "content": prompt}
                ]
            )

            # Check if valid 'choices' exist
            if hasattr(response, "choices") and response.choices:
#                st.write(f"✅ Using model: {model}")
                return response.choices[0].message.content.strip()
            else:
                st.write(f"⚠️ Model {model} returned no choices.")
                continue

        except Exception as e:
#            st.write(f"❌ Model failed: {model}")
            continue

    st.error("All models are currently unavailable or rate-limited. Please try again later.")
    return ""

def get_place_photos(photo_metadata):
    photo_urls = []
    for p in photo_metadata[:5]:  # Limit to 5 photos
        ref = p.get("photo_reference")
        if ref:
            url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={GOOGLE_API_KEY}"
            photo_urls.append(url)
    return photo_urls

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
                        "place_id": place.get("place_id"),
                        "rating": rating,
                        "address": place.get("formatted_address"),
                        "url": f"https://www.google.com/maps/search/?api=1&query={place.get('name').replace(' ', '+')}"
                    })
                # If no rating available and min_rating is 0, include it
                elif rating is None and min_rating == 0:
                    places.append({
                        "name": place.get("name"),
                        "place_id": place.get("place_id"),
                        "rating": rating,
                        "address": place.get("formatted_address"),
                        "url": f"https://www.google.com/maps/search/?api=1&query={place.get('name').replace(' ', '+')}"
                    })
    
    # Limit to top 3 results after filtering
    return places[:3]

# --- Streamlit UI ---
st.set_page_config(page_title="CraveMap 🍜", page_icon="🍴")
st.title("CraveMap: Find Food by Craving")
st.markdown("Type in what you're craving and get real nearby suggestions!")

craving = st.text_input("What are you craving today?")
location = st.text_input("Where are you? (City or Area)", placeholder="e.g. Orchard Road")

# Rating filter
st.markdown("### Filter Options")
min_rating = st.selectbox(
    "Minimum Google Star Rating:",
    options=[4.5, 4.0, 3.5, 3.0, 0],
    index=4,
    format_func=lambda x: "Any rating" if x == 0 else f"{x}+ stars"
)

if st.button("Find Food") and craving:
    keywords = [craving.strip()]
    st.write(f"### Searching for: {craving.strip()}")
    
    # Show filter info
    if min_rating > 0:
        st.write(f"**Filter:** Showing places with {min_rating}+ star rating")

    with st.spinner("Searching for places..."):
        places = search_food_places(location, keywords, min_rating)

    if places:
        st.success(f"Found {len(places)} suggestion(s)!")
        for place in places:
            st.markdown(f"## {place['name']}")
            st.markdown(f"⭐ {place.get('rating', 'N/A')}\n\n📍 {place['address']}\n\n[🔗 View on Google Maps]({place['url']})")

            # Get place details
            details = get_place_details(place['place_id'])
            result = details.get("result", {})

            if "reviews" in result:
                summary = summarize_reviews_and_dishes(result["reviews"])
                if summary:
                    st.markdown(f"""**What people say:**  
                {summary}""")

            if "photos" in result:
                st.markdown("**Reviewer-uploaded photos (not dish-specific):**")
                photo_urls = get_place_photos(result["photos"])
                cols = st.columns(3)
                for idx, url in enumerate(photo_urls):
                    with cols[idx % 3]:
                        st.image(url, use_container_width=True)
    else:
        if min_rating > 0:
            st.warning(f"No places found with {min_rating}+ star rating. Try lowering the rating filter, rephrasing your craving, or changing your location.")
        else:
            st.warning("No matching places found. Try rephrasing your craving or changing your location.")

st.markdown("---")
st.markdown("Want to support this app? [Buy me a coffee ☕](https://www.buymeacoffee.com/alvincheong)")
