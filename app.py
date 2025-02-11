import time

from flask import Flask, render_template, jsonify
from scraper import scrape_latest_matches, get_combined_player_data
from database import save_match_data, get_match_history, get_match_data, init_db


app = Flask(__name__)

init_db()


@app.route("/", methods=["GET"])
def index():
    """Fetches and processes matches multiple times to collect more data."""
    total_scraped_matches = 0
    for i in range(3):  # ✅ Repeat 3 times
        print(f"🔄 Scraping batch {i + 1}/3...")

        latest_matches = scrape_latest_matches()

        if not latest_matches:
            print("❌ No matches found!")
        else:
            for server, nickname in latest_matches:
                combined_data = get_combined_player_data(server, nickname)
                if combined_data:
                    save_match_data(server, combined_data)
                    total_scraped_matches += 1

        if i < 2:  # ✅ Wait 10 minutes before scraping again (skip on last iteration)
            print("⏳ Waiting 10 minutes before scraping next batch...")
            time.sleep(600)  # 10 minutes

    print(f"✅ Finished scraping {total_scraped_matches} matches in total!")

    return render_template("index.html", message="✅ Matches processed!", matches=get_match_history())


@app.route("/match/<int:match_id>")
def view_match(match_id):
    """Displays match details."""
    match_data = get_match_data(match_id)
    return jsonify(match_data if match_data else {"error": "Match not found!"})

if __name__ == "__main__":
    try:
        init_db()  # Ensure database initializes
        app.run(debug=True)
    except Exception as e:
        print(f"❌ ERROR STARTING APP: {e}")
