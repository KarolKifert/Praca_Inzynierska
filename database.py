import sqlite3
import json
import os
from datetime import datetime

DATABASE_NAME = "matches.db"


# Initialize the database
# Initialize the database
def initialize_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Create table for storing matches
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            team1_elo REAL,
            team2_elo REAL,
            team1_win_probability REAL,
            team2_win_probability REAL,
            match_data TEXT
        )
    """)

    conn.commit()
    conn.close()


# Save a match entry
def save_match(team1_elo, team2_elo, team1_win_probability, team2_win_probability, match_data):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO matches (timestamp, team1_elo, team2_elo, team1_win_probability, team2_win_probability, match_data)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, team1_elo, team2_elo, team1_win_probability, team2_win_probability, json.dumps(match_data)))

    conn.commit()
    conn.close()


# Retrieve match history
def get_match_history():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, timestamp, team1_elo, team2_elo, team1_win_probability, team2_win_probability, match_data FROM matches ORDER BY timestamp DESC
    """)

    matches = cursor.fetchall()
    conn.close()

    match_history = []
    for match in matches:
        match_id, timestamp, team1_elo, team2_elo, team1_win_probability, team2_win_probability, match_data = match
        match_history.append({
            "id": match_id,
            "timestamp": timestamp,
            "team1_elo": team1_elo,
            "team2_elo": team2_elo,
            "team1_win_probability": team1_win_probability,
            "team2_win_probability": team2_win_probability,
            "match_data": json.loads(match_data)
        })

    return match_history
