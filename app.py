import time

from flask import Flask, render_template, jsonify
import threading
from scraper import scrape_latest_matches, get_combined_player_data
from database import save_match_data, get_match_history, get_match_data

app = Flask(__name__)


def run_scraper():
    """Processes matches one by one instead of all at once."""
    print("🔵 Scraper function running...")

    latest_matches = scrape_latest_matches()
    if not latest_matches:
        print("❌ No matches scraped! Something is wrong.")
        return

    for server, nickname in latest_matches:
        print(f"🟡 Processing match for {nickname} on {server}...")

        # ✅ STEP 1: Scrape live match from OP.GG
        combined_data = get_combined_player_data(server, nickname)
        if not combined_data:
            print(f"❌ Failed to retrieve player data for {nickname} on {server}")
            continue  # Skip this match if data is missing

        # ✅ STEP 2: Save match in the database
        save_match_data(server, combined_data)
        print(f"✅ Match successfully saved for {nickname} on {server}")

        # ✅ STEP 3: Wait a few seconds before the next match (to avoid IP bans)
        time.sleep(5)

    print("✅ All matches processed!")


@app.route("/", methods=["GET"])
def index():
    matches = get_match_history()
    return render_template("index.html", matches=matches)

@app.route("/start_scraping", methods=["POST"])
def start_scraping():
    """Starts a new batch of match scraping in the background."""
    thread = threading.Thread(target=run_scraper)
    thread.start()
    return jsonify({"status": "Scraping started!"})

@app.route("/match/<int:match_id>")
def view_match(match_id):
    """Displays match details."""
    match_data = get_match_data(match_id)
    if match_data:
        return jsonify(match_data)
    return jsonify({"error": "Match not found!"})


if __name__ == "__main__":
    app.run(debug=True)
