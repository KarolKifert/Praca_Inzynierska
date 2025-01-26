import sqlite3
from datetime import datetime


def init_db():
    conn = sqlite3.connect("match_data.db")
    cursor = conn.cursor()

    # Create the table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME,
        nickname TEXT,
        champion TEXT,
        rank TEXT,
        player_winrate TEXT,
        champion_winrate TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def save_data_to_db(players_data):
    conn = sqlite3.connect("match_data.db")
    cursor = conn.cursor()

    for player in players_data:
        cursor.execute("""
        INSERT INTO match_data (timestamp, nickname, champion, rank, player_winrate, champion_winrate)
        VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now(),
            player["nickname"],
            player["champion"],
            player["rank"],
            player["winrate"],
            player["champion_winrate"]
        ))

    conn.commit()
    conn.close()
    print("Data saved successfully to the database.")
