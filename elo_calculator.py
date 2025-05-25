import numpy as np
import re

# === Base Elo mapping by rank tier ===
rank_values = {
    "Iron": 1000, "Bronze": 1200, "Silver": 1400, "Gold": 1600,
    "Platinum": 1800, "Emerald": 2000, "Diamond": 2200,
    "Master": 2500, "Grandmaster": 2700, "Challenger": 3000
}

# === Population means & standard deviations for performance stats ===
pop_means = {
    'win_rate': 50,
    'kda': 2.5,
    'gold_per_minute': 400,
    'damage_per_minute': 500
}

pop_std = {
    'win_rate': 10,
    'kda': 1.0,
    'gold_per_minute': 100,
    'damage_per_minute': 200
}

# === Stat impact weights for Elo adjustment ===
stat_weights = {
    'win_rate': 50,
    'kda': 10,
    'gold_per_minute': 25,
    'damage_per_minute': 15
}


def convert_rank_to_elo(rank_str):
    """
    Convert a textual rank like 'Gold II (89 LP)' into a numeric Elo base value.
    """
    match = re.match(r"(\w+) (\d) \((\d+)LP\)", rank_str)
    if not match:
        return 1500  # Fallback Elo for unranked or invalid format
    tier, division, lp = match.groups()
    base = rank_values.get(tier, 1500)
    bonus = (4 - int(division)) * 50  # Division I is best
    return base + int(lp) + bonus


def z_score(value, metric):
    """
    Convert a raw stat value into a z-score (standard deviation from the mean).
    """
    try:
        value = float(value)
    except:
        value = pop_means[metric]
    return (value - pop_means[metric]) / pop_std[metric]


def calculate_player_elo(player):
    """
    Compute the player's overall Elo based on:
    - Absolute rank Elo
    - Adjustments from performance stats using z-scores and weights
    """
    rank_elo = convert_rank_to_elo(player.get("rank", "Unranked"))

    # z-scores for stats
    winrate_z = z_score(player.get("general_winrate", 50), "win_rate")
    kda_z = z_score(player.get("kda", 2.5), "kda")
    gpm_z = z_score(player.get("gold_per_minute", 400), "gold_per_minute")
    dpm_z = z_score(player.get("damage_per_minute", 500), "damage_per_minute")

    # Final Elo = rank base + stat-based adjustments
    total_elo = rank_elo
    total_elo += winrate_z * stat_weights["win_rate"]
    total_elo += kda_z * stat_weights["kda"]
    total_elo += gpm_z * stat_weights["gold_per_minute"]
    total_elo += dpm_z * stat_weights["damage_per_minute"]

    return total_elo


def expected_win_probability(elo_a, elo_b):
    """
    Standard Elo-based expected win chance.
    """
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def calculate_team_probabilities(team1, team2):
    """
    Calculates both weighted and Bayesian win probabilities based on team Elo values.
    """
    team1_elos = [calculate_player_elo(p) for p in team1]
    team2_elos = [calculate_player_elo(p) for p in team2]

    mean1 = np.mean(team1_elos)
    mean2 = np.mean(team2_elos)

    # Weighted (Elo-based)
    prob1 = expected_win_probability(mean1, mean2)
    prob2 = 1 - prob1

    # Bayesian (accounts for team Elo variance)
    var1 = np.var(team1_elos) + 100
    var2 = np.var(team2_elos) + 100
    diff = mean1 - mean2
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
