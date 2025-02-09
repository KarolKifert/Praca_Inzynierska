import sqlite3
import numpy as np
import re
from sklearn.linear_model import LogisticRegression

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

    prob_team1 = expected_win_probability(team1_elo, team2_elo) * 100  # ✅ Convert to percentage
    prob_team2 = 100 - prob_team1  # ✅ Ensure percentages sum to 100

    return {
        "team1_elo": round(team1_elo, 2),
        "team2_elo": round(team2_elo, 2),
        "team1_win_probability": round(prob_team1, 2),  # ✅ Ensure percentage format
        "team2_win_probability": round(prob_team2, 2)
    }


def calculate_bayesian_elo_probability(team1, team2):
    """Computes probability using Bayesian Elo method."""

    # Convert ranks to Elo values
    team1_elos = [convert_rank_to_elo(player.get("rank", "Unranked")) for player in team1]
    team2_elos = [convert_rank_to_elo(player.get("rank", "Unranked")) for player in team2]

    # Compute mean and variance
    mean_team1 = np.mean(team1_elos)
    mean_team2 = np.mean(team2_elos)

    var_team1 = np.var(team1_elos) + 100  # Adding uncertainty
    var_team2 = np.var(team2_elos) + 100

    # Compute probability using Bayesian inference
    prob_team1 = 1 / (1 + np.exp(-(mean_team1 - mean_team2) / np.sqrt(var_team1 + var_team2)))

    return {
        "team1_win_probability": round(prob_team1 * 100, 2),
        "team2_win_probability": round((1 - prob_team1) * 100, 2)
    }


def train_logistic_model():
    """Train a logistic regression model using available match data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT team1_win_probability, team2_win_probability, 
               team1_win_probability_bayes, actual_winner
        FROM matches
        WHERE actual_winner IS NOT NULL
    """)

    data = cursor.fetchall()
    conn.close()

    if not data:
        return None  # No training data

    # ✅ Convert to NumPy array and filter out NaN values
    data = np.array(data, dtype=np.float64)
    data = data[~np.isnan(data).any(axis=1)]  # ✅ Remove rows that contain NaN

    if data.shape[0] == 0:
        print("❌ No valid training data after removing NaN values!")
        return None

    X = data[:, :-1]  # Features (probabilities)
    y = data[:, -1]   # Labels (actual winners)

    model = LogisticRegression()
    model.fit(X, y)
    print(f"✅ Logistic Regression model trained with {len(X)} matches.")
    return model


# ✅ Ensure we re-train model only if needed
logistic_model = train_logistic_model()


def calculate_logistic_regression_probability(team1, team2):
    """Predicts match probability using logistic regression."""
    global logistic_model

    if logistic_model is None:
        logistic_model = train_logistic_model()

    if logistic_model is None:
        return {"team1_win_probability": 50, "team2_win_probability": 50}

    match_prob_elo = calculate_match_probability(team1, team2)
    match_prob_bayes = calculate_bayesian_elo_probability(team1, team2)

    X_new = np.array([[match_prob_elo["team1_win_probability"],
                       match_prob_elo["team2_win_probability"],
                       match_prob_bayes["team1_win_probability"]]])

    X_new = np.nan_to_num(X_new, nan=50)  # ✅ Replace NaN values with neutral probability

    prediction = logistic_model.predict_proba(X_new)[0]

    return {
        "team1_win_probability": round(prediction[1] * 100, 2),
        "team2_win_probability": round(prediction[0] * 100, 2)
    }


