import argparse
import pandas as pd

from API import fetch_team_df  
from winningparameters import compute_feature_importances
from Black_Scholes import analyze_match_with_bs, print_report

# Map friendly names → (team_id, rows)
TEAMS = {
    "real_madrid": (541, 25),
    "alaves": (542, 24),
    # Add more teams here as needed
}

def feature_analysis(team_key):
    """
    Perform feature analysis for the given team.

    Args:
        team_key (str): Key of the team in the global TEAMS dictionary.
    """
    team_id, n_matches = TEAMS[team_key]
    print(f"\n▶ Feature analysis for {team_key} (last {n_matches} matches):")
    df = fetch_team_df(team_id, n_matches)
    compute_feature_importances(df, team_key)

def black_scholes_valuation(home_team_key, away_team_key, market_odds):
    """
    Perform Black-Scholes valuation for a given match.

    Args:
        home_team_key (str): Key of the home team in the TEAMS dictionary.
        away_team_key (str): Key of the away team in the TEAMS dictionary.
        market_odds (dict): Market odds for home, draw, and away outcomes.
    """
    home_team_id, home_matches = TEAMS[home_team_key]
    away_team_id, away_matches = TEAMS[away_team_key]

    print(f"\n▶ Black-Scholes valuation for {home_team_key} vs {away_team_key}:")
    report = analyze_match_with_bs(
        fetch_team_df(home_team_id, home_matches),  # Fetch data for home team
        fetch_team_df(away_team_id, away_matches),  # Fetch data for away team
        market_odds
    )
    print_report(report)

def main():
    """
    Main entry point for the script.
    Allows feature analysis and Black-Scholes valuation for general cases.
    """
    parser = argparse.ArgumentParser(
        description="1) Fetch & model features for any LaLiga team. "
                    "2) Optionally run the Black-Scholes valuation for any two teams."
    )
    parser.add_argument(
        "mode",
        choices=["features", "valuation", "both"],
        help="features: run RF/SMOTE importances; valuation: BS model; both: do both"
    )
    parser.add_argument(
        "--team",
        choices=TEAMS.keys(),
        default="real_madrid",
        help="Which team for feature analysis"
    )
    parser.add_argument(
        "--home_team",
        choices=TEAMS.keys(),
        default="real_madrid",
        help="Home team for valuation"
    )
    parser.add_argument(
        "--away_team",
        choices=TEAMS.keys(),
        default="alaves",
        help="Away team for valuation"
    )
    parser.add_argument(
        "--odds",
        nargs=3,
        metavar=("HOME", "DRAW", "AWAY"),
        type=float,
        default=[1.36, 4.90, 9.50],
        help="Market odds for home (Real Madrid), draw, and away (Alavés)"
    )
    args = parser.parse_args()

    # Perform feature analysis
    if args.mode in ("features", "both"):
        feature_analysis(args.team)

    # Perform Black-Scholes valuation
    if args.mode in ("valuation", "both"):
        market_odds = dict(zip(["home", "draw", "away"], args.odds))
        black_scholes_valuation(args.home_team, args.away_team, market_odds)

if __name__ == "__main__":
    main()