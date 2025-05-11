import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import requests
import time
from dataclasses import dataclass
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('player_fetcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
def load_env_file(filepath: str):
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

# Set up paths and config
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent 
env_path = project_root / '.env'
load_env_file(str(env_path))

API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY not found in .env file")

BASE_URL = "https://v3.football.api-sports.io/"
CACHE_DIR = project_root / "api_cache"
CACHE_DIR.mkdir(exist_ok=True)
SEASON = 2023
REQUEST_DELAY = 2  # Seconds between API calls


# Updated teams with league information, the code didnt worked for La Liga clubs
EXTRA_TEAMS = [
    {'name': 'Leipzig', 'id': 173, 'league_id': 78},      
    {'name': 'PSG', 'id': 85, 'league_id': 61},          
    {'name': 'Leverkusen', 'id': 168, 'league_id': 78},   
    {'name': 'Lazio', 'id': 487, 'league_id': 135},       
    {'name': 'AC Milan', 'id': 489, 'league_id': 135},    
    {'name': 'Sporting CP', 'id': 228, 'league_id': 94}, 
    {'name': 'Udinese', 'id': 494, 'league_id': 135},     
    {'name': 'Marseille', 'id': 81, 'league_id': 61},     
    {'name': 'Roma', 'id': 497, 'league_id': 135},        
    {'name': 'Napoli', 'id': 495, 'league_id': 135},           
    {'name': 'Bayern Munich', 'id': 157, 'league_id': 78},   
    {'name': 'Porto', 'id': 212, 'league_id': 94} ,      
    {'name': 'Benfica', 'id': 211, 'league_id': 94},  
    {'name': 'Inter', 'id': 503, 'league_id': 135},        
    {'name': 'Barcelona', 'id': 529, 'league_id': 140},
    {'name': 'Atletico Madrid', 'id': 530, 'league_id': 140},
    {'name': 'Real Madrid', 'id': 541, 'league_id': 140},
    {'name': 'Real Betis', 'id': 543, 'league_id': 140},
    {'name': 'Valencia', 'id': 532, 'league_id': 140},
    {'name': 'Sevilla', 'id': 536, 'league_id': 140},
    {'name': 'Villarreal', 'id': 533, 'league_id': 140},
    {'name': 'Real Sociedad', 'id': 548, 'league_id': 140},
    {'name': 'Athletic Club', 'id': 531, 'league_id': 140},
    {'name': 'Celta Vigo', 'id': 538, 'league_id': 140},
    {'name': 'Getafe', 'id': 546, 'league_id': 140},
    {'name': 'Girona', 'id': 547, 'league_id': 140},
    {'name': 'Alaves', 'id': 542, 'league_id': 140},
    {'name': 'Rayo Vallecano', 'id': 728, 'league_id': 140},
    {'name': 'Mallorca', 'id': 798, 'league_id': 140},
    {'name': 'Cadiz', 'id': 724, 'league_id': 140},
    {'name': 'Granada', 'id': 715, 'league_id': 140},
    {'name': 'Las Palmas', 'id': 534, 'league_id': 140},
    {'name': 'Osasuna', 'id': 727, 'league_id': 140},
    {'name': 'Almeria', 'id': 723, 'league_id': 140}  
]

# League IDs to process
LEAGUE_IDS = {
    'Premier League': 39
}

@dataclass
class Player:
    player_id: int
    name: str
    age: int
    position: str
    nationality: str
    team_id: int
    team_name: str
    league_id: int
    league_name: str
    appearances: int = 0
    minutes: int = 0
    goals: int = 0
    assists: Optional[int] = None
    rating: Optional[float] = None

def get_cache_filename(endpoint: str, params: Dict[str, str]) -> Path:
    param_str = json.dumps(params, sort_keys=True) if params else "no_params"
    unique_key = f"{endpoint}_{param_str}"
    filename = hashlib.md5(unique_key.encode()).hexdigest() + ".json"
    return CACHE_DIR / filename

def load_from_cache(cache_file: Path) -> Optional[Dict]:
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Cache file corrupted, deleting {cache_file}")
            cache_file.unlink()
            return None
    return None

def save_to_cache(cache_file: Path, data: Dict):
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        logger.warning(f"Could not save cache file {cache_file}: {e}")

class APIClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'x-rapidapi-host': "v3.football.api-sports.io",
            'x-rapidapi-key': API_KEY
        })
    
    def make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        cache_file = get_cache_filename(endpoint, params)
        cached_data = load_from_cache(cache_file)
        
        if cached_data is not None:
            logger.debug(f"Using cached data for {endpoint}")
            return cached_data
            
        try:
            time.sleep(REQUEST_DELAY)
            response = self.session.get(
                f"{BASE_URL}/{endpoint}",
                params=params,
                timeout=10
            )
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.make_request(endpoint, params)
                
            response.raise_for_status()
            data = response.json()
            save_to_cache(cache_file, data)
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

class PlayerFetcher:
    def __init__(self):
        self.api = APIClient()
        self.teams = self._load_teams()
    
    def _load_teams(self) -> Dict[int, Dict[str, Any]]:
        """Load teams from leagues and additional teams"""
        teams = {}
        
        # Load teams from leagues
        for league_name, league_id in LEAGUE_IDS.items():
            try:
                logger.info(f"Fetching teams for {league_name}...")
                params = {'league': league_id, 'season': SEASON}
                data = self.api.make_request('teams', params)
                
                if not data or 'response' not in data:
                    logger.warning(f"No teams found for {league_name}")
                    continue
                    
                for team_data in data['response']:
                    team = team_data['team']
                    teams[team['id']] = {
                        'name': team['name'],
                        'league_id': league_id,
                        'league_name': league_name
                    }
                    
            except Exception as e:
                logger.error(f"Error loading teams for {league_name}: {e}")
        
        # Add extra teams with their league information
        for team_info in EXTRA_TEAMS:
            teams[team_info['id']] = {
                'name': team_info['name'],
                'league_id': team_info['league_id'],
                'league_name': 'Other Leagues'
            }
        
        logger.info(f"Loaded {len(teams)} teams in total")
        return teams
    
    def fetch_all_players(self) -> List[Player]:
        """Fetch players from all teams"""
        players = []
        
        # Process league teams
        for league_name, league_id in LEAGUE_IDS.items():
            try:
                league_players = self._fetch_league_players(league_id, league_name)
                players.extend(league_players)
                logger.info(f"Found {len(league_players)} players in {league_name}")
            except Exception as e:
                logger.error(f"Failed to process {league_name}: {e}")
        
        # Process extra teams with their actual leagues
        for team_info in EXTRA_TEAMS:
            try:
                team_data = self.teams[team_info['id']]
                team_players = self._fetch_team_players(
                    team_id=team_info['id'],
                    team_name=team_data['name'],
                    league_id=team_info['league_id'],
                    league_name=team_data['league_name']
                )
                players.extend(team_players)
                logger.info(f"Found {len(team_players)} players in {team_data['name']}")
            except Exception as e:
                logger.error(f"Failed to process {team_data['name']}: {e}")
        
        return players
    
    def _fetch_league_players(self, league_id: int, league_name: str) -> List[Player]:
        """Fetch all players from a league"""
        players = []
        team_ids = [team_id for team_id, info in self.teams.items() if info.get('league_id') == league_id]
        
        for team_id in team_ids:
            team_name = self.teams[team_id]['name']
            try:
                team_players = self._fetch_team_players(team_id, team_name, league_id, league_name)
                players.extend(team_players)
                logger.info(f"Found {len(team_players)} players in {team_name} ({league_name})")
            except Exception as e:
                logger.error(f"Failed to process {team_name}: {e}")
        
        return players
    
    def _fetch_team_players(self, team_id: int, team_name: str, league_id: Optional[int], league_name: str) -> List[Player]:
        """Fetch all players for a single team with pagination"""
        players = []
        page = 1
        total_pages = 1
        
        while page <= total_pages:
            try:
                params = {
                    'team': team_id,
                    'season': SEASON,
                    'page': page
                }
                if league_id:
                    params['league'] = league_id
                
                data = self.api.make_request('players', params)
                
                if not data or 'response' not in data:
                    break
                
                # Process current page
                for player_data in data['response']:
                    player = self._process_player(player_data, team_id, team_name, league_id, league_name)
                    if player:
                        players.append(player)
                
                # Update pagination
                if page == 1:
                    total_pages = data['paging']['total']
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error fetching page {page} for {team_name}: {e}")
                break
        
        return players
    
    def _process_player(self, player_data: Dict[str, Any], team_id: int, team_name: str, 
                       league_id: Optional[int], league_name: str) -> Optional[Player]:
        """Convert raw API data to Player object"""
        try:
            player_info = player_data['player']
            stats = player_data['statistics'][0] if player_data.get('statistics') else {}
            
            return Player(
                player_id=player_info['id'],
                name=player_info['name'],
                age=player_info['age'],
                position=stats.get('games', {}).get('position', 'Unknown'),
                nationality=player_info.get('nationality', 'Unknown'),
                team_id=team_id,
                team_name=team_name,
                league_id=league_id if league_id else 0,
                league_name=league_name,
                appearances=stats.get('games', {}).get('appearances', 0),
                minutes=stats.get('games', {}).get('minutes', 0),
                goals=stats.get('goals', {}).get('total', 0),
                assists=stats.get('goals', {}).get('assists'),
                rating=stats.get('games', {}).get('rating')
            )
        except Exception as e:
            logger.error(f"Error processing player data: {e}")
            return None

def save_to_csv(players: List[Player], filename: str) -> bool:
    """Save player data to CSV with error handling"""
    try:
        df = pd.DataFrame([vars(p) for p in players])
        df.to_csv(filename, index=False)
        logger.info(f"Data successfully saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to save data: {e}")
        return False

def get_players_ids(country_name, season):
    """
    Get a list of player IDs for a given country and season.

    Args:
        country_name (str): The name of the country (e.g., 'Spain').
        season (str): The season (e.g., '2023').

    Returns:
        list: A list of player IDs for the specified country and season.
    """
    # Define or load the `players` list
    fetcher = PlayerFetcher()
    players = fetcher.fetch_all_players()  # Replace with actual logic to fetch players
    SEASON = season  # Use the provided season

    # Collect player IDs for the specified country
    country_players_list = [
        player.player_id for player in players if player.nationality.lower() == country_name.lower()
    ]

    logger.info(f"Total players found for {country_name}: {len(country_players_list)}")
    logger.info(f"Player IDs for {country_name}: {country_players_list}")

    return country_players_list


def main():
    try:
        logger.info("Starting player data collection...")
        
        # Example usage
        country_name = "spain"  # Replace with desired country name
        season = "2023"  # Replace with desired season
        player_ids = get_players_ids(country_name, season)
        
        logger.info(f"Player IDs for {country_name} in season {season}: {player_ids}")
    except Exception as e:
        logger.critical(f"Fatal error in main execution: {e}")
    finally:
        logger.info("Process completed")


if __name__ == "__main__":
    main()