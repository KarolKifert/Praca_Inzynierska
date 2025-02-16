import sqlite3
from datetime import datetime
from elo_calculator import calculate_weighted_elo_probability, calculate_bayesian_elo_probability
from scraper import scrape_latest_matches, get_combined_player_data

DB_PATH = "matches.db"


# Initialize a new database with a stable schema
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            server TEXT NOT NULL,
            team1_win_probability REAL NOT NULL,
            team2_win_probability REAL NOT NULL,
            team1_win_probability_bayes REAL,
            team2_win_probability_bayes REAL,
            json_file_path TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            rank TEXT NOT NULL,
            win_rate REAL,
            kda REAL,
            gold_per_minute REAL,
            damage_per_minute REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE match_player_data (
            match_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            champion TEXT NOT NULL,
            general_winrate REAL,
            champion_winrate REAL,
            kda REAL,
            gold_per_minute REAL,
            damage_per_minute REAL,
            FOREIGN KEY (match_id) REFERENCES matches(match_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ New database initialized successfully!")


def save_match_data_to_db(server, players_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Calculate probabilities before inserting into the database
    team1 = players_data[:5]
    team2 = players_data[5:]
    match_prob_elo = calculate_weighted_elo_probability(team1, team2)
    match_prob_bayes = calculate_bayesian_elo_probability(team1, team2)

    cursor.execute("""
        INSERT INTO matches (timestamp, server, team1_win_probability, team2_win_probability,
                            team1_win_probability_bayes, team2_win_probability_bayes, json_file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, server, match_prob_elo["team1_win_probability"], match_prob_elo["team2_win_probability"],
          match_prob_bayes["team1_win_probability"], match_prob_bayes["team2_win_probability"],
          f"data/matches/match_{timestamp}.json"))

    match_id = cursor.lastrowid

    for player in players_data:
        nickname = player.get("nickname", "Unknown")
        champion = player.get("champion", "Unknown")
        rank = player.get("rank", "Unranked")
        win_rate = player.get("champion_winrate", 0.0)
        kda = player.get("kda", 0.0)
        gold = player.get("gold_per_minute", 0.0)
        damage = player.get("damage_per_minute", 0.0)

        cursor.execute("""
            INSERT INTO players (nickname, rank, win_rate, kda, gold_per_minute, damage_per_minute)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nickname, rank, win_rate, kda, gold, damage))
        player_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO match_player_data (match_id, player_id, champion, general_winrate, champion_winrate, kda, gold_per_minute, damage_per_minute)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (match_id, player_id, champion, None, win_rate, kda, gold, damage))

    conn.commit()
    conn.close()


# Function to fetch match history
def get_match_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT match_id, timestamp, server, team1_win_probability, team2_win_probability, team1_win_probability_bayes, team2_win_probability_bayes FROM matches ORDER BY timestamp DESC")
    matches = cursor.fetchall()
    conn.close()
    return matches


# Function to fetch detailed match data
def get_match_data(match_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.nickname, p.rank, p.win_rate, p.kda, p.gold_per_minute, p.damage_per_minute, mp.champion
        FROM players p
        JOIN match_player_data mp ON p.player_id = mp.player_id
        WHERE mp.match_id = ?
    """, (match_id,))
    players = cursor.fetchall()
    conn.close()

    return players


if __name__ == "__main__":
    matches = scrape_latest_matches()
    for server, nickname in matches:
        data = get_combined_player_data(server, nickname)
        save_match_data_to_db(server, data)
        print(f"✅ Match for {nickname} saved to database!")