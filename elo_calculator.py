import numpy as np
import re

# Rank Elo mapping
rank_values = {
    "Iron": 1000, "Bronze": 1200, "Silver": 1400, "Gold": 1600,
    "Platinum": 1800, "Emerald": 2000, "Diamond": 2200,
    "Master": 2500, "Grandmaster": 2700, "Challenger": 3000
}

pop_means = {'win_rate': 50, 'kda': 2.5, 'gold_per_minute': 400, 'damage_per_minute': 500}
pop_std = {'win_rate': 10, 'kda': 1.0, 'gold_per_minute': 100, 'damage_per_minute': 200}

def convert_rank_to_elo(rank_str):
    import re
    match = re.match(r"(\w+) (\d) \((\d+)LP\)", rank_str)
    if not match:
        return 1500
    tier, division, lp = match.groups()
    base = rank_values.get(tier, 1500)
    bonus = (4 - int(division)) * 50
    return base + bonus + int(lp)

def convert_to_elo(value, metric):
    try:
        value = float(value)
    except:
        value = pop_means[metric]
    z = (value - pop_means[metric]) / pop_std[metric]
    return 1500 + z * 100

def calculate_player_elo(player):
    rank_elo = convert_rank_to_elo(player.get("rank", "Unranked"))
    winrate_elo = convert_to_elo(player.get("general_winrate", 50), "win_rate")
    kda_elo = convert_to_elo(player.get("kda", 2.5), "kda")
    gpm_elo = convert_to_elo(player.get("gold_per_minute", 400), "gold_per_minute")
    dpm_elo = convert_to_elo(player.get("damage_per_minute", 500), "damage_per_minute")

    total_elo = rank_elo  # ✅ Baseline Elo stays absolute

    # ✅ Stat deviations are relative adjustments
    total_elo += (winrate_elo - 1500) * 0.5
    total_elo += (kda_elo - 1500) * 0.05
    total_elo += (gpm_elo - 1500) * 0.25
    total_elo += (dpm_elo - 1500) * 0.1

    return total_elo

def expected_win_probability(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def calculate_team_probabilities(team1, team2):
    import numpy as np

    team1_elos = [calculate_player_elo(p) for p in team1]
    team2_elos = [calculate_player_elo(p) for p in team2]

    avg_elo_team1 = np.mean(team1_elos)
    avg_elo_team2 = np.mean(team2_elos)

    prob1 = expected_win_probability(avg_elo_team1, avg_elo_team2)
    prob2 = 1 - prob1

    return (
        {
            "team1_win_probability": round(prob1 * 100, 2),
            "team2_win_probability": round(prob2 * 100, 2)
        },
        {
            "team1_win_probability": None,
            "team2_win_probability": None
        }
    )
