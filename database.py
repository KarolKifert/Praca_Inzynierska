import sqlite3
from datetime import datetime
from elo_calculator import calculate_player_elo
import numpy as np

DB_PATH = "matches.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            summoner TEXT NOT NULL,
            server TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            team1_win_probability REAL,
            team2_win_probability REAL,
            team1_win_probability_bayes REAL,
            team2_win_probability_bayes REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            champion TEXT NOT NULL,
            rank TEXT,
            general_winrate REAL,
            champion_winrate REAL,
            kda REAL,
            gold_per_minute REAL,
            damage_per_minute REAL,
            FOREIGN KEY (match_id) REFERENCES matches(match_id)
        )
    """)

    conn.commit()
    conn.close()

def save_match_data_to_db(players_data, weighted, bayesian, summoner_name, server):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO matches (summoner, server, timestamp, team1_win_probability, team2_win_probability,
                             team1_win_probability_bayes, team2_win_probability_bayes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (summoner_name, server, timestamp,
          weighted['team1_win_probability'], weighted['team2_win_probability'],
          bayesian['team1_win_probability'], bayesian['team2_win_probability']))

    match_id = cursor.lastrowid

    for player in players_data:
        cursor.execute("""
            INSERT INTO players (match_id, nickname, champion, rank, general_winrate,
                                 champion_winrate, kda, gold_per_minute, damage_per_minute)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (match_id, player['nickname'], player['champion'], player['rank'],
              player['general_winrate'], player['champion_winrate'], player['kda'],
              player['gold_per_minute'], player['damage_per_minute']))

    conn.commit()
    conn.close()
    return match_id

def get_match_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT summoner, timestamp, server, match_id
        FROM matches
        ORDER BY timestamp DESC
    """)
    matches = cursor.fetchall()
    conn.close()
    return matches

def get_match_data(match_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nickname, rank, champion, general_winrate, champion_winrate,
               kda, gold_per_minute, damage_per_minute
        FROM players
        WHERE match_id = ?
    """, (match_id,))
    players = cursor.fetchall()
    conn.close()

    cols = ["nickname", "rank", "champion", "general_winrate", "champion_winrate",
            "kda", "gold_per_minute", "damage_per_minute"]

    player_dicts = [dict(zip(cols, p)) for p in players]
    player_elos = [round(calculate_player_elo(p), 2) for p in player_dicts]

    team1_elo = round(np.mean(player_elos[:5]), 2)
    team2_elo = round(np.mean(player_elos[5:]), 2)

    team1 = [players[i] + (player_elos[i], team1_elo) for i in range(5)]
    team2 = [players[i] + (player_elos[i], team2_elo) for i in range(5, 10)]

    return team1 + team2


def get_match_by_id(match_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM matches WHERE match_id = ?
    """, (match_id,))
    match = cursor.fetchone()
    conn.close()
    return match
