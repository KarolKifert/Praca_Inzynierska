from flask import Flask, render_template, jsonify
import threading
from scraper import get_combined_player_data, scrape_latest_matches
from database import save_match_data_to_db, get_match_history, get_match_data

app = Flask(__name__)

def run_scraper():
    """Scrapes one match and one player only."""
    print("🔵 Running scraper for one match...")
    server, nickname = scrape_latest_matches()[0]  # Get the first match only
    combined_data = get_combined_player_data(server, nickname)
    if combined_data:
        save_match_data_to_db(server, combined_data)
        print(f"✅ Match saved for {nickname} on {server}")

@app.route("/", methods=["GET"])
def index():
    matches = get_match_history()
    return render_template("index.html", matches=matches)

@app.route("/start_scraping", methods=["POST"])
def start_scraping():
    thread = threading.Thread(target=run_scraper)
    thread.start()
    return jsonify({"status": "Scraping started!"})

@app.route("/match/<int:match_id>")
def view_match(match_id):
    players = get_match_data(match_id)
    return render_template("match_details.html", players=players)

if __name__ == "__main__":
    app.run(debug=True)
