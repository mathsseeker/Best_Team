import pandas as pd
import requests
from typing import Optional, Dict

KEY = "82c2ff00a706bf9dd19cdd152fd01aeb"
URL = "https://v3.football.api-sports.io/"

def call_api(endpoint: str, params: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """
    Makes a GET request to the specified API endpoint with optional query parameters.
    
    Args:
        endpoint (str): The API endpoint to call (e.g., "players").
        params (Optional[Dict[str, str]]): A dictionary of query parameters to include in the request.

    Returns:
        pd.DataFrame: A Pandas DataFrame containing the flattened API response data.

    Raises:
        Exception: If the API request fails or the response contains no data.
    """

    params = params or {}
    headers = {"x-rapidapi-key": KEY}
    url = f"{URL}{endpoint}"
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # Raises an error for bad responses
        data = response.json()
        
        if not data.get("response"):
            raise ValueError("No data found in the API response.")
            
        # Normalize the main response
        df = pd.json_normalize(data["response"], sep="_")
        
        # If statistics exist, process them
        if "statistics" in df.columns:
            # Reset index before exploding to avoid index issues
            df = df.reset_index(drop=True)
            
            # Explode statistics (each player might have multiple entries)
            df = df.explode("statistics", ignore_index=True)
            
            # Normalize statistics
            stats_df = pd.json_normalize(
                df["statistics"],
                sep="_",
                meta_prefix="statistics_"
            ).reset_index(drop=True)
            
            # Merge with player data
            df = pd.concat([
                df.drop("statistics", axis=1).reset_index(drop=True), 
                stats_df
            ], axis=1)
            
            # Flatten remaining nested columns
            for col in df.columns:
                if df[col].notna().any() and isinstance(df[col].iloc[0], dict):
                    nested_df = pd.json_normalize(df[col], sep="_").add_prefix(f"{col}_")
                    df = pd.concat([
                        df.drop(col, axis=1).reset_index(drop=True),
                        nested_df.reset_index(drop=True)
                    ], axis=1)
        
        return df
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    except ValueError as ve:
        raise Exception (f"Valure Error : {str(ve)}")
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
    
    # Step 2: Explicitly rename key columns (no guessing!)
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

    print("\nPlayer Statistics:")
    print(df.to_string(index=False))  # Print without DataFrame index
    return df