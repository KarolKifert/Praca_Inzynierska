import sqlite3
import numpy as np


DB_PATH = "matches.db"

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


def fetch_player_data(match_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.nickname, p.rank, p.win_rate, p.kda, p.gold_per_minute, p.damage_per_minute, 
               mp.champion, mp.general_winrate, mp.champion_winrate, mp.kda, mp.gold_per_minute, mp.damage_per_minute
        FROM players p
        JOIN match_player_data mp ON p.player_id = mp.player_id
        WHERE mp.match_id = ?
    """, (match_id,))
    players = cursor.fetchall()
    conn.close()

    player_list = []
    for p in players:
        player_list.append({
            "nickname": p[0],
            "rank": p[1],
            "general_winrate": float(p[7]) if p[7] is not None else 50.0,
            "champion_winrate": float(p[8]) if p[8] is not None else 50.0,
            "kda": float(p[9]) if p[9] is not None else 2.5,
            "gold_per_minute": float(p[10]) if p[10] is not None else 400,
            "damage_per_minute": float(p[11]) if p[11] is not None else 500,
            "champion": p[6]
        })
    return player_list


def convert_rank_to_elo(rank_str):
    rank_values = {
        "Iron": 1000, "Bronze": 1200, "Silver": 1400, "Gold": 1600,
        "Platinum": 1800, "Emerald": 2000, "Diamond": 2200,
        "Master": 2500, "Grandmaster": 2700, "Challenger": 3000
    }
    import re
    match = re.match(r"(\w+) (\d) \((\d+)LP\)", rank_str)
    if not match:
        return 1500  # Default for unranked

    tier, division, lp = match.groups()
    base_elo = rank_values.get(tier, 1500)
    division_bonus = (4 - int(division)) * 50
    return base_elo + division_bonus + int(lp)


def calculate_elo(player_metrics, base_elo=1500, scaling=100):
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


def expected_win_probability(elo_team1, elo_team2):
    return 1 / (1 + 10 ** ((elo_team2 - elo_team1) / 400))


def calculate_weighted_elo_probability(team1, team2):
    team1_elo = np.mean([calculate_elo(player) for player in team1])
    team2_elo = np.mean([calculate_elo(player) for player in team2])

    prob_team1 = expected_win_probability(team1_elo, team2_elo) * 100
    prob_team2 = 100 - prob_team1

    return {
        "team1_win_probability": round(prob_team1, 2),
        "team2_win_probability": round(prob_team2, 2)
    }


def convert_to_elo(value, metric):
    try:
        value = float(value)
    except ValueError:
        print(f"❌ WARNING: Invalid value {value} for {metric}, setting to default.")
        value = pop_means[metric]

    z_score = (value - pop_means[metric]) / pop_std[metric]
    return 1500 + (z_score * 100)


def calculate_player_bayesian_elo(player):
    rank_elo = convert_rank_to_elo(player.get("rank", "Unranked"))

    kda_value = player.get("kda", 2.5)
    if isinstance(kda_value, str) and not kda_value.replace('.', '', 1).isdigit():
        kda_value = 2.5  # ⬅️ Ensuring valid float

    win_rate_elo = convert_to_elo(player.get("win_rate", 50), "win_rate")
    kda_elo = convert_to_elo(kda_value, "kda")
    gold_elo = convert_to_elo(player.get("gold_per_minute", 400), "gold_per_minute")
    damage_elo = convert_to_elo(player.get("damage_per_minute", 500), "damage_per_minute")

    combined_elo = (
        (rank_elo * weights["rank_elo"]) +
        (win_rate_elo * weights["win_rate"]) +
        (kda_elo * weights["kda"]) +
        (gold_elo * weights["gold_per_minute"]) +
        (damage_elo * weights["damage_per_minute"])
    )
    return combined_elo


def calculate_bayesian_elo_probability(team1, team2):
    team1_elos = [calculate_player_bayesian_elo(player) for player in team1]
    team2_elos = [calculate_player_bayesian_elo(player) for player in team2]

    team1_general_winrates = [player.get("general_winrate", 50) for player in team1]
    team1_champ_winrates = [player.get("champion_winrate", 50) for player in team1]
    team2_general_winrates = [player.get("general_winrate", 50) for player in team2]
    team2_champ_winrates = [player.get("champion_winrate", 50) for player in team2]

    mean_team1_winrate = np.mean(team1_general_winrates) * 0.6 + np.mean(team1_champ_winrates) * 0.4
    mean_team2_winrate = np.mean(team2_general_winrates) * 0.6 + np.mean(team2_champ_winrates) * 0.4

    mean_team1 = np.mean(team1_elos) + mean_team1_winrate * 5  # ✅ Weighted winrate contribution
    mean_team2 = np.mean(team2_elos) + mean_team2_winrate * 5

    var_team1 = np.var(team1_elos) + 100
    var_team2 = np.var(team2_elos) + 100

    prob_team1 = 1 / (1 + np.exp(-(mean_team1 - mean_team2) / np.sqrt(var_team1 + var_team2)))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT team1_win_probability, team2_win_probability FROM matches")
    results = cursor.fetchall()
    conn.close()

    if results:
        observed_win_rates = []
        for team1_prob, team2_prob in results:
            elo_diff = team1_prob - team2_prob
            if elo_diff > 0:
                observed_win_rates.append(team1_prob / 100)
            else:
                observed_win_rates.append(team2_prob / 100)

        avg_win_rate_adjustment = np.mean(observed_win_rates) if observed_win_rates else 0.5
        prob_team1 = (prob_team1 * avg_win_rate_adjustment) / (
                prob_team1 * avg_win_rate_adjustment + (1 - prob_team1) * (1 - avg_win_rate_adjustment))

    return {
        "team1_win_probability": round(prob_team1 * 100, 2),
        "team2_win_probability": round((1 - prob_team1) * 100, 2)
    }


def calculate_match_probabilities(match_id, conn):
    print(f"Calculating probabilities for match_id: {match_id}")
    try:
        players = fetch_player_data(match_id)
        if len(players) < 10:
            print(f"⚠️ Warning: Not enough player data for match {match_id}.")
            return {"team1_win_probability": None, "team2_win_probability": None}

        team1, team2 = players[:5], players[5:]

        for player in team1 + team2:
            player["general_winrate"] = player.get("general_winrate", 50)
            player["champion_winrate"] = player.get("champion_winrate", 50)

        print("[DEBUG] Running weighted Elo probability calculation...")
        match_prob_elo = calculate_weighted_elo_probability(team1, team2)
        print(f"[DEBUG] Weighted probabilities computed: {match_prob_elo}")

        print("[DEBUG] Running Bayesian probability calculation...")
        match_prob_bayes = calculate_bayesian_elo_probability(team1, team2)
        print(f"[DEBUG] Bayesian probabilities computed: {match_prob_bayes}")

        print(f"[DEBUG] ✅ Probabilities calculated successfully for match {match_id}")

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE matches 
            SET team1_win_probability = ?, team2_win_probability = ?,
                team1_win_probability_bayes = ?, team2_win_probability_bayes = ?
            WHERE match_id = ?
        """, (match_prob_elo["team1_win_probability"], match_prob_elo["team2_win_probability"],
              match_prob_bayes["team1_win_probability"], match_prob_bayes["team2_win_probability"],
              match_id))
        conn.commit()

        if not isinstance(match_prob_elo, dict):
            raise TypeError(f"❌ ERROR: Expected dictionary but got {type(match_prob_elo)}: {match_prob_elo}")

        if not isinstance(match_prob_bayes, dict):
            raise TypeError(f"❌ ERROR: Expected dictionary but got {type(match_prob_bayes)}: {match_prob_bayes}")

        return match_prob_elo, match_prob_bayes

    except Exception as e:
        print(f"❌ ERROR in calculate_match_probabilities: {e}")
        return {"team1_win_probability": None, "team2_win_probability": None}  # Ensure dictionary return


