import requests
from datetime import datetime, timedelta
import time
import random
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get tomorrow's date in YYYY-MM-DD format
tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

# Define the sports you want to fetch
sports = ["football", "basketball", "tennis"]
matches = []

# Configure a session with retry logic
def get_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Set headers to mimic a browser request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com"
}

session = get_session()

try:
    for sport in sports:
        logger.info(f"Fetching {sport} matches...")
        
        # Construct the URL dynamically for the current sport
        sport_url = f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{tomorrow}"
        
        try:
            # Make the API request with headers
            response = session.get(sport_url, headers=headers)
            # Check if the response is successful
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            # Extract the events from the response
            events = data.get("events", [])

            if events:
                for match in events:
                    start_time = match.get("startTimestamp")
                    if start_time:
                        match_date = datetime.utcfromtimestamp(start_time)
                        home_team_id = match.get("homeTeam", {}).get("id")
                        away_team_id = match.get("awayTeam", {}).get("id")
                        match_obj = {
                            "match_date": match_date.strftime("%Y-%m-%d %H:%M"),
                            "home_team": match.get("homeTeam", {}).get("name", "Unknown"),
                            "home_team_image": f"https://api.sofascore.com/api/v1/team/{home_team_id}/image",
                            "away_team": match.get("awayTeam", {}).get("name", "Unknown"),
                            "away_team_image": f"https://api.sofascore.com/api/v1/team/{away_team_id}/image",
                            "country": match.get("tournament", {}).get("category", {}).get("country", {}).get("name", "Unknown"),
                            "league": match.get("tournament", {}).get("name", "Unknown"),
                            "sport": match.get("tournament", {}).get("category", {}).get("sport", {}).get("name", "Unknown"),
                        }
                        matches.append(match_obj)
                        logger.info(f"Added match: {match_obj['home_team']} vs {match_obj['away_team']}")

            
            # Add a random delay between requests to avoid rate limiting
            delay = random.uniform(5, 10)
            logger.info(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
            
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 403:
                logger.error(f"403 Forbidden error for {sport}. API may require authentication or is blocking requests.")
            else:
                logger.error(f"HTTP Error for {sport}: {err}")
            # Longer delay after an error
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error fetching {sport} matches: {e}")
            time.sleep(5)

    if matches:
        logger.info(f"Sending {len(matches)} matches to the local API...")
        response = requests.post(
            # "https://telegram-bot-2h7q.onrender.com/match/create",
            "http://localhost:8000/match/create",
            json=matches
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Successfully sent {len(matches)} matches")
        else:
            logger.error(f"❌ Failed to send matches: {response.status_code} - {response.text}")
    else:
        logger.warning("No matches were collected to send")
            
except Exception as e:
    logger.error(f"❌ Unexpected error: {e}")
