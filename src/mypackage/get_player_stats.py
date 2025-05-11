import pandas as pd
import requests
from typing import Optional, Dict
import os
import hashlib
import json
from pathlib import Path


# For privacy purposes, the API key is not hardcoded.
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

# Get the path to the .env file in the project root
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent 
env_path = project_root / '.env'


load_env_file(str(env_path))

# Get the API key
KEY = os.getenv('API_KEY')
URL = "https://v3.football.api-sports.io/"

# Create a cache directory
CACHE_DIR = project_root / "api_cache"
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_filename(endpoint: str, params: Dict[str, str]) -> Path:
    """Generate a unique filename for caching based on endpoint and parameters."""
    param_str = json.dumps(params, sort_keys=True) if params else "no_params"
    unique_key = f"{endpoint}_{param_str}"
    filename = hashlib.md5(unique_key.encode()).hexdigest() + ".json"
    return CACHE_DIR / filename

def load_from_cache(cache_file: Path) -> Optional[Dict]:
    """Load data from cache file if it exists."""
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Cache file corrupted, deleting {cache_file}")
            cache_file.unlink()  # Remove corrupted cache file if it exists
            return None
    return None

def save_to_cache(cache_file: Path, data: Dict):
    """Save API response data to cache file."""
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    except IOError as e:
        print(f"Warning: Could not save cache file {cache_file}: {e}")



def call_api(endpoint: str, params: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Makes a GET request to the specified API endpoint with optional query parameters.
    Uses local cache to avoid repeated calls for the same data."""
    params = params or {}
    cache_file = get_cache_filename(endpoint, params)
    
    # Try to load from cache first
    cached_data = load_from_cache(cache_file)
    if cached_data is not None:
        data = cached_data
    else:
        # Not in cache, make API call
        headers = {"x-rapidapi-key": KEY}
        url = f"{URL}{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("response"):
                raise ValueError("No data found in the API response.")
            
            # Save to cache for future use
            save_to_cache(cache_file, data)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except ValueError as ve:
            raise Exception(f"Value Error: {str(ve)}")
    
    # Process the data into a DataFrame
    try:
        df = pd.json_normalize(data["response"], sep="_")
        
        if "statistics" in df.columns:
            df = df.reset_index(drop=True)
            df = df.explode("statistics", ignore_index=True)
            
            stats_df = pd.json_normalize(
                df["statistics"],
                sep="_",
                meta_prefix="statistics_"
            ).reset_index(drop=True)
            
            df = pd.concat([
                df.drop("statistics", axis=1).reset_index(drop=True), 
                stats_df
            ], axis=1)
            
            for col in df.columns:
                if df[col].notna().any() and isinstance(df[col].iloc[0], dict):
                    nested_df = pd.json_normalize(df[col], sep="_").add_prefix(f"{col}_")
                    df = pd.concat([
                        df.drop(col, axis=1).reset_index(drop=True),
                        nested_df.reset_index(drop=True)
                    ], axis=1)
        
        return df
    
    except Exception as e:
        raise Exception(f"Error processing API response: {str(e)}")

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and standardizes column names in the DataFrame, preserving key fields.

    Args:
        df (pd.DataFrame): The DataFrame whose columns need to be cleaned.

    Returns:
        pd.DataFrame: A DataFrame with cleaned and standardized column names.
    """
    # Step 1: Remove prefixes carefully
    df.columns = df.columns.str.replace(r'^(statistics_|games_)', '', regex=True)  # Only remove unnecessary prefixes
    
    # Step 2: Explicitly rename the columns
    column_renames = {
        # Player
        'player_id': 'player_id',
        'player_name': 'player_name',
        
        # Team
        'team_id': 'team_id',
        'team_name': 'team_name',
        'team_logo': 'team_logo',
        
        # Competition
        'league_id': 'competition_id',
        'league_name': 'competition_name',
        'league_logo': 'competition_logo',
        'country_logo': 'country_flag',  # Rename for clarity
    }
    
    # Step 3: Apply renames (skip missing columns)
    return df.rename(columns={k: v for k, v in column_renames.items() if k in df.columns})

def get_player_stats(player_id: str, season: str) -> pd.DataFrame:
    """
    Fetches and displays player statistics for a given season.

    Args:
        player_id (str): The unique identifier of the player.
        season (str): The season for which to fetch the player's statistics (e.g., "2022").

    Returns:
        pd.DataFrame: A DataFrame containing the player's statistics for the specified season.
    """
    params = {"id": player_id, "season": season}
    df = call_api("players", params)
    df = clean_column_names(df)
    return df

if __name__ == "__main__":
    # Example usage
    player_id = "154"  # Replace with actual player ID
    season = "2022"  # Replace with actual season
    try:
        stats_df = get_player_stats(player_id, season)
        print(stats_df.iloc[0])
    except Exception as e:
        print(f"An error occurred: {e}")