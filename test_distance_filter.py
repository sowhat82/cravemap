#!/usr/bin/env python3
"""
Distance Filter Testing - Debug Production Issues
Tests the distance filtering logic and Google Places API parameters
"""

import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers using the Haversine formula"""
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    R = 6371
    distance = R * c
    
    return distance

def test_distance_filtering():
    print("🧪 Distance Filter Testing")
    print("=" * 40)
    
    # Test coordinates (Singapore examples)
    orchard_road = (1.3048, 103.8318)  # Orchard Road, Singapore
    marina_bay = (1.2807, 103.8559)    # Marina Bay, Singapore  
    changi_airport = (1.3644, 103.9915) # Changi Airport, Singapore
    sentosa = (1.2494, 103.8303)       # Sentosa Island, Singapore
    
    print(f"📍 Origin: Orchard Road {orchard_road}")
    print()
    
    # Test different locations
    test_locations = [
        ("Marina Bay", marina_bay),
        ("Changi Airport", changi_airport), 
        ("Sentosa Island", sentosa)
    ]
    
    for name, coords in test_locations:
        distance = calculate_distance(
            orchard_road[0], orchard_road[1],
            coords[0], coords[1]
        )
        print(f"📍 {name}: {distance:.2f} km")
    
    print("\n🎯 Distance Filter Tests")
    print("-" * 30)
    
    # Test filter scenarios
    filter_distances = [0.5, 1.0, 2.0, 5.0, 10.0]
    
    for filter_km in filter_distances:
        print(f"\n🔍 Filter: {filter_km} km maximum")
        for name, coords in test_locations:
            distance = calculate_distance(
                orchard_road[0], orchard_road[1],
                coords[0], coords[1]
            )
            passed = distance <= filter_km
            status = "✅ INCLUDED" if passed else "❌ FILTERED OUT"
            print(f"  {name}: {distance:.2f} km - {status}")
    
    print("\n🔧 Google Places API Parameters")
    print("-" * 30)
    
    # Test API parameter logic
    premium_filters = {"distance": 0.5}
    
    if premium_filters and premium_filters.get("distance"):
        radius_meters = int(premium_filters["distance"] * 1000)
        print(f"✅ Using radius parameter: {radius_meters} meters")
        print(f"   API call: &location=1.3048,103.8318&radius={radius_meters}")
    else:
        print(f"✅ Using rankby=distance")
        print(f"   API call: &location=1.3048,103.8318&rankby=distance")
    
    print("\n🚨 Common Production Issues:")
    print("1. Google Places API returns results beyond radius")
    print("2. Need post-filtering with Haversine distance calculation")
    print("3. Some places may not have accurate coordinates")
    print("4. API location parameter vs user's actual location mismatch")

if __name__ == "__main__":
    test_distance_filtering()
