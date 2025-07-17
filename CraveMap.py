from urllib import response
import streamlit as st
import requests
import os
from openai import OpenAI

# Load API keys
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

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
        "mistralai/mistral-7b-instruct:free",   # Use first if available
        "openrouter/mistral-7b",                # Good fallback, usually fast
        "openrouter/mixtral-8x7b"               # Quality fallback
    ]


    for model in models:
        st.write(f"🔍 Trying model: {model}")  # Always logs to UI

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
                st.write(f"✅ Using model: {model}")
                return response.choices[0].message.content.strip()
            else:
                st.write(f"⚠️ Model {model} returned no choices.")
                continue

        except Exception as e:
            st.write(f"❌ Exception for model {model}: {str(e)}")
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

def search_food_places(location, keywords):
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
            for place in data["results"][:3]:  # Take only the top result for each keyword
                places.append({
                    "name": place.get("name"),
                    "place_id": place.get("place_id"),
                    "rating": place.get("rating"),
                    "address": place.get("formatted_address"),
                    "url": f"https://www.google.com/maps/search/?api=1&query={place.get('name').replace(' ', '+')}"
                })
    return places

# --- Streamlit UI ---
st.set_page_config(page_title="CraveMap 🍜", page_icon="🍴")
st.title("CraveMap: Find Food by Craving")
st.markdown("Type in what you're craving and get real nearby suggestions!")

craving = st.text_input("What are you craving today?")
location = st.text_input("Where are you? (City or Area)", value="Tiong Bahru")

if st.button("Find Food") and craving:
    keywords = [craving.strip()]
    st.write(f"### Searching for: {craving.strip()}")

    with st.spinner("Searching for places..."):
        places = search_food_places(location, keywords)

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
        st.warning("No matching places found. Try rephrasing your craving or changing your location.")

st.markdown("---")
st.markdown("Want to support this app? [Buy me a coffee ☕](https://www.buymeacoffee.com/alvincheong)")
