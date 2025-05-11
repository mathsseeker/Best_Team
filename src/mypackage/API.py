import os
import time
import requests
import pandas as pd
from datetime import datetime

# API settings
URL = "https://v3.football.api-sports.io/"
CACHE_DIR = "match_data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Rate limiting (10 calls/minute, 100 calls/day)
MIN_DELAY = 6  # 6 seconds between calls

# Add your API key here
KEY = "your_api_key_here"

def call_api(endpoint, params=None):
    """Makes API call with rate limiting."""
    if params is None:
        params = {}
    
    headers = {"x-rapidapi-key": KEY}
    url = f"{URL}{endpoint}"
    
    # Enforce rate limiting
    time.sleep(MIN_DELAY)
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")

def get_cache_path(team_id):
    """Returns cache file path for a team."""
    return f"{CACHE_DIR}/team_{team_id}_2021_season.csv"

def load_from_cache(team_id):
    """Loads cached data if available and recent."""
    cache_file = get_cache_path(team_id)
    if os.path.exists(cache_file):
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if (datetime.now() - cache_time).days < 7:  # 7-day cache validity
            return pd.read_csv(cache_file)
    return None

def save_to_cache(df, team_id):
    """Saves data to cache."""
    df.to_csv(get_cache_path(team_id), index=False)

def get_team_fixtures(team_id, season=2021):
    """Gets all fixtures for a team in a season."""
    cache = load_from_cache(team_id)
    if cache is not None:
        return cache
    
    print(f"Fetching fixtures for team {team_id}...")
    fixtures = call_api("fixtures", {
        "league": 140,  # LaLiga
        "season": season,
        "team": team_id
    })
    
    if not fixtures.get("response"):
        raise Exception(f"No fixtures found for team {team_id}")
    
    # Convert to DataFrame and cache
    df = pd.json_normalize(fixtures["response"])
    save_to_cache(df, team_id)
    return df

def get_match_stats(fixture_id, team_id):
    """Gets statistics for a specific match and team."""
    stats = call_api("fixtures/statistics", {
        "fixture": fixture_id,
        "team": team_id
    })
    
    if not stats.get("response"):
        return None
    
    # Extract and format statistics
    stats_data = {}
    for stat in stats["response"][0]["statistics"]:
        stat_name = stat["type"].lower().replace(" ", "_").replace("%", "pct")
        stats_data[stat_name] = stat["value"]
    
    return stats_data

def fetch_team_df(team_id, n_matches, season=2021):
    """
    Fetches the last `n_matches` for a given team.
    
    Args:
        team_id (int): ID of the team to fetch.
        n_matches (int): Number of recent matches to fetch.
        season (int): Season year (default: 2021).
    
    Returns:
        pd.DataFrame: DataFrame containing the team's last `n_matches`.
    """
    # Fetch fixtures for the team
    fixtures = get_team_fixtures(team_id, season)
    
    # Sort fixtures by date and get the required number of matches
    fixtures['fixture.timestamp'] = pd.to_numeric(fixtures['fixture.timestamp'])
    sorted_fixtures = fixtures.sort_values('fixture.timestamp').head(n_matches)
    
    # Collect statistics for each match
    all_stats = []
    print(f"Fetching statistics for {n_matches} matches for team ID {team_id}...")
    for i, (_, match) in enumerate(sorted_fixtures.iterrows(), 1):
        print(f"Fetching match {i}/{n_matches} (Fixture ID: {match['fixture.id']})")
        stats = get_match_stats(match['fixture.id'], team_id)
        if stats:
            match_data = {
                'team': team_id,
                'matchday': i,
                'fixture_id': match['fixture.id'],
                'date': match['fixture.date'],
                'opponent': match['teams.away.name'] if match['teams.home.id'] == team_id else match['teams.home.name'],
                'venue': match['fixture.venue.name'],
                'result': f"{match['goals.home']}-{match['goals.away']}",
                'is_home': match['teams.home.id'] == team_id
            }
            match_data.update(stats)
            all_stats.append(match_data)
    
    # Convert to DataFrame
    team_df = pd.DataFrame(all_stats)
    return team_df
