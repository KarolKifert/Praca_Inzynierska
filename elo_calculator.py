import numpy as np
import re

# Rank Elo mapping
rank_values = {
    "Iron": 1000, "Bronze": 1200, "Silver": 1400, "Gold": 1600,
    "Platinum": 1800, "Emerald": 2000, "Diamond": 2200,
    "Master": 2500, "Grandmaster": 2700, "Challenger": 3000
}

# Population stats for relative metrics
pop_means = {'win_rate': 50, 'kda': 2.5, 'gold_per_minute': 400, 'damage_per_minute': 500}
pop_std = {'win_rate': 10, 'kda': 1.0, 'gold_per_minute': 100, 'damage_per_minute': 200}

# Influence weights (only for stats, not rank)
weights = {
    'win_rate': 0.5,
    'kda': 0.05,
    'gold_per_minute': 0.25,
    'damage_per_minute': 0.1
}

# Convert rank string to absolute Elo value
def convert_rank_to_elo(rank_str):
    match = re.match(r"(\w+) (\d) \((\d+)LP\)", rank_str)
    if not match:
        return 1500  # Default for unranked
    tier, division, lp = match.groups()
    base = rank_values.get(tier, 1500)
    bonus = (4 - int(division)) * 50
    return base + bonus + int(lp)

# Compute influence of a metric (as deviation from population mean)
def stat_influence(value, metric, weight):
    try:
        value = float(value)
    except:
        value = pop_means[metric]
    z = (value - pop_means[metric]) / pop_std[metric]
    return z * weight * 100  # influence in Elo units

# Compute final player Elo
def calculate_player_elo(player):
    # Rank Elo is raw
    rank_elo = convert_rank_to_elo(player.get("rank", "Unranked"))

    # Stat deviations added on top
    winrate_infl = stat_influence(player.get("general_winrate", 50), "win_rate", weights["win_rate"])
    kda_infl = stat_influence(player.get("kda", 2.5), "kda", weights["kda"])
    gpm_infl = stat_influence(player.get("gold_per_minute", 400), "gold_per_minute", weights["gold_per_minute"])
    dpm_infl = stat_influence(player.get("damage_per_minute", 500), "damage_per_minute", weights["damage_per_minute"])

    total_elo = rank_elo + winrate_infl + kda_infl + gpm_infl + dpm_infl

    return total_elo

# Standard Elo vs Elo win probability
def expected_win_probability(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

# Compute weighted Elo & Bayesian team probabilities
def calculate_team_probabilities(team1, team2):
    team1_elos = [calculate_player_elo(p) for p in team1]
    team2_elos = [calculate_player_elo(p) for p in team2]

    avg_elo_team1 = np.mean(team1_elos)
    avg_elo_team2 = np.mean(team2_elos)

    # Standard weighted Elo probability
    prob1 = expected_win_probability(avg_elo_team1, avg_elo_team2)
    prob2 = 1 - prob1

    # Bayesian winrate correction based on variance
    var1 = np.var(team1_elos) + 100
    var2 = np.var(team2_elos) + 100
    diff = avg_elo_team1 - avg_elo_team2
    bayes1 = 1 / (1 + np.exp(-diff / np.sqrt(var1 + var2)))
    bayes2 = 1 - bayes1

    return (
        {
            "team1_win_probability": round(prob1 * 100, 2),
            "team2_win_probability": round(prob2 * 100, 2)
        },
        {
            "team1_win_probability": round(bayes1 * 100, 2),
            "team2_win_probability": round(bayes2 * 100, 2)
        }
    )
