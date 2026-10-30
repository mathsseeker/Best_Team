# Best Team Project

Automated selection of the best possible Spanish national football
team: live player stats from a football API are scored with a
weighted-metrics + Random Forest pipeline (SMOTE for class
imbalance), and the top-ranked player is picked for each position to
assemble the optimal starting eleven.

## What it does

The pipeline pulls player and team data from a football API, cleans
and preprocesses it, computes a per-player rating from weighted
performance metrics, and then picks the top-ranked player for each
position (goalkeeper, defender, midfielder, attacker) to assemble an
optimal starting eleven. Feature weights are learned with a Random
Forest; SMOTE handles the class imbalance between winning and losing
matches.

## Project layout

```
.
├── src/mypackage/
│   ├── get_player_stats.py       Fetch raw player stats from the API
│   ├── get_players_ids.py        Resolve player identifiers
│   ├── get_team_stats.py         Fetch team-level match stats
│   ├── get_top_players.py        Rank players by position
│   ├── player_init.py            Player data classes / initialisation
│   ├── winning_parameters.py     Weighted scoring + feature importance
│   └── main.py                   Entry point for the full pipeline
│
├── tests/                        Unit tests for data collection + ranking
├── environment 2.yml             Conda environment specification
├── setup.py                      Package metadata
└── README.md
```

## Setup

```bash
# Clone and enter
git clone git@github.com:mathsseeker/Best_Team.git
cd Best_Team

# Create the conda environment (named "football-analytics")
conda env create -f "environment 2.yml"
conda activate football-analytics

# Install the local package in editable mode
pip install -e .

# Run the pipeline
python src/mypackage/main.py
```

The data collection step reads an API key from a `.env` file in the
project root (loaded via `python-dotenv`). Create one with:

```
FOOTBALL_API_KEY=your_key_here
```

## Status

Course project for the Mathematical Modeling Lab (IE, Year 2, Q2).
Early-stage; interfaces and scoring weights are still being iterated.

## Authors

- [@mathsseeker](https://github.com/mathsseeker) — Ricardo Pérez Pérez-Piñeiro
- [@apayanieu](https://github.com/apayanieu) — Alfonso Payán Callejas
