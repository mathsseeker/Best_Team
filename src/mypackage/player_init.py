import pandas as pd
from get_player_stats import get_player_stats
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PlayerStats:
    """Class to organize player statistics"""
    def __init__(self, games, shots, goals, passes, defenses, fouls, cards, subs, dribbles, duels, penalties):
        self.games = games
        self.shots = shots
        self.goals = goals
        self.passes = passes
        self.defenses = defenses
        self.fouls = fouls
        self.cards = cards
        self.subs = subs
        self.dribbles = dribbles
        self.duels = duels
        self.penalties = penalties


class Player:
    # Adjusted weights for Spanish football (La Liga) with available stats
    BASE_WEIGHTS = {
        'passing': {
            'total': 0.0020,
            'key': 0.030,
            'accuracy': 0.025
        },
        'shooting': {
            'total': 0.0025,
            'on_target': 0.035,
            'goals': 0.40
        },
        'creativity': {
            'assists': 0.40,
            'dribbles': 0.0030,
            'fouls_drawn': 0.010
        },
        'defensive': {
            'tackles': 0.0040,
            'interceptions': 0.0030,
            'duels': 0.0030
        },
        'discipline': {
            'fouls': -0.015,
            'cards': -0.10
        }
    }

    def __init__(self, player_name, player_id, age, height, weight, nationality, team_name, stats):
        self.player_id = player_id
        self.player_name = player_name
        self.age = age
        self.height = height
        self.weight = weight
        self.nationality = nationality
        self.team_name = team_name
        self.stats = stats

    def calculate_passing_score(self):
        total_passes = self.stats.passes.get('total', 0)
        key_passes = self.stats.passes.get('key', 0)
        accuracy = self.stats.passes.get('accuracy', 0)

        return (
            total_passes * self.BASE_WEIGHTS['passing']['total'] +
            key_passes * self.BASE_WEIGHTS['passing']['key'] +
            accuracy * self.BASE_WEIGHTS['passing']['accuracy']
        )

    def calculate_shooting_score(self):
        total_shots = self.stats.shots.get('total', 0)
        shots_on_target = self.stats.shots.get('on', 0)
        goals = self.stats.goals.get('total', 0)

        return (
            total_shots * self.BASE_WEIGHTS['shooting']['total'] +
            shots_on_target * self.BASE_WEIGHTS['shooting']['on_target'] +
            goals * self.BASE_WEIGHTS['shooting']['goals']
        )

    def calculate_creativity_score(self):
        assists = self.stats.goals.get('assists', 0)
        dribbles = self.stats.dribbles.get('success', 0)
        fouls_drawn = self.stats.fouls.get('drawn', 0)

        return (
            assists * self.BASE_WEIGHTS['creativity']['assists'] +
            dribbles * self.BASE_WEIGHTS['creativity']['dribbles'] +
            fouls_drawn * self.BASE_WEIGHTS['creativity']['fouls_drawn']
        )

    def calculate_defensive_score(self):
        tackles = self.stats.defenses.get('tackles', 0)
        interceptions = self.stats.defenses.get('interceptions', 0)
        duels = self.stats.duels.get('won', 0)

        return (
            tackles * self.BASE_WEIGHTS['defensive']['tackles'] +
            interceptions * self.BASE_WEIGHTS['defensive']['interceptions'] +
            duels * self.BASE_WEIGHTS['defensive']['duels']
        )

    def calculate_discipline_score(self):
        fouls = self.stats.fouls.get('committed', 0)
        cards = self.stats.cards.get('yellow', 0) + self.stats.cards.get('red', 0)

        return (
            fouls * self.BASE_WEIGHTS['discipline']['fouls'] +
            cards * self.BASE_WEIGHTS['discipline']['cards']
        )

    def compute_rating(self):
        raise NotImplementedError("Subclasses must implement rating logic")

    def __str__(self):
        return (f"{self.player_name} ({self.stats.games.get('position', 'Unknown')}) | "
                f"Rating: {self.compute_rating():.2f} | "
                f"Apps: {self.stats.games.get('appearances', 0)}")

    @classmethod
    def from_api(cls, player_id, season, team_filter=None):
        df = get_player_stats(player_id, season)
        if df.empty:
            raise ValueError("No data found for the given player and season.")

        if team_filter:
            df = df[df['team_name'].str.contains(team_filter, case=False, na=False)].copy()
            if df.empty:
                raise ValueError(f"No data found for player with team: {team_filter}")

        # Standardize column names
        df = df.rename(columns={
            'appearences': 'appearances',
            'shots_on': 'shots_on_goal',
            'passes_accuracy': 'passes_pct',
            'tackles_interceptions': 'interceptions'
        })

        # Convert numeric columns 
        numeric_cols = [
            'appearances', 'minutes', 'shots_total', 'shots_on_goal',
            'goals_total', 'goals_conceded', 'goals_saves',
            'passes_total', 'passes_key', 'passes_pct',
            'tackles_total', 'interceptions', 'fouls_committed',
            'cards_yellow', 'cards_red', 'goals_assists',
            'dribbles_success', 'fouls_drawn', 'duels_total', 'duels_won',
            'penalty_scored', 'penalty_missed', 'penalty_saved'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Get first record (assuming single player/season combo)
        data = df.iloc[0].to_dict()

        # Handle missing or malformed height and weight
        def parse_measurement(value, unit):
            if pd.isna(value) or value is None:
                return 0
            try:
                if isinstance(value, str):
                    return int(value.split(unit)[0].strip())
                return int(value)
            except (ValueError, AttributeError):
                return 0

        height = parse_measurement(data.get('player_height'), 'cm')
        weight = parse_measurement(data.get('player_weight'), 'kg')

        # Initialize PlayerStats with goalkeeper data
        stats = PlayerStats(
            games={
                'appearances': data.get('appearances', 0),
                'minutes': data.get('minutes', 0),
                'position': data.get('position', 'Unknown'),
                'lineups': data.get('lineups', 0)
            },
            shots={
                'total': data.get('shots_total', 0),
                'on': data.get('shots_on_goal', 0)
            },
            goals={
                'total': data.get('goals_total', 0),
                'assists': data.get('goals_assists', 0),
                'conceded': data.get('goals_conceded', 0),  
                'saves': data.get('goals_saves', 0)          
            },
            passes={
                'total': data.get('passes_total', 0),
                'key': data.get('passes_key', 0),
                'accuracy': data.get('passes_pct', 0)
            },
            defenses={
                'tackles': data.get('tackles_total', 0),
                'interceptions': data.get('interceptions', 0)
            },
            fouls={
                'committed': data.get('fouls_committed', 0),
                'drawn': data.get('fouls_drawn', 0)
            },
            cards={
                'yellow': data.get('cards_yellow', 0),
                'red': data.get('cards_red', 0)
            },
            subs={
                'in': data.get('substitutes_in', 0),
                'out': data.get('substitutes_out', 0),
                'bench': data.get('substitutes_bench', 0)
            },
            dribbles={
                'success': data.get('dribbles_success', 0)
            },
            duels={
                'total': data.get('duels_total', 0),
                'won': data.get('duels_won', 0)
            },
            penalties={
                'scored': data.get('penalty_scored', 0),
                'missed': data.get('penalty_missed', 0),
                'saved': data.get('penalty_saved', 0)  
            }
        )

        position = str(data.get('position', '')).lower()
        if 'goalkeeper' in position:
            return Goalkeeper(
                player_id=int(player_id),
                player_name=data.get('player_name', 'Unknown'),
                age=data.get('player_age', '0'),
                height=height,
                weight=weight,
                nationality=data.get('player_nationality', 'Unknown'),
                team_name=data.get('team_name', 'Unknown'),
                stats=stats
            )
        elif 'defender' in position:
            return Defender(
                player_id=int(player_id),
                player_name=data.get('player_name', 'Unknown'),
                age=data.get('player_age', '0'),
                height=height,
                weight=weight,
                nationality=data.get('player_nationality', 'Unknown'),
                team_name=data.get('team_name', 'Unknown'),
                stats=stats
            )
        elif 'midfielder' in position:
            return Midfielder(
                player_id=int(player_id),
                player_name=data.get('player_name', 'Unknown'),
                age=data.get('player_age', '0'),
                height=height,
                weight=weight,
                nationality=data.get('player_nationality', 'Unknown'),
                team_name=data.get('team_name', 'Unknown'),
                stats=stats
            )
        else:  # Default to attacker for any other position
            return Attacker(
                player_id=int(player_id),
                player_name=data.get('player_name', 'Unknown'),
                age=data.get('player_age', '0'),
                height=height,
                weight=weight,
                nationality=data.get('player_nationality', 'Unknown'),
                team_name=data.get('team_name', 'Unknown'),
                stats=stats
            )


class Goalkeeper(Player):
    def compute_rating(self):
        saves = self.stats.goals.get('saves', 0)
        penalty_saves = self.stats.penalties.get('saved', 0)
        conceded = self.stats.goals.get('conceded', 0)
        pass_accuracy = self.stats.passes.get('accuracy', 0)

        save_score = saves * self.BASE_WEIGHTS['shooting']['on_target']
        penalty_score = penalty_saves * 0.5  # Custom weight for penalty saves
        conceded_score = conceded * -0.02  # Custom weight for goals conceded
        pass_score = pass_accuracy * self.BASE_WEIGHTS['passing']['accuracy']

        total = save_score + penalty_score + conceded_score + pass_score
        return max(total, 0)  # Ensure rating isn't negative


class Defender(Player):
    def compute_rating(self):
        pass_score = self.calculate_passing_score() * 1.3
        defensive_score = self.calculate_defensive_score() * 1.5
        discipline_score = self.calculate_discipline_score()
        
        base_rating = pass_score + defensive_score + discipline_score
        return base_rating


class Midfielder(Player):
    def compute_rating(self):
        pass_score = self.calculate_passing_score() * 1.8
        creativity_score = self.calculate_creativity_score() * 1.5
        defensive_score = self.calculate_defensive_score()
        discipline_score = self.calculate_discipline_score()
        
        base_rating = pass_score + creativity_score + defensive_score + discipline_score
        return base_rating


class Attacker(Player):
    def compute_rating(self):
        shoot_score = self.calculate_shooting_score() * 1.5
        pass_score = self.calculate_passing_score() * 1.2
        creativity_score = self.calculate_creativity_score() * 1.3
        discipline_score = self.calculate_discipline_score()
        
        base_rating = shoot_score + pass_score + creativity_score + discipline_score
        return base_rating