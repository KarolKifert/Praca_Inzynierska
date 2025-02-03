import numpy as np
import re

# Weight distribution for probability calculation
weights = {
    'win_rate': 0.4,
    'rank_elo': 0.3,
    'kda': 0.15,
    'gold_per_minute': 0.1,
    'damage_per_minute': 0.05
}

# Rank-to-Elo conversion table
rank_values = {
    "Iron": 1000,
    "Bronze": 1200,
    "Silver": 1400,
    "Gold": 1600,
    "Platinum": 1800,
    "Emerald": 2000,
    "Diamond": 2200,
    "Master": 2500,
    "Grandmaster": 2700,
    "Challenger": 3000
}

# Population means for normalization (estimated real-world averages)
pop_means = {
    'win_rate': 50,  # Percentage
    'rank_elo': 1500,  # Default Elo for unranked
    'kda': 2.5,
    'gold_per_minute': 400,
    'damage_per_minute': 500
}

# Standard deviations for normalization
pop_std = {
    'win_rate': 10,
    'rank_elo': 300,
    'kda': 1.0,
    'gold_per_minute': 100,
    'damage_per_minute': 200
}

def convert_rank_to_elo(rank_str):
    """Converts rank (e.g., 'Diamond 1 (45LP)') into an Elo score."""
    try:
        match = re.match(r"(\w+) (\d) \((\d+)LP\)", rank_str)
        if not match:
            return 1500  # Default Elo if unranked or invalid format

        tier, division, lp = match.groups()
        base_elo = rank_values.get(tier, 1500)
        division = int(division)
        lp = int(lp)

        division_bonus = (4 - division) * 50  # Higher division, higher Elo
        return base_elo + division_bonus + lp
    except Exception as e:
        print(f"❌ Rank conversion error '{rank_str}': {e}")
        return 1500  # Default Elo fallback

def clean_numeric_value(value):
    """Removes '/m', '%', and converts to float."""
    try:
        if isinstance(value, str):
            value = re.sub(r"[^0-9.]", "", value.split("\n")[0])
        return float(value) if value else 0
    except Exception as e:
        print(f"❌ Error cleaning value '{value}': {e}")
        return 0

def calculate_elo(player_metrics, base_elo=1500, scaling=100):
    """Computes a player's Elo based on weighted attributes."""
    composite = 0
    for metric in weights:
        if metric == "rank_elo":
            metric_value = convert_rank_to_elo(player_metrics.get("rank", "Unranked"))
        else:
            metric_value = clean_numeric_value(player_metrics.get(metric, 0))

        if metric_value == "N/A" or metric_value == "":
            continue  # Ignore missing values

        try:
            z = (metric_value - pop_means[metric]) / pop_std[metric]
            composite += z * weights[metric]
        except Exception as e:
            print(f"❌ Error in metric {metric}: {metric_value} -> {e}")

    return base_elo + composite * scaling

def expected_win_probability(elo_team1, elo_team2):
    """Computes probability of Team 1 winning against Team 2."""
    return 1 / (1 + 10 ** ((elo_team2 - elo_team1) / 400))

def calculate_match_probability(team1, team2):
    """Computes probability of winning for each team based on Elo scores."""
    team1_elo = np.mean([calculate_elo(player) for player in team1])
    team2_elo = np.mean([calculate_elo(player) for player in team2])

    prob_team1 = expected_win_probability(team1_elo, team2_elo) * 100  # Convert to percentage
    prob_team2 = (1 - expected_win_probability(team1_elo, team2_elo)) * 100  # Convert to percentage

    return {
        "team1_elo": round(team1_elo, 2),
        "team2_elo": round(team2_elo, 2),
        "team1_win_probability": round(prob_team1, 2),  # Ensure formatted properly
        "team2_win_probability": round(prob_team2, 2)   # Ensure formatted properly
    }

