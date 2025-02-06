import os
import sqlite3
import json
from datetime import datetime

DB_PATH = "matches.db"


def init_db():
    """Creates the required database tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ✅ Create matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            server TEXT NOT NULL,
            team1_win_probability REAL NOT NULL,
            team2_win_probability REAL NOT NULL,
            json_file_path TEXT NOT NULL
        )
    """)

    # ✅ Create players table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL UNIQUE,
            server TEXT NOT NULL,
            rank TEXT
        )
    """)

    # ✅ Create match-player relation table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_player_data (
            match_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            champion TEXT NOT NULL,
            general_winrate TEXT,
            champion_winrate TEXT,
            kda TEXT,
            gold_per_minute TEXT,
            damage_per_minute TEXT,
            FOREIGN KEY (match_id) REFERENCES matches(match_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


# Call the function to initialize the database when script runs
init_db()


def save_match_data(server, players_data, match_probabilities):
    """Stores a match and associated player data into the database and JSON file."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ✅ Generate a timestamp and filename for JSON storage
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_filename = f"data/matches/match_{timestamp}.json"

    # ✅ Insert match into the database
    cursor.execute("""
        INSERT INTO matches (timestamp, server, team1_win_probability, team2_win_probability, json_file_path)
        VALUES (?, ?, ?, ?, ?)
    """, (timestamp, server, match_probabilities["team1_win_probability"], match_probabilities["team2_win_probability"],
          json_filename))

    match_id = cursor.lastrowid

    # ✅ Save match data as JSON file
    os.makedirs(os.path.dirname(json_filename), exist_ok=True)  # Ensure directory exists
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(players_data, f, indent=4)

    # ✅ Ensure players are saved properly
    for player in players_data:
        nickname = player.get("nickname", "Unknown")
        champion = player.get("champion", "Unknown")
        rank = player.get("rank", "Unranked")
        general_winrate = player.get("general_winrate", "N/A")
        champion_winrate = player.get("champion_winrate", "N/A")
        kda = player.get("kda", "N/A")
        gold_per_minute = player.get("gold_per_minute", "N/A")
        damage_per_minute = player.get("damage_per_minute", "N/A")

        # ✅ Ensure player exists in database
        cursor.execute("SELECT player_id FROM players WHERE nickname = ?", (nickname,))
        result = cursor.fetchone()

        if result:
            player_id = result[0]
        else:
            cursor.execute("INSERT INTO players (nickname, server, rank) VALUES (?, ?, ?)",
                           (nickname, server, rank))
            player_id = cursor.lastrowid

        # ✅ Insert match-player data
        cursor.execute("""
            INSERT INTO match_player_data 
            (match_id, player_id, champion, general_winrate, champion_winrate, kda, gold_per_minute, damage_per_minute)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (match_id, player_id, champion, general_winrate, champion_winrate, kda, gold_per_minute, damage_per_minute))

    conn.commit()
    conn.close()
    print(f"✅ Match saved successfully! JSON stored at {json_filename}")


def get_match_history():
    """Retrieves all stored matches from the database for displaying in the web interface."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ✅ Retrieve match history
    cursor.execute("""
        SELECT match_id, timestamp, server, team1_win_probability, team2_win_probability
        FROM matches
        ORDER BY timestamp DESC
    """)

    matches = cursor.fetchall()
    conn.close()

    return matches  # Returns list of tuples


def get_match_data(match_id):
    """Retrieves detailed match data from the stored JSON file in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ✅ Get the JSON file path for the match
    cursor.execute("SELECT json_file_path FROM matches WHERE match_id = ?", (match_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        json_file = result[0]
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                match_data = json.load(f)
                return match_data  # Returns detailed match data from JSON file

    return None  # If no data found
