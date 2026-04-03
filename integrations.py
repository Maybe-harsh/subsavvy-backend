import os
import requests
from datetime import datetime, timedelta

# Tells Python to look for your Trakt API key in your .env file
TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID", "")
TRAKT_API_URL = "https://api.trakt.tv"

def fetch_tv_watch_history(user_trakt_token: str, days_back: int = 1) -> int:
    """
    Pulls the user's Smart TV watch history from Trakt's API.
    Returns the total minutes watched in the specified timeframe.
    """
    
    # Failsafe: If the user doesn't have a token, return 0 minutes
    if not user_trakt_token:
        return 0
        
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": TRAKT_CLIENT_ID,
        "Authorization": f"Bearer {user_trakt_token}"
    }
    
    # Calculate the timestamp to look back (e.g., the last 24 hours)
    start_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
    
    try:
        # Hit the Trakt history endpoint
        response = requests.get(
            f"{TRAKT_API_URL}/users/me/history?start_at={start_date}", 
            headers=headers,
            timeout=10 # Prevents the server from hanging if Trakt is slow
        )
        
        if response.status_code == 200:
            history = response.json()
            total_minutes = 0
            
            for item in history:
                # Trakt provides the runtime of the movie/episode
                if 'movie' in item:
                    total_minutes += item['movie'].get('runtime', 0)
                elif 'episode' in item:
                    total_minutes += item['episode'].get('runtime', 0)
                    
            print(f"✅ Successfully fetched {total_minutes} TV minutes from Trakt.")
            return total_minutes
        else:
            print(f"⚠️ Trakt API returned status {response.status_code}")
            return 0
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while fetching from Trakt: {e}")
        return 0