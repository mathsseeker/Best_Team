import time
import logging
from player_init import Player, Goalkeeper, Defender, Midfielder, Attacker
from get_players_ids import get_players_ids

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Logs to the console
    ]
)
logger = logging.getLogger(__name__)

# Rate-limiting constant
REQUEST_DELAY = 0.2  # 300 requests per minute = 0.2 seconds per request


def get_top_players(country_name: str, season: str):
    """
    Fetches and returns the top players by position for a given country and season.

    Args:
        country_name (str): The name of the country (e.g., 'Spain').
        season (str): The season (e.g., '2022').

    Returns:
        dict: A dictionary containing the top players by position.
    """
    # Fetch player IDs for the given country and season
    player_ids = get_players_ids(country_name, season)

    # Fetch player data and classify by position
    players = []
    for idx, player_id in enumerate(player_ids):
        try:
            # Rate-limiting: Ensure we don't exceed the maximum requests per minute
            if idx > 0:
                time.sleep(REQUEST_DELAY)

            player = Player.from_api(player_id, season)
            players.append(player)
        except Exception as e:
            logger.error(f"Failed to fetch data for player ID {player_id}: {e}")

    # Group players by position
    grouped_players = {
        "Goalkeeper": [],
        "Defender": [],
        "Midfielder": [],
        "Attacker": []
    }

    for player in players:
        if isinstance(player, Goalkeeper):
            grouped_players["Goalkeeper"].append(player)
        elif isinstance(player, Defender):
            grouped_players["Defender"].append(player)
        elif isinstance(player, Midfielder):
            grouped_players["Midfielder"].append(player)
        elif isinstance(player, Attacker):
            grouped_players["Attacker"].append(player)

    # Sort players in each position by their computed rating and select the top N
    top_players = {
        "Goalkeeper": sorted(grouped_players["Goalkeeper"], key=lambda p: p.compute_rating(), reverse=True)[:3],
        "Defender": sorted(grouped_players["Defender"], key=lambda p: p.compute_rating(), reverse=True)[:8],
        "Midfielder": sorted(grouped_players["Midfielder"], key=lambda p: p.compute_rating(), reverse=True)[:6],
        "Attacker": sorted(grouped_players["Attacker"], key=lambda p: p.compute_rating(), reverse=True)[:6]
    }

    return top_players


if __name__ == "__main__":
    # Example usage
    country_name = "Spain"  # Replace with the desired country name
    season = "2023"  # Replace with the desired season

    top_players = get_top_players(country_name, season)

    # Print the top players for each position
    for position, players in top_players.items():
        print(f"\nTop {len(players)} {position}s:")
        for player in players:
            print(player)