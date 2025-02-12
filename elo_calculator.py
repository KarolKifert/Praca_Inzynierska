import numpy as np
import re
from sklearn.linear_model import LogisticRegression
import sqlite3

DB_PATH = "matches.db"

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
    "Iron": 1000, "Bronze": 1200, "Silver": 1400, "Gold": 1600,
    "Platinum": 1800, "Emerald": 2000, "Diamond": 2200,
    "Master": 2500, "Grandmaster": 2700, "Challenger": 3000
}

# Population means and standard deviations for normalization
pop_means = {'win_rate': 50, 'rank_elo': 1500, 'kda': 2.5, 'gold_per_minute': 400, 'damage_per_minute': 500}
pop_std = {'win_rate': 10, 'rank_elo': 300, 'kda': 1.0, 'gold_per_minute': 100, 'damage_per_minute': 200}


### **1. Rank-to-Elo Conversion**
def convert_rank_to_elo(rank_str):
    """Converts a player's rank into an Elo score."""
    match = re.match(r"(\w+) (\d) \((\d+)LP\)", rank_str)
    if not match:
        return 1500  # Default for unranked

    tier, division, lp = match.groups()
    base_elo = rank_values.get(tier, 1500)
    division_bonus = (4 - int(division)) * 50
    return base_elo + division_bonus + int(lp)


### **2. Weighted Elo Calculation**
def calculate_elo(player_metrics, base_elo=1500, scaling=100):
    """Computes a player's Elo based on weighted attributes."""
    composite = 0
    for metric in weights:
        if metric == "rank_elo":
            metric_value = convert_rank_to_elo(player_metrics.get("rank", "Unranked"))
        else:
            metric_value = player_metrics.get(metric, 0)
            if metric_value is None:
                metric_value = 0

        try:
            metric_value = float(metric_value)
            z = (metric_value - pop_means[metric]) / pop_std[metric]
            composite += z * weights[metric]
        except Exception as e:
            print(f"❌ Error in metric {metric}: {metric_value} -> {e}")

    return base_elo + composite * scaling


### **3. Win Probability (Elo-Based)**
def expected_win_probability(elo_team1, elo_team2):
    """Computes win probability using the Elo rating system."""
    return 1 / (1 + 10 ** ((elo_team2 - elo_team1) / 400))


### **4. Compute Weighted Elo Match Probability**
def calculate_weighted_elo_probability(team1, team2):
    """Computes probability of winning based on weighted Elo scores."""
    team1_elo = np.mean([calculate_elo(player) for player in team1])
    team2_elo = np.mean([calculate_elo(player) for player in team2])

    prob_team1 = expected_win_probability(team1_elo, team2_elo) * 100
    prob_team2 = 100 - prob_team1

    return {
        "team1_win_probability": round(prob_team1, 2),
        "team2_win_probability": round(prob_team2, 2)
    }


### **5. Bayesian Elo Probability Calculation**
def calculate_bayesian_elo_probability(team1, team2):
    """Computes Bayesian probability for a match."""
    team1_elos = [convert_rank_to_elo(player.get("rank", "Unranked")) for player in team1]
    team2_elos = [convert_rank_to_elo(player.get("rank", "Unranked")) for player in team2]

    mean_team1, mean_team2 = np.mean(team1_elos), np.mean(team2_elos)
    var_team1, var_team2 = np.var(team1_elos) + 100, np.var(team2_elos) + 100

    prob_team1 = 1 / (1 + np.exp(-(mean_team1 - mean_team2) / np.sqrt(var_team1 + var_team2)))

    return {
        "team1_win_probability": round(prob_team1 * 100, 2),
        "team2_win_probability": round((1 - prob_team1) * 100, 2)
    }


### **8. Compute & Save Probabilities for a Match**
def calculate_match_probabilities(team1, team2, match_id):
    """Computes and saves three probability methods for a match."""

    match_prob_elo = calculate_weighted_elo_probability(team1, team2)
    match_prob_bayes = calculate_bayesian_elo_probability(team1, team2)

    # ✅ Ensure no None values
    for key in match_prob_elo:
        if match_prob_elo[key] is None:
            match_prob_elo[key] = 50.0  # Neutral 50% probability

    for key in match_prob_bayes:
        if match_prob_bayes[key] is None:
            match_prob_bayes[key] = 50.0

    # ✅ Save probabilities in the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE matches 
        SET 
            team1_win_probability = ?, team2_win_probability = ?, 
            team1_win_probability_bayes = ?, team2_win_probability_bayes = ?, 
            team1_win_probability_lr = ?, team2_win_probability_lr = ?
        WHERE match_id = ?
    """, (match_prob_elo["team1_win_probability"], match_prob_elo["team2_win_probability"],
          match_prob_bayes["team1_win_probability"], match_prob_bayes["team2_win_probability"],
          match_id))

    conn.commit()
    conn.close()
