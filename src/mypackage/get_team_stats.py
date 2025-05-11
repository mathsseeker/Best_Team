import os
import json
import time
import requests
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import hashlib

# Environment and API Setup
def load_env_file(filepath: str):
    """Load environment variables from a file."""
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Could not find .env file at {filepath}")

# Set up paths and load API key
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
env_path = project_root / '.env'
load_env_file(str(env_path))

KEY = os.getenv('API_KEY')
if not KEY:
    raise ValueError("API_KEY not found in .env file")
URL = "https://v3.football.api-sports.io/"

# Cache Setup
CACHE_DIR = project_root / "api_cache"
CACHE_DIR.mkdir(exist_ok=True)

# Rate Limiting (300 calls/minute = 0.2s delay)
REQUEST_DELAY = 0.2
last_request_time = 0

def get_cache_filename(endpoint: str, params: Dict[str, str]) -> Path:
    """Generate unique cache filename."""
    param_str = json.dumps(params, sort_keys=True)
    unique_key = f"{endpoint}_{param_str}"
    filename = hashlib.md5(unique_key.encode()).hexdigest() + ".json"
    return CACHE_DIR / filename

def load_from_cache(cache_file: Path) -> Optional[Dict]:
    """Load cached data if recent."""
    if cache_file.exists():
        cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if (datetime.now() - cache_time).days < 1:  # 1-day cache
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                cache_file.unlink()
    return None

def save_to_cache(cache_file: Path, data: Dict):
    """Save data to cache."""
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save cache {cache_file}: {e}")

def call_api(endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict:
    """Make API call with rate limiting."""
    global last_request_time
    params = params or {}
    cache_file = get_cache_filename(endpoint, params)
    
    # Check cache first
    cached_data = load_from_cache(cache_file)
    if cached_data:
        return cached_data

    # Rate limiting
    current_time = time.time()
    elapsed = current_time - last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    
    # Make request
    headers = {
        "x-rapidapi-key": KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    
    try:
        response = requests.get(f"{URL}{endpoint}", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("response"):
            print(f"API Warning: Empty response for {endpoint} with params {params}")
            return {"response": []}
        
        save_to_cache(cache_file, data)
        last_request_time = time.time()
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"API Error: {str(e)}")
        return {"response": []}

def process_stats(stats: List[Dict]) -> Dict:
    """Convert stats to consistent format with error handling."""
    processed = {}
    if not stats:
        return processed
        
    for stat in stats:
        try:
            if not isinstance(stat, dict):
                continue
            key = stat.get('type', '').lower().replace(' ', '_').replace('%', 'pct')
            if key and 'value' in stat:
                processed[key] = stat['value']
        except Exception as e:
            print(f"Warning: Error processing stat {stat}: {str(e)}")
            continue
    return processed

def get_team_matches(team_id: str, season: str, league_ids: List[int]) -> List[Dict]:
    """Get all matches for a team in a season across specified leagues."""
    all_matches = []
    
    for league_id in league_ids:
        print(f"Checking league {league_id}...")
        params = {
            "team": team_id,
            "season": season,
            "league": league_id
        }
        data = call_api("fixtures", params)
        matches = data.get("response", [])
        
        if matches:
            print(f"Found {len(matches)} matches in league {league_id}")
            all_matches.extend(matches)
        else:
            print(f"No matches found in league {league_id}")
    
    return all_matches

def get_match_stats(fixture_id: int, team_id: str) -> Optional[Dict]:
    """Get statistics for a specific match with robust error handling."""
    params = {
        "fixture": fixture_id,
        "team": team_id
    }
    data = call_api("fixtures/statistics", params)
    responses = data.get("response", [])
    
    if not responses:
        print(f"No statistics data found for fixture {fixture_id}")
        return None
        
    try:
        # Find our team's stats in the response
        team_stats = next(
            (r for r in responses if isinstance(r, dict) and str(r.get('team', {}).get('id')) == str(team_id)),
            None
        )
        if team_stats and isinstance(team_stats.get('statistics'), list):
            return process_stats(team_stats['statistics'])
        return None
    except Exception as e:
        print(f"Error processing stats for fixture {fixture_id}: {str(e)}")
        return None

def get_team_match_stats_for_seasons(team_id: str, seasons: List[str], league_ids: List[int]) -> pd.DataFrame:
    """Main function to get match stats across seasons and leagues."""
    all_matches = []
    
    for season in seasons:
        print(f"\nProcessing season {season}...")
        matches = get_team_matches(team_id, season, league_ids)
        
        if not matches:
            print(f"No matches found for team {team_id} in {season}")
            continue
            
        for i, match in enumerate(matches, 1):
            try:
                if not isinstance(match, dict):
                    continue
                    
                fixture = match.get('fixture', {})
                teams = match.get('teams', {})
                league = match.get('league', {})
                goals = match.get('goals', {})
                
                match_info = {
                    'fixture_id': fixture.get('id'),
                    'date': fixture.get('date'),
                    'season': season,
                    'team_id': team_id,
                    'league_id': league.get('id'),
                    'league_name': league.get('name'),
                    'competition_type': league.get('type'),
                    'home_team': teams.get('home', {}).get('name'),
                    'away_team': teams.get('away', {}).get('name'),
                    'home_goals': goals.get('home'),
                    'away_goals': goals.get('away'),
                    'venue': fixture.get('venue', {}).get('name')
                }
                
                # Get statistics if available
                stats = get_match_stats(fixture.get('id'), team_id)
                if stats:
                    match_info.update(stats)
                
                all_matches.append(match_info)
                
                print(f"Processed match {i}/{len(matches)}: {match_info['home_team']} vs {match_info['away_team']}")
                
            except Exception as e:
                print(f"Error processing match {i}: {str(e)}")
                continue
    
    return pd.DataFrame(all_matches)
