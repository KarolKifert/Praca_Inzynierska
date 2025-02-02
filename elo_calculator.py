import numpy as np
import re

# Updated weights for Elo calculation model
weights = {
    'win_rate': 0.4,
    'rank_elo': 0.3,
    'kda': 0.15,
    'gold_per_minute': 0.1,
    'damage_per_minute': 0.05
}

# Rank point system for conversion
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

# **1️⃣ Convert rank into Elo**
def convert_rank_to_elo(rank_str):
    try:
        match = re.match(r"(\w+) (\d) \((\d+)LP\)", rank_str)
        if not match:
            return 1500  # Default Elo for unranked or invalid format

        tier, division, lp = match.groups()
        base_elo = rank_values.get(tier, 1500)  # Default if tier is missing
        division = int(division)
        lp = int(lp)

        division_bonus = (4 - division) * 50  # Higher division gets more Elo
        return base_elo + division_bonus + lp
    except Exception as e:
        print(f"❌ Error converting rank '{rank_str}': {e}")
        return 1500  # Default Elo fallback

# **2️⃣ Clean numerical values (Remove `/m`, `%`, `\nXX%`)**
def clean_numeric_value(value):
    try:
        if isinstance(value, str):
            value = re.sub(r"[^0-9.]", "", value.split("\n")[0])  # Removes non-numeric characters
        return float(value) if value else 0
    except Exception as e:
        print(f"❌ Error cleaning numeric value '{value}': {e}")
        return 0

# **3️⃣ Calculate player Elo**
def calculate_elo(player_metrics, population_means, population_std, base_elo=1500, scaling=100):
    composite = 0
    for metric in weights:
        if metric == "rank_elo":
            metric_value = convert_rank_to_elo(player_metrics.get("rank", "Unranked"))
        else:
            metric_value = clean_numeric_value(player_metrics.get(metric, 0))

        if metric_value == "N/A" or metric_value == "":
            continue  # Skip invalid values

        try:
            z = (metric_value - population_means[metric]) / population_std[metric]
            composite += z * weights[metric]
        except Exception as e:
            print(f"❌ Error processing metric {metric}: {metric_value} -> {e}")

    return base_elo + composite * scaling

# **4️⃣ Compute win probability**
def expected_win_probability(elo_team1, elo_team2):
    return 1 / (1 + 10 ** ((elo_team2 - elo_team1) / 400))

# **5️⃣ Calculate match probability using team Elo averages**
def calculate_match_probability(team1, team2, pop_means, pop_std):
    team1_elo = np.mean([calculate_elo(player, pop_means, pop_std) for player in team1])
    team2_elo = np.mean([calculate_elo(player, pop_means, pop_std) for player in team2])

    prob_team1 = expected_win_probability(team1_elo, team2_elo)
    prob_team2 = 1 - prob_team1

    return {
        "team1_elo": round(team1_elo, 2),
        "team2_elo": round(team2_elo, 2),
        "team1_win_probability": round(prob_team1 * 100, 2),
        "team2_win_probability": round(prob_team2 * 100, 2)
    }

# **6️⃣ Population means & standard deviations (Adjustable based on real data)**
pop_means = {
    'win_rate': 50,  # Percentage
    'rank_elo': 1500,  # Default Elo for unranked
    'kda': 2.5,
    'gold_per_minute': 400,
    'damage_per_minute': 500
}
pop_std = {
    'win_rate': 10,
    'rank_elo': 300,
    'kda': 1.0,
    'gold_per_minute': 100,
    'damage_per_minute': 200
}

# **7️⃣ Example match data (Simulated scraped data)**
team1 = [
    {'win_rate': "60", 'rank': 'Diamond 1 (45LP)', 'kda': "3.5", 'gold_per_minute': "500/m", 'damage_per_minute': "600/m"},
    {'win_rate': "55", 'rank': 'Diamond 2 (30LP)', 'kda': "2.8", 'gold_per_minute': "470/m", 'damage_per_minute': "590/m"},
    {'win_rate': "50", 'rank': 'Platinum 1 (80LP)', 'kda': "2.6", 'gold_per_minute': "450/m", 'damage_per_minute': "560/m"},
    {'win_rate': "52", 'rank': 'Emerald 3 (20LP)', 'kda': "2.7", 'gold_per_minute': "430/m", 'damage_per_minute': "520/m"},
    {'win_rate': "58", 'rank': 'Emerald 1 (10LP)', 'kda': "3.2", 'gold_per_minute': "510/m", 'damage_per_minute': "580/m"}
]

team2 = [
    {'win_rate': "48", 'rank': 'Platinum 2 (50LP)', 'kda': "2.3", 'gold_per_minute': "420/m", 'damage_per_minute': "480/m"},
    {'win_rate': "50", 'rank': 'Platinum 3 (75LP)', 'kda': "2.5", 'gold_per_minute': "430/m", 'damage_per_minute': "500/m"},
    {'win_rate': "49", 'rank': 'Emerald 4 (10LP)', 'kda': "2.4", 'gold_per_minute': "440/m", 'damage_per_minute': "490/m"},
    {'win_rate': "51", 'rank': 'Diamond 4 (5LP)', 'kda': "2.6", 'gold_per_minute': "460/m", 'damage_per_minute': "510/m"},
    {'win_rate': "47", 'rank': 'Platinum 1 (20LP)', 'kda': "2.2", 'gold_per_minute': "410/m", 'damage_per_minute': "470/m"}
]

# **8️⃣ Match probability calculation**
match_result = calculate_match_probability(team1, team2, pop_means, pop_std)
print("Match Probability:", match_result)
