#!/usr/bin/env python3
"""
Google Maps Places API module for finding local repair shops and services
Uses the Nearby Search (New) API to find places within a specified area
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

@dataclass
class PlaceInfo:
    """Data class for place information"""
    place_id: str
    name: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    price_level: Optional[int] = None
    business_status: Optional[str] = None
    types: List[str] = None
    location: Tuple[float, float] = None  # (latitude, longitude)
    distance_meters: Optional[float] = None

class GoogleMapsPlacesAPI:
    """Google Maps Places API client for finding local repair shops and services"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Google Maps Places API client
        
        Args:
            api_key: Google Maps API key. If None, will try to get from environment variable GOOGLE_MAPS_API_KEY
        """
        self.api_key = api_key or os.getenv('GOOGLE_MAPS_API_KEY')
        if not self.api_key:
            raise ValueError("Google Maps API key is required. Set GOOGLE_MAPS_API_KEY environment variable or pass api_key parameter.")
        
        self.base_url = "https://places.googleapis.com/v1/places"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.api_key
        })
    
    def search_nearby_repair_shops(
        self, 
        latitude: float, 
        longitude: float, 
        radius: float = 5000,  # 5km default radius
        max_results: int = 10,
        device_type: str = "phone"
    ) -> List[PlaceInfo]:
        """
        Search for nearby repair shops using Nearby Search (New) API
        
        Args:
            latitude: User's latitude
            longitude: User's longitude  
            radius: Search radius in meters (default 5000m = 5km)
            max_results: Maximum number of results to return
            device_type: Type of device to search for repair shops (phone, laptop, car, etc.)
            
        Returns:
            List of PlaceInfo objects containing repair shop information
        """
        # Map device types to relevant place types
        place_types = self._get_repair_place_types(device_type)
        
        # Field mask for the data we want to retrieve
        field_mask = [
            "places.displayName",
            "places.formattedAddress", 
            "places.nationalPhoneNumber",
            "places.websiteUri",
            "places.rating",
            "places.priceLevel",
            "places.businessStatus",
            "places.types",
            "places.location",
            "places.id"
        ]
        
        # Prepare the request payload
        payload = {
            "includedTypes": place_types,
            "maxResultCount": max_results,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "radius": radius
                }
            },
            "rankPreference": "DISTANCE"  # Rank by distance from user
        }
        
        try:
            # Make the API request
            response = self.session.post(
                f"{self.base_url}:searchNearby",
                headers={'X-Goog-FieldMask': ','.join(field_mask)},
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_places_response(data, latitude, longitude)
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Error searching for repair shops: {e}")
            return []
    
    def search_text_repair_shops(
        self,
        query: str,
        latitude: float,
        longitude: float,
        radius: float = 5000,
        max_results: int = 10
    ) -> List[PlaceInfo]:
        """
        Search for repair shops using Text Search (New) API with location bias
        
        Args:
            query: Search query (e.g., "iPhone repair shop", "laptop repair near me")
            latitude: User's latitude for location bias
            longitude: User's longitude for location bias
            radius: Search radius in meters
            max_results: Maximum number of results to return
            
        Returns:
            List of PlaceInfo objects containing repair shop information
        """
        # Field mask for the data we want to retrieve
        field_mask = [
            "places.displayName",
            "places.formattedAddress",
            "places.nationalPhoneNumber", 
            "places.websiteUri",
            "places.rating",
            "places.priceLevel",
            "places.businessStatus",
            "places.types",
            "places.location",
            "places.id"
        ]
        
        # Prepare the request payload
        payload = {
            "textQuery": query,
            "maxResultCount": max_results,
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "radius": radius
                }
            },
            "rankPreference": "DISTANCE"
        }
        
        try:
            # Make the API request
            response = self.session.post(
                f"{self.base_url}:searchText",
                headers={'X-Goog-FieldMask': ','.join(field_mask)},
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_places_response(data, latitude, longitude)
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Error searching for repair shops: {e}")
            return []
    
    def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific place
        
        Args:
            place_id: Google Places ID
            
        Returns:
            Dictionary containing detailed place information
        """
        field_mask = [
            "id",
            "displayName",
            "formattedAddress",
            "nationalPhoneNumber",
            "websiteUri", 
            "rating",
            "priceLevel",
            "businessStatus",
            "types",
            "location",
            "openingHours",
            "reviews",
            "photos"
        ]
        
        try:
            response = self.session.get(
                f"{self.base_url}/{place_id}",
                headers={'X-Goog-FieldMask': ','.join(field_mask)}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API Error getting place details: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting place details: {e}")
            return None
    
    def _get_repair_place_types(self, device_type: str) -> List[str]:
        """
        Map device types to relevant Google Places types
        
        Args:
            device_type: Type of device (phone, laptop, car, etc.)
            
        Returns:
            List of Google Places types
        """
        type_mapping = {
            "phone": [
                "electronics_store",
                "mobile_phone_shop", 
                "store"
            ],
            "laptop": [
                "electronics_store",
                "computer_store",
                "store"
            ],
            "car": [
                "car_repair",
                "car_dealer",
                "gas_station"
            ],
            "appliance": [
                "electronics_store",
                "home_goods_store",
                "store"
            ],
            "general": [
                "electronics_store",
                "store",
                "establishment"
            ]
        }
        
        return type_mapping.get(device_type.lower(), type_mapping["general"])
    
    def _parse_places_response(self, data: Dict[str, Any], user_lat: float, user_lng: float) -> List[PlaceInfo]:
        """
        Parse the API response and convert to PlaceInfo objects
        
        Args:
            data: API response data
            user_lat: User's latitude for distance calculation
            user_lng: User's longitude for distance calculation
            
        Returns:
            List of PlaceInfo objects
        """
        places = []
        
        for place_data in data.get("places", []):
            try:
                # Extract basic information
                place_id = place_data.get("id", "")
                name = place_data.get("displayName", {}).get("text", "Unknown")
                address = place_data.get("formattedAddress", "Address not available")
                
                # Extract contact information
                phone = place_data.get("nationalPhoneNumber")
                website = place_data.get("websiteUri")
                
                # Extract ratings and pricing
                rating = place_data.get("rating")
                price_level = place_data.get("priceLevel")
                business_status = place_data.get("businessStatus")
                
                # Extract types
                types = place_data.get("types", [])
                
                # Extract location
                location_data = place_data.get("location", {})
                location = None
                if location_data:
                    lat = location_data.get("latitude")
                    lng = location_data.get("longitude")
                    if lat is not None and lng is not None:
                        location = (lat, lng)
                        
                        # Calculate distance from user
                        distance = self._calculate_distance(user_lat, user_lng, lat, lng)
                    else:
                        distance = None
                else:
                    distance = None
                
                place_info = PlaceInfo(
                    place_id=place_id,
                    name=name,
                    address=address,
                    phone=phone,
                    website=website,
                    rating=rating,
                    price_level=price_level,
                    business_status=business_status,
                    types=types,
                    location=location,
                    distance_meters=distance
                )
                
                places.append(place_info)
                
            except Exception as e:
                print(f"Error parsing place data: {e}")
                continue
        
        return places
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        
        Args:
            lat1, lng1: First point coordinates
            lat2, lng2: Second point coordinates
            
        Returns:
            Distance in meters
        """
        import math
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in meters
        r = 6371000
        return c * r

def search_repair_shops_advanced(
    query: str,
    latitude: float,
    longitude: float,
    radius: float = 5000,
    max_results: int = 10,
    device_type: str = "phone"
) -> List[Dict[str, Any]]:
    """
    Advanced search function for repair shops that combines multiple search strategies
    
    Args:
        query: Search query (e.g., "iPhone repair", "laptop repair near me")
        latitude: User's latitude
        longitude: User's longitude
        radius: Search radius in meters
        max_results: Maximum number of results
        device_type: Type of device to search for
        
    Returns:
        List of dictionaries containing repair shop information
    """
    try:
        # Initialize the API client
        api = GoogleMapsPlacesAPI()
        
        # Try text search first (more specific)
        text_results = api.search_text_repair_shops(
            query=query,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            max_results=max_results
        )
        
        # If text search doesn't return enough results, try nearby search
        if len(text_results) < max_results:
            nearby_results = api.search_nearby_repair_shops(
                latitude=latitude,
                longitude=longitude,
                radius=radius,
                max_results=max_results - len(text_results),
                device_type=device_type
            )
            
            # Combine results, avoiding duplicates
            existing_ids = {place.place_id for place in text_results}
            for place in nearby_results:
                if place.place_id not in existing_ids:
                    text_results.append(place)
        
        # Convert to dictionary format for consistency with other modules
        results = []
        for place in text_results[:max_results]:
            result_dict = {
                "place_id": place.place_id,
                "name": place.name,
                "address": place.address,
                "phone": place.phone,
                "website": place.website,
                "rating": place.rating,
                "price_level": place.price_level,
                "business_status": place.business_status,
                "types": place.types or [],
                "location": place.location,
                "distance_meters": place.distance_meters,
                "distance_km": round(place.distance_meters / 1000, 2) if place.distance_meters else None,
                "source": "Google Maps Places API"
            }
            results.append(result_dict)
        
        return results
        
    except Exception as e:
        print(f"Error in search_repair_shops_advanced: {e}")
        return []

def format_repair_shops_response(places: List[Dict[str, Any]]) -> str:
    """
    Format the repair shops results into a readable string
    
    Args:
        places: List of place dictionaries
        
    Returns:
        Formatted string with repair shop information
    """
    if not places:
        return "No repair shops found in your area."
    
    formatted_results = []
    formatted_results.append(f"Found {len(places)} repair shops near you:\n")
    
    for i, place in enumerate(places, 1):
        result = f"{i}. **{place['name']}**\n"
        result += f"   📍 {place['address']}\n"
        
        if place.get('distance_km'):
            result += f"   📏 {place['distance_km']} km away\n"
        
        if place.get('phone'):
            result += f"   📞 {place['phone']}\n"
        
        if place.get('website'):
            result += f"   🌐 {place['website']}\n"
        
        if place.get('rating'):
            result += f"   ⭐ {place['rating']}/5.0 rating\n"
        
        if place.get('business_status'):
            status_emoji = "🟢" if place['business_status'] == "OPERATIONAL" else "🔴"
            result += f"   {status_emoji} {place['business_status']}\n"
        
        formatted_results.append(result)
    
    return "\n".join(formatted_results)

# Test function
def test_google_maps_search():
    """Test the Google Maps Places API functionality"""
    print("🧪 Testing Google Maps Places API")
    print("=" * 50)
    
    # Test coordinates (San Francisco)
    test_lat = 37.7749
    test_lng = -122.4194
    
    try:
        # Test 1: Search for iPhone repair shops
        print("📱 Testing iPhone repair shop search...")
        results = search_repair_shops_advanced(
            query="iPhone repair shop",
            latitude=test_lat,
            longitude=test_lng,
            radius=5000,
            max_results=5,
            device_type="phone"
        )
        
        if results:
            print(f"✅ Found {len(results)} iPhone repair shops")
            print(format_repair_shops_response(results))
        else:
            print("❌ No iPhone repair shops found")
        
        print("\n" + "-" * 50 + "\n")
        
        # Test 2: Search for laptop repair shops
        print("💻 Testing laptop repair shop search...")
        results = search_repair_shops_advanced(
            query="laptop repair",
            latitude=test_lat,
            longitude=test_lng,
            radius=5000,
            max_results=3,
            device_type="laptop"
        )
        
        if results:
            print(f"✅ Found {len(results)} laptop repair shops")
            print(format_repair_shops_response(results))
        else:
            print("❌ No laptop repair shops found")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure you have set the GOOGLE_MAPS_API_KEY environment variable")

if __name__ == "__main__":
    test_google_maps_search()
