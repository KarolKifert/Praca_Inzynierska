import os
import sqlite3
import json
import time
from datetime import datetime

from selenium.webdriver.common.by import By

from elo_calculator import calculate_match_probability, calculate_bayesian_elo_probability, \
    calculate_logistic_regression_probability
from scraper import setup_selenium_driver

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

    # ✅ Ensure probability columns exist
    try:
        cursor.execute("ALTER TABLE matches ADD COLUMN team1_win_probability_lr REAL;")
        cursor.execute("ALTER TABLE matches ADD COLUMN team2_win_probability_lr REAL;")
        cursor.execute("ALTER TABLE matches ADD COLUMN team1_win_probability_bayes REAL;")
        cursor.execute("ALTER TABLE matches ADD COLUMN team2_win_probability_bayes REAL;")
        cursor.execute("ALTER TABLE matches ADD COLUMN actual_winner INTEGER DEFAULT NULL;")  # ✅ Add actual_winner
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Columns already exist

    # ✅ Create table to track pending match results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_results (
            match_id INTEGER PRIMARY KEY,
            server TEXT NOT NULL,
            nickname TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (match_id) REFERENCES matches(match_id)
        )
    """)

    # ✅ Ensure `actual_winner` column exists
    try:
        cursor.execute("ALTER TABLE matches ADD COLUMN actual_winner INTEGER DEFAULT NULL;")
        conn.commit()
        print("✅ Added `actual_winner` column to `matches` table.")
    except sqlite3.OperationalError:
        print("✅ `actual_winner` column already exists.")

    conn.close()
    print("✅ Database initialized successfully!")


# ✅ Call at script start
init_db()


def save_match_data(server, players_data):
    """Stores a match and tracks it for result checking later."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_filename = f"data/matches/match_{timestamp}.json"

    team1 = players_data[:5]
    team2 = players_data[5:]

    # ✅ Compute match probabilities
    match_prob_elo = calculate_match_probability(team1, team2)
    match_prob_lr = calculate_logistic_regression_probability(team1, team2)
    match_prob_bayes = calculate_bayesian_elo_probability(team1, team2)

    # ✅ Insert match into the database (10 values for 10 columns)
    cursor.execute("""
        INSERT INTO matches (
            timestamp, server, 
            team1_win_probability, team2_win_probability,
            team1_win_probability_lr, team2_win_probability_lr,
            team1_win_probability_bayes, team2_win_probability_bayes,
            json_file_path, actual_winner
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
    """, (timestamp, server,
          match_prob_elo["team1_win_probability"], match_prob_elo["team2_win_probability"],
          match_prob_lr["team1_win_probability"], match_prob_lr["team2_win_probability"],
          match_prob_bayes["team1_win_probability"], match_prob_bayes["team2_win_probability"],
          json_filename))  # ✅ Added `json_filename` as the 9th value

    match_id = cursor.lastrowid

    # ✅ Store live match for later checking
    cursor.execute("""
        INSERT INTO pending_results (match_id, server, nickname, timestamp)
        VALUES (?, ?, ?, ?)
    """, (match_id, server, players_data[0]["nickname"], timestamp))

    conn.commit()
    conn.close()


def get_match_history():
    """Retrieves all stored matches from the database for displaying in the web interface."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT match_id, timestamp, server, 
               team1_win_probability, team2_win_probability,
               team1_win_probability_lr, team2_win_probability_lr,
               team1_win_probability_bayes, team2_win_probability_bayes
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


def check_pending_results():
    """Periodically checks if pending matches have ended and updates the winner."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT match_id, server, nickname FROM pending_results")
    pending_matches = cursor.fetchall()

    if not pending_matches:
        print("✅ No matches need checking.")
        conn.close()
        return

    for match_id, server, nickname in pending_matches:
        print(f"🔍 Checking match result for {nickname} on {server}...")

        match_result = get_match_result(server, nickname)
        if match_result is not None:
            print(f"✅ Match {match_id} completed! Updating winner.")

            cursor.execute("UPDATE matches SET actual_winner = ? WHERE match_id = ?", (match_result, match_id))
            cursor.execute("DELETE FROM pending_results WHERE match_id = ?", (match_id,))

    conn.commit()
    conn.close()


def get_match_result(server, nickname):
    """Scrapes OP.GG to find out who won the match."""
    url = f"https://www.op.gg/summoners/{server}/{nickname}"
    driver = setup_selenium_driver()

    try:
        print(f"🔄 Checking match history for {nickname} on {server}...")
        driver.get(url)
        time.sleep(5)

        match_result = driver.find_element(By.XPATH, '//div[contains(@class, "GameResult")]').text.strip()
        return 1 if "Victory" in match_result else 0  # ✅ 1 = Team 1 win, 0 = Team 2 win

    except Exception as e:
        print(f"❌ Error checking match result: {e}")
        return None

    finally:
        driver.quit()
