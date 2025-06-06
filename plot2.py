import sqlite3
import matplotlib.pyplot as plt
import numpy as np


def fake_elo(rank, winrate, kda, gpm, dpm):
    try:
        base = 1500
        lp = int(rank.split("(")[-1].replace("LP)", "").strip())
        return base + lp + float(winrate) + float(kda) * 10 + float(gpm) + float(dpm) * 0.1
    except:
        return 1500


def load_variances_and_deltas():
    conn = sqlite3.connect("matches.db")
    cur = conn.cursor()

    cur.execute("SELECT match_id FROM matches ORDER BY timestamp ASC")
    match_ids = [row[0] for row in cur.fetchall()]

    cur.execute("""
        SELECT team1_win_probability, team1_win_probability_bayes, 
               team2_win_probability, team2_win_probability_bayes
        FROM matches ORDER BY timestamp ASC
    """)
    probs = cur.fetchall()
    conn.commit()

    variances, deltas = [], []
    for i, match_id in enumerate(match_ids):
        cur.execute(
            "SELECT rank, general_winrate, kda, gold_per_minute, damage_per_minute FROM players WHERE match_id = ?",
            (match_id,))
        rows = cur.fetchall()
        if len(rows) != 10: continue
        elos = [fake_elo(*r) for r in rows]
        var1, var2 = np.var(elos[:5]), np.var(elos[5:])
        variances.append((var1 + var2) / 2)
        try:
            w1, b1, w2, b2 = probs[i]
            delta = (abs(w1 - b1) + abs(w2 - b2)) * 10

            deltas.append(delta)
        except:
            continue
    conn.close()
    return variances[:len(deltas)], deltas


def plot_variance_vs_difference(variances, deltas):
    plt.figure(figsize=(10, 6))
    plt.scatter(variances, deltas, alpha=0.7, color='purple')
    plt.title("Różnica modeli vs. wariancja Elo drużyn")
    plt.xlabel("Średnia wariancja Elo w meczu")
    plt.ylabel("Średnia różnica predykcji [%]")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("elo_variance_vs_model_difference.png")
    plt.show()


if __name__ == "__main__":
    v, d = load_variances_and_deltas()
    plot_variance_vs_difference(v, d)
