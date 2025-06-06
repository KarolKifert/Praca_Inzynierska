import sqlite3
import matplotlib.pyplot as plt
import numpy as np


def load_match_probabilities():
    conn = sqlite3.connect("matches.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT team1_win_probability, team1_win_probability_bayes
        FROM matches
        ORDER BY timestamp ASC
    """)
    results = cursor.fetchall()
    conn.close()

    weighted = [r[0] for r in results]
    bayesian = [r[1] for r in results]
    return weighted, bayesian


def plot_scatter_with_dashed_lines(weighted, bayesian):
    x = np.arange(1, len(weighted) + 1)

    plt.figure(figsize=(12, 6))

    # Punkty
    plt.scatter(x, weighted, label="Weighted Elo", marker='o', color='blue')
    plt.scatter(x, bayesian, label="Bayesian", marker='x', color='orange')

    # Przerywane linie między punktami
    plt.plot(x, weighted, linestyle='--', color='blue', alpha=0.5)
    plt.plot(x, bayesian, linestyle='--', color='orange', alpha=0.5)

    plt.title("Porównanie prawdopodobieństw zwycięstwa Team 1 (Weighted vs Bayesian)")
    plt.xlabel("Numer meczu")
    plt.ylabel("Prawdopodobieństwo Team 1 [%]")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("probability_comparison_scatter_dashed.png")
    plt.show()


if __name__ == "__main__":
    weighted, bayesian = load_match_probabilities()
    plot_scatter_with_dashed_lines(weighted, bayesian)
