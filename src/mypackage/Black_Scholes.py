import pandas as pd
import numpy as np
from scipy.stats import poisson, norm
from datetime import datetime
import os

# File paths with your exact path for Real Madrid
RM_PATH = "/Users/fut_payi/Desktop/Calc_Project/Real Madrid_pre_h2h_2021.csv"
ALAVES_PATH = "/Users/fut_payi/Desktop/Calc_Project/Alaves_pre_h2h_2021.csv"

def load_specific_matches():
    """Load specific number of matches for each team from exact paths"""
    try:
        # Load Real Madrid data (first 25 matches)
        rm_df = pd.read_csv(RM_PATH).head(25)
        # Load Alavés data (first 24 matches)
        alaves_df = pd.read_csv(ALAVES_PATH).head(24)
        
        # Verify we got the right number of matches
        assert len(rm_df) == 25, f"Expected 25 RM matches, got {len(rm_df)}"
        assert len(alaves_df) == 24, f"Expected 24 Alavés matches, got {len(alaves_df)}"
        
        # Common preprocessing
        for df in [rm_df, alaves_df]:
            df['date'] = pd.to_datetime(df['date'])
            df[['goals_scored', 'goals_conceded']] = df['result'].str.split('-', expand=True).astype(int)
            if 'ball_possession' in df.columns:
                df['ball_possession'] = df['ball_possession'].str.rstrip('%').astype(float) / 100
            if 'passes_pct' in df.columns:
                df['passes_pct'] = df['passes_pct'].str.rstrip('%').astype(float) / 100
        
        return rm_df, alaves_df
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Required data files not found at:\n{RM_PATH}\n{ALAVES_PATH}") from e
    except Exception as e:
        raise Exception(f"Error loading data: {str(e)}") from e

# Team classification system
team_classes = {
    'Atletico Madrid': 1, 'Real Madrid': 1, 'Barcelona': 1,
    'Sevilla': 2, 'Betis': 2, 'Real Sociedad': 2, 'Athletic Club': 2, 'Villarreal': 2,
    'Valencia': 3, 'Osasuna': 3, 'Celta Vigo': 3,
    'Rayo Vallecano': 4, 'Elche': 4, 'Espanyol': 4, 'Getafe': 4,
    'Mallorca': 5, 'Cadiz': 5, 'Granada CF': 5, 'Levante': 5, 'Alavés': 5
}

def calculate_team_metrics(df, team_name):
    """Calculate performance metrics using specific match counts"""
    df = df.copy()
    df['opponent_class'] = df['opponent'].map(team_classes)
    df['days_rest'] = df.groupby('team')['date'].diff().dt.days.fillna(7)
    
    # Weight stats by opponent class
    weights = {1: 2.0, 2: 1.5, 3: 1.2, 4: 0.8, 5: 0.5}
    df['weight'] = df['opponent_class'].map(weights)
    df['weighted_goals_scored'] = df['goals_scored'] * df['weight']
    df['weighted_goals_conceded'] = df['goals_conceded'] * df['weight']
    
    return {
        'team': team_name,
        'matches_used': len(df),
        'avg_goals_scored': df['goals_scored'].mean(),
        'avg_goals_conceded': df['goals_conceded'].mean(),
        'volatility': df['goals_scored'].std(),
        'weighted_avg_scored': df['weighted_goals_scored'].mean(),
        'weighted_avg_conceded': df['weighted_goals_conceded'].mean(),
        'last_rest_days': df['days_rest'].iloc[-1],
        'opponent_classes_faced': df['opponent_class'].unique()
    }

def calculate_fair_odds(home_metrics, away_metrics):
    """Calculate fair odds using Poisson distribution with class weights"""
    home_avg = home_metrics['weighted_avg_scored']
    away_avg = away_metrics['weighted_avg_scored']
    
    home_win = sum(poisson.pmf(i, home_avg) * poisson.sf(i, away_avg) for i in range(0, 10))
    draw = sum(poisson.pmf(i, home_avg) * poisson.pmf(i, away_avg) for i in range(0, 10))
    away_win = 1 - home_win - draw
    
    return {
        'home': 1 / home_win,
        'draw': 1 / draw,
        'away': 1 / away_win,
        'probabilities': {
            'home': home_win,
            'draw': draw,
            'away': away_win
        }
    }

def football_black_scholes(current_odds, fair_odds, home_vol, away_vol, home_rest, away_rest):
    """Adapted Black-Scholes model for football betting"""
    def rest_to_T(days):
        return 1 / (1 + np.exp(-days / 7))  # Sigmoid scaling
    
    T_home = rest_to_T(home_rest)
    T_away = rest_to_T(away_rest)
    T_draw = (T_home + T_away) / 2
    
    # Adjust risk-free rates by outcome probability
    r_base = 0.05
    r_home = r_base * fair_odds['probabilities']['home'] / (fair_odds['probabilities']['home'] + fair_odds['probabilities']['draw'])
    r_draw = r_base * fair_odds['probabilities']['draw'] / (fair_odds['probabilities']['home'] + fair_odds['probabilities']['draw'])
    r_away = r_base - r_home - r_draw
    
    def bs_formula(S, K, sigma, T, r):
        d1 = (np.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    C_home = bs_formula(current_odds['home'], fair_odds['home'], home_vol, T_home, r_home)
    C_draw = bs_formula(current_odds['draw'], fair_odds['draw'], (home_vol + away_vol)/2, T_draw, r_draw)
    C_away = bs_formula(current_odds['away'], fair_odds['away'], away_vol, T_away, r_away)
    
    return {
        'home': C_home,
        'draw': C_draw,
        'away': C_away,
        'time_factors': {
            'home': T_home,
            'away': T_away,
            'draw': T_draw
        }
    }

def analyze_real_madrid_vs_alaves(market_odds):
    """Analyze the specific match using exact match counts"""
    try:
        print("=== Real Madrid vs Alavés Analysis ===")
        print(f"Using data from:\n{RM_PATH}\n{ALAVES_PATH}")
        
        # Load exactly 25 RM matches and 24 Alavés matches
        rm_df, alaves_df = load_specific_matches()
        
        # Calculate metrics
        rm_metrics = calculate_team_metrics(rm_df, "Real Madrid")
        alaves_metrics = calculate_team_metrics(alaves_df, "Alavés")
        
        print(f"\nReal Madrid Metrics (from {rm_metrics['matches_used']} matches):")
        print(f"- Weighted avg goals scored: {rm_metrics['weighted_avg_scored']:.2f}")
        print(f"- Weighted avg goals conceded: {rm_metrics['weighted_avg_conceded']:.2f}")
        print(f"- Volatility: {rm_metrics['volatility']:.2f}")
        print(f"- Last rest days: {rm_metrics['last_rest_days']}")
        print(f"- Opponent classes faced: {sorted(rm_metrics['opponent_classes_faced'])}")
        
        print(f"\nAlavés Metrics (from {alaves_metrics['matches_used']} matches):")
        print(f"- Weighted avg goals scored: {alaves_metrics['weighted_avg_scored']:.2f}")
        print(f"- Weighted avg goals conceded: {alaves_metrics['weighted_avg_conceded']:.2f}")
        print(f"- Volatility: {alaves_metrics['volatility']:.2f}")
        print(f"- Last rest days: {alaves_metrics['last_rest_days']}")
        print(f"- Opponent classes faced: {sorted(alaves_metrics['opponent_classes_faced'])}")
        
        # Calculate fair odds
        fair_odds = calculate_fair_odds(rm_metrics, alaves_metrics)
        
        # Apply Black-Scholes model
        bs_values = football_black_scholes(
            market_odds, 
            fair_odds, 
            rm_metrics['volatility'], 
            alaves_metrics['volatility'],
            rm_metrics['last_rest_days'],
            alaves_metrics['last_rest_days']
        )
        
        # Generate report
        home_goals = round(poisson.ppf(0.5, rm_metrics['weighted_avg_scored']))
        away_goals = round(poisson.ppf(0.5, alaves_metrics['weighted_avg_scored']))
        
        report = {
            'predicted_score': f"{home_goals}-{away_goals}",
            'fair_odds': fair_odds,
            'market_odds': market_odds,
            'valuation': bs_values,
            'recommendations': []
        }
        
        for outcome in ['home', 'draw', 'away']:
            value = bs_values[outcome] - market_odds[outcome]
            if value > 0:
                stake_pct = 100 * value / market_odds[outcome]
                report['recommendations'].append({
                    'outcome': outcome,
                    'odds': market_odds[outcome],
                    'value': value,
                    'stake_pct': stake_pct,
                    'edge': f"{value/market_odds[outcome]*100:.1f}%"
                })
        
        return report
        
    except Exception as e:
        print(f"\nError analyzing match: {str(e)}")
        return None

def print_report(report):
    """Print detailed analysis report"""
    if not report:
        return
    
    print("\n=== Analysis Results ===")
    print(f"\nPredicted Score: {report['predicted_score']}")
    
    print("\nFair Odds vs Market Odds:")
    print(f"{'Outcome':<8} {'Market':>10} {'Model Fair':>10} {'Value':>10} {'Edge':>10}")
    for outcome in ['home', 'draw', 'away']:
        market = report['market_odds'][outcome]
        fair = report['fair_odds'][outcome]
        value = report['valuation'][outcome] - market
        edge = value/market*100 if market else 0
        print(f"{outcome.capitalize():<8} {market:>10.2f} {fair:>10.2f} {value:>+10.2f} {edge:>9.1f}%")
    
    if report['recommendations']:
        print("\nRecommended Bets:")
        for rec in report['recommendations']:
            print(f"- {rec['outcome'].capitalize():<6} @ {rec['odds']:.2f} (Value: +{rec['value']:.2f}, Edge: {rec['edge']}, Stake: {rec['stake_pct']:.1f}%)")
    else:
        print("\nNo value bets identified at current odds")
    
    print("\nModel Parameters:")
    print(f"Time Factors - Home: {report['valuation']['time_factors']['home']:.2f}, "
          f"Away: {report['valuation']['time_factors']['away']:.2f}, "
          f"Draw: {report['valuation']['time_factors']['draw']:.2f}")

# Main execution
if __name__ == "__main__":
    # Market odds for Real Madrid vs Alavés
    market_odds = {
        'home': 1.36,  # Real Madrid
        'draw': 4.90,
        'away': 9.50   # Alavés
    }
    
    # Run analysis
    report = analyze_real_madrid_vs_alaves(market_odds)
    
    # Print results
    print_report(report)


def analyze_match_with_bs(home_csv: str, away_csv: str, market_odds: dict):
    """
    Loads the two CSVs, computes metrics, fair odds, BS valuations, and returns the report.
    """
    rm_df, al_df = load_specific_matches()   # uses RM_PATH / ALAVES_PATH internally
    return analyze_real_madrid_vs_alaves(market_odds)
