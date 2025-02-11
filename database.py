import os
import sqlite3
import json
import time
from datetime import datetime

from selenium.webdriver.common.by import By

from elo_calculator import calculate_bayesian_elo_probability, \
    calculate_logistic_regression_probability, calculate_weighted_elo_probability
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
            team1_win_probability_bayes REAL,
            team2_win_probability_bayes REAL,
            team1_win_probability_lr REAL,
            team2_win_probability_lr REAL,
            json_file_path TEXT NOT NULL
        )
    """)

    # ✅ Create players table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            rank TEXT NOT NULL,
            win_rate REAL,
            kda REAL,
            gold_per_minute REAL,
            damage_per_minute REAL,
            FOREIGN KEY (match_id) REFERENCES matches(match_id)
        )
    """)

    conn.commit()
    conn.close()


def save_match_data(server, players_data):
    """Stores match details and associated player stats in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_filename = f"data/matches/match_{timestamp}.json"

    team1 = players_data[:5]
    team2 = players_data[5:]

    # ✅ Compute probabilities
    match_prob_elo = calculate_weighted_elo_probability(team1, team2)
    match_prob_bayes = calculate_bayesian_elo_probability(team1, team2)
    match_prob_lr = calculate_logistic_regression_probability(team1, team2)

    # ✅ Insert match into the database
    cursor.execute("""
        INSERT INTO matches (
            timestamp, server, 
            team1_win_probability, team2_win_probability,
            team1_win_probability_bayes, team2_win_probability_bayes,
            team1_win_probability_lr, team2_win_probability_lr,
            json_file_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, server,
          match_prob_elo["team1_win_probability"], match_prob_elo["team2_win_probability"],
          match_prob_bayes["team1_win_probability"], match_prob_bayes["team2_win_probability"],
          match_prob_lr["team1_win_probability"], match_prob_lr["team2_win_probability"],
          json_filename))

    match_id = cursor.lastrowid

    # ✅ Insert player data
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
            cursor.execute("INSERT INTO players (nickname, server, rank) VALUES (?, ?, ?)", (nickname, server, rank))
            player_id = cursor.lastrowid

        # ✅ Insert match-player data with match_id!
        cursor.execute("""
            INSERT INTO match_player_data 
            (match_id, player_id, champion, general_winrate, champion_winrate, kda, gold_per_minute, damage_per_minute)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id, player_id, champion, general_winrate, champion_winrate, kda, gold_per_minute, damage_per_minute))

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
