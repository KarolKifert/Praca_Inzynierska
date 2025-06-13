import sqlite3

from matplotlib import pyplot as plt

from plot2 import fake_elo


def plot_model_comparison():
    conn = sqlite3.connect("matches.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT team1_win_probability, team1_win_probability_bayes,
               team2_win_probability, team2_win_probability_bayes
        FROM matches ORDER BY timestamp ASC
    """)
    data = cur.fetchall()
    conn.close()

    team1_weighted = []
    team1_bayes = []
    team2_weighted = []
    team2_bayes = []

    for w1, b1, w2, b2 in data:
        if None in (w1, b1, w2, b2):
            continue
        team1_weighted.append(w1)
        team1_bayes.append(b1)
        team2_weighted.append(w2)
        team2_bayes.append(b2)

    # Wykres rozrzutu dla team1
    plt.figure(figsize=(10, 5))
    plt.scatter(team1_weighted, team1_bayes, alpha=0.6, label='Team 1', color='blue')
    plt.scatter(team2_weighted, team2_bayes, alpha=0.6, label='Team 2', color='red')
    plt.plot([0, 100], [0, 100], '--', color='gray', label='Idealna zgodność')
    plt.xlabel("Predykcja Weighted Elo [%]")
    plt.ylabel("Predykcja Bayesian [%]")
    plt.title("Porównanie modeli predykcji – Team 1 i Team 2")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("model_comparison_scatter.png")
    plt.show()


def plot_prediction_difference_histogram():
    conn = sqlite3.connect("matches.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT team1_win_probability, team1_win_probability_bayes,
               team2_win_probability, team2_win_probability_bayes
        FROM matches
    """)
    data = cur.fetchall()
    conn.close()

    differences = []
    for w1, b1, w2, b2 in data:
        if None in (w1, b1, w2, b2):
            continue
        diff1 = abs(w1 - b1)
        diff2 = abs(w2 - b2)
        differences.extend([diff1, diff2])

    plt.figure(figsize=(10, 5))
    plt.hist(differences, bins=30, color='purple', alpha=0.7)
    plt.xlabel("Różnica między modelami [%]")
    plt.ylabel("Liczba meczów")
    plt.title("Histogram różnic predykcji Weighted vs Bayesian")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("model_difference_histogram.png")
    plt.show()

def plot_models_vs_variance():
    import sqlite3
    import matplotlib.pyplot as plt
    import numpy as np

    conn = sqlite3.connect("matches.db")
    cur = conn.cursor()

    cur.execute("SELECT match_id, team1_win_probability, team1_win_probability_bayes FROM matches ORDER BY timestamp ASC")
    data = cur.fetchall()

    variances = []
    weighted_preds = []
    bayesian_preds = []

    for match_id, w, b in data:
        cur.execute(
            "SELECT rank, general_winrate, kda, gold_per_minute, damage_per_minute FROM players WHERE match_id = ?",
            (match_id,))
        rows = cur.fetchall()
        if len(rows) != 10 or None in (w, b):
            continue
        elos = [fake_elo(*r) for r in rows]
        var1 = np.var(elos[:5])
        var2 = np.var(elos[5:])
        avg_var = (var1 + var2) / 2

        variances.append(avg_var)
        weighted_preds.append(w)
        bayesian_preds.append(b)

    conn.close()

    # Sort for smoother lines
    variances = np.array(variances)
    weighted_preds = np.array(weighted_preds)
    bayesian_preds = np.array(bayesian_preds)

    sorted_idx = np.argsort(variances)
    v_sorted = variances[sorted_idx]
    w_sorted = weighted_preds[sorted_idx]
    b_sorted = bayesian_preds[sorted_idx]

    # Wykres
    plt.figure(figsize=(10, 6))
    plt.plot(v_sorted, w_sorted, label="Weighted Elo", color='blue', marker='o', linestyle='--', alpha=0.6)
    plt.plot(v_sorted, b_sorted, label="Bayesian", color='red', marker='x', linestyle='-', alpha=0.7)
    plt.xlabel("Średnia wariancja Elo w meczu")
    plt.ylabel("Predykcja zwycięstwa Team 1 [%]")
    plt.title("Wpływ rozrzutu siły graczy na predykcję – porównanie modeli")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("models_vs_variance.png")
    plt.show()

if __name__ == "__main__":
    plot_model_comparison()
    plot_prediction_difference_histogram()
    plot_models_vs_variance()