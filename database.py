import sqlite3
from datetime import datetime
from elo_calculator import calculate_match_probabilities
from scraper import scrape_match_for_summoner, get_combined_player_data, scrape_champion_stats
from elo_calculator import calculate_player_bayesian_elo

DB_PATH = "matches.db"


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

    cursor.execute("""
        INSERT INTO matches (timestamp, server, team1_win_probability, team2_win_probability,
                            team1_win_probability_bayes, team2_win_probability_bayes, json_file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, server, 0, 0, 0, 0, f"data/matches/match_{timestamp}.json"))

    match_id = cursor.lastrowid

    for player in players_data:
        nickname = player.get("nickname", "Unknown")
        champion = player.get("champion", "Unknown")
        rank = player.get("rank", "Unranked")

        champ_stats = scrape_champion_stats(server, nickname, champion)
        player.update(champ_stats)

        win_rate = player.get("general_winrate", 50)
        champ_win_rate = player.get("champion_winrate", 50)
        kda = player.get("kda", 2.5)
        gold = player.get("gold_per_minute", 400)
        damage = player.get("damage_per_minute", 500)

        cursor.execute("""
            INSERT INTO players (nickname, rank, win_rate, kda, gold_per_minute, damage_per_minute)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nickname, rank, win_rate, kda, gold, damage))
        player_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO match_player_data (match_id, player_id, champion, general_winrate, champion_winrate, kda, gold_per_minute, damage_per_minute)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (match_id, player_id, champion, win_rate, champ_win_rate, kda, gold, damage))

    conn.commit()

    # ✅ Add debugging before using match_prob_elo
    match_prob_elo, match_prob_bayes = calculate_match_probabilities(match_id, conn)

    print(f"[DEBUG] match_prob_elo: {match_prob_elo} ({type(match_prob_elo)})")
    print(f"[DEBUG] match_prob_bayes: {match_prob_bayes} ({type(match_prob_bayes)})")

    if not isinstance(match_prob_elo, dict):
        raise TypeError(f"❌ Expected dictionary but got {type(match_prob_elo)}: {match_prob_elo}")

    if not isinstance(match_prob_bayes, dict):
        raise TypeError(f"❌ Expected dictionary but got {type(match_prob_bayes)}: {match_prob_bayes}")

    cursor.execute("""
        UPDATE matches 
        SET team1_win_probability = ?, team2_win_probability = ?,
            team1_win_probability_bayes = ?, team2_win_probability_bayes = ?
        WHERE match_id = ?
    """, (match_prob_elo["team1_win_probability"], match_prob_elo["team2_win_probability"],
          match_prob_bayes["team1_win_probability"], match_prob_bayes["team2_win_probability"],
          match_id))

    conn.commit()
    conn.close()
    print(f"✅ Match data saved! Probabilities computed after all data was inserted.")


def get_match_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT match_id, timestamp, server, team1_win_probability, team2_win_probability, team1_win_probability_bayes, team2_win_probability_bayes FROM matches ORDER BY timestamp DESC")
    matches = cursor.fetchall()
    conn.close()
    return matches


def get_match_data(match_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ✅ Correctly fetch data by joining match_player_data with players
    cursor.execute("""
        SELECT p.nickname, p.rank, mp.champion, mp.general_winrate, 
               mp.champion_winrate, mp.kda, mp.gold_per_minute, mp.damage_per_minute
        FROM match_player_data mp
        JOIN players p ON mp.player_id = p.player_id  -- ✅ Fetch nickname & rank from players
        WHERE mp.match_id = ?
    """, (match_id,))

    players = cursor.fetchall()
    conn.close()

    player_list = []
    for player in players:
        try:
            general_winrate = float(player[3]) if player[3] is not None else 50.0
        except:
            print(f"⚠️ Warning: Could not convert general win rate for {player[0]}, setting to default 50.0")
            general_winrate = 50.0

        try:
            champion_winrate = float(player[4]) if player[4] is not None else 50.0
        except:
            print(f"⚠️ Warning: Could not convert champion win rate for {player[0]}, setting to default 50.0")
            champion_winrate = 50.0

        player_data = {
            "nickname": player[0],
            "rank": player[1],
            "champion": player[2],
            "general_winrate": general_winrate,
            "champion_winrate": champion_winrate,
            "kda": float(player[5]) if player[5] is not None else 2.5,
            "gold_per_minute": float(player[6]) if player[6] is not None else 400,
            "damage_per_minute": float(player[7]) if player[7] is not None else 500
        }

        player_elo = calculate_player_bayesian_elo(player_data)

        player_list.append((
            player[0],  # Nickname
            player[1],  # Rank
            player[2],  # Champion
            general_winrate,  # General Win Rate
            champion_winrate,  # Champion Win Rate
            player[5],  # KDA
            player[6],  # Gold/Minute
            player[7],  # Damage/Minute
            round(player_elo, 2)  # Computed Elo (rounded)
        ))

    return player_list





if __name__ == "__main__":
    matches = scrape_match_for_summoner()
    for server, nickname in matches:
        data = get_combined_player_data(server, nickname)
        save_match_data_to_db(server, data)
        print(f"✅ Match for {nickname} saved to database!")