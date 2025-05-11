from get_top_players import get_top_players

if __name__ == "__main__":
    country_name = "spain"  # Replace with the desired country name
    season = "2023"  # Replace with the desired season

    try:
        # Fetch the top players by position
        top_players = get_top_players(country_name, season)

        # Print the top players for each position
        for position, players in top_players.items():
            print(f"\nTop {len(players)} {position}s:")
            for player in players:
                print(player)
    except Exception as e:
        print(f"An error occurred: {e}")