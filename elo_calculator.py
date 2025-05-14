import numpy as np

# Elo configuration
weights = {
    'win_rate': 0.5,
    'rank_elo': 0.1,
    'kda': 0.05,
    'gold_per_minute': 0.25,
    'damage_per_minute': 0.1
}

rank_values = {
    "Iron": 1000, "Bronze": 1200, "Silver": 1400, "Gold": 1600,
    "Platinum": 1800, "Emerald": 2000, "Diamond": 2200,
    "Master": 2500, "Grandmaster": 2700, "Challenger": 3000
}

pop_means = {'win_rate': 50, 'rank_elo': 1500, 'kda': 2.5, 'gold_per_minute': 400, 'damage_per_minute': 500}
pop_std = {'win_rate': 10, 'rank_elo': 300, 'kda': 1.0, 'gold_per_minute': 100, 'damage_per_minute': 200}

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
    win_rate_elo = convert_to_elo(player.get("general_winrate", 50), "win_rate")
    kda_elo = convert_to_elo(player.get("kda", 2.5), "kda")
    gold_elo = convert_to_elo(player.get("gold_per_minute", 400), "gold_per_minute")
    dmg_elo = convert_to_elo(player.get("damage_per_minute", 500), "damage_per_minute")

    return (
        rank_elo * weights["rank_elo"] +
        win_rate_elo * weights["win_rate"] +
        kda_elo * weights["kda"] +
        gold_elo * weights["gold_per_minute"] +
        dmg_elo * weights["damage_per_minute"]
    )

def expected_win_probability(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def calculate_team_probabilities(team1, team2):
    team1_elo = np.mean([calculate_player_elo(p) for p in team1])
    team2_elo = np.mean([calculate_player_elo(p) for p in team2])

    prob1 = expected_win_probability(team1_elo, team2_elo)
    prob2 = 1 - prob1

    var1 = np.var([calculate_player_elo(p) for p in team1]) + 100
    var2 = np.var([calculate_player_elo(p) for p in team2]) + 100
    diff = team1_elo - team2_elo
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
