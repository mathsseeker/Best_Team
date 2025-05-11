class Player:
    def __init__(self, name, age, height, weight, team):
        self.name = name
        self.age = age
        self.height = height
        self.weight = weight
        self.team = team

    def compute_rating(self):
        raise NotImplementedError("Subclasses must implement rating logic")

class Goalkeeper(Player):
    def __init__(self, name, age, height, weight, team,
                 goals_conceded=0, goals_saves=0, penalty_saved=0):
        super().__init__(name, age, height, weight, team)
        self.goals_conceded = goals_conceded
        self.goals_saves = goals_saves
        self.penalty_saved = penalty_saved

    def compute_rating(self):
        # Ratio of saves to total shots conceded
        total_shots = self.goals_saves + self.goals_conceded
        save_ratio = (self.goals_saves / total_shots) if total_shots > 0 else 0
        # Base rating from save percentage (0 to 10), plus bonus for penalty saves
        rating = save_ratio * 10 + 0.5 * self.penalty_saved
        return max(0, min(rating, 10))

class Defender(Player):
    pass  # Base for defenders (could hold common methods)

class CentralDefender(Defender):
    def __init__(self, name, age, height, weight, team,
                 tackles_total=0, tackles_blocks=0, tackles_interceptions=0,
                 duels_won=0, duels_total=0):
        super().__init__(name, age, height, weight, team)
        self.tackles_total = tackles_total
        self.tackles_blocks = tackles_blocks
        self.tackles_interceptions = tackles_interceptions
        self.duels_won = duels_won
        self.duels_total = duels_total

    def compute_rating(self):
        actions = self.tackles_total + self.tackles_blocks + self.tackles_interceptions
        # Weight defensive actions and duel success rate
        duel_ratio = (self.duels_won / self.duels_total) if self.duels_total > 0 else 0
        rating = actions * 0.1 + duel_ratio * 5
        return max(0, min(rating, 10))

class Fullback(Defender):
    def __init__(self, name, age, height, weight, team,
                 tackles_total=0, tackles_blocks=0, tackles_interceptions=0,
                 passes_key=0, duels_won=0, duels_total=0, dribbles_success=0):
        super().__init__(name, age, height, weight, team)
        self.tackles_total = tackles_total
        self.tackles_blocks = tackles_blocks
        self.tackles_interceptions = tackles_interceptions
        self.passes_key = passes_key
        self.duels_won = duels_won
        self.duels_total = duels_total
        self.dribbles_success = dribbles_success

    def compute_rating(self):
        defense = self.tackles_total + self.tackles_blocks + self.tackles_interceptions
        duel_ratio = (self.duels_won / self.duels_total) if self.duels_total > 0 else 0
        # Mix defense, support (key passes), and dueling/dribbling
        rating = defense * 0.08 + self.passes_key * 0.2 + duel_ratio * 3 + self.dribbles_success * 0.1
        return max(0, min(rating, 10))

class Midfielder(Player):
    pass  # Base for midfielders

class DefensiveMidfielder(Midfielder):
    def __init__(self, name, age, height, weight, team,
                 tackles_total=0, tackles_interceptions=0, passes_total=0, passes_accuracy=0):
        super().__init__(name, age, height, weight, team)
        self.tackles_total = tackles_total
        self.tackles_interceptions = tackles_interceptions
        self.passes_total = passes_total
        self.passes_accuracy = passes_accuracy

    def compute_rating(self):
        # Focus on defense and passing
        defense = self.tackles_total + self.tackles_interceptions
        rating = defense * 0.2 + self.passes_accuracy * 0.1
        return max(0, min(rating, 10))

class AttackingMidfielder(Midfielder):
    def __init__(self, name, age, height, weight, team,
                 goals_total=0, goals_assists=0,
                 passes_key=0, dribbles_success=0):
        super().__init__(name, age, height, weight, team)
        self.goals_total = goals_total
        self.goals_assists = goals_assists
        self.passes_key = passes_key
        self.dribbles_success = dribbles_success

    def compute_rating(self):
        # Creative and scoring contributions
        rating = (self.goals_total * 0.3 +
                  self.goals_assists * 0.3 +
                  self.passes_key * 0.2 +
                  self.dribbles_success * 0.2)
        return max(0, min(rating, 10))

class Forward(Player):
    pass  # Base for forwards

class Winger(Forward):
    def __init__(self, name, age, height, weight, team,
                 goals_total=0, goals_assists=0,
                 passes_key=0, dribbles_success=0):
        super().__init__(name, age, height, weight, team)
        self.goals_total = goals_total
        self.goals_assists = goals_assists
        self.passes_key = passes_key
        self.dribbles_success = dribbles_success

    def compute_rating(self):
        # Emphasize dribbling and chance creation
        rating = (self.goals_total * 0.2 +
                  self.goals_assists * 0.3 +
                  self.dribbles_success * 0.4 +
                  self.passes_key * 0.1)
        return max(0, min(rating, 10))

class Striker(Forward):
    def __init__(self, name, age, height, weight, team,
                 goals_total=0, goals_assists=0,
                 shots_on=0, penalty_scored=0, penalty_missed=0):
        super().__init__(name, age, height, weight, team)
        self.goals_total = goals_total
        self.goals_assists = goals_assists
        self.shots_on = shots_on
        self.penalty_scored = penalty_scored
        self.penalty_missed = penalty_missed

    def compute_rating(self):
        # Finishing ability and shooting accuracy
        rating = (self.goals_total * 0.3 +
                  self.goals_assists * 0.2 +
                  self.shots_on * 0.1 +
                  self.penalty_scored * 0.5 -
                  self.penalty_missed * 0.5)
        return max(0, min(rating, 10))
