from flask import Flask, render_template, request, jsonify
from scraper import scrape_match_for_summoner
from database import save_match_data_to_db, get_match_history, get_match_data

app = Flask(__name__)


def run_scraper(summoner_name, hashtag, server):
    print(f"🔍 Fetching live match for {summoner_name}#{hashtag} on {server}...")

    match_data = scrape_match_for_summoner(summoner_name, hashtag, server)
    if match_data:
        save_match_data_to_db(server, match_data)
        print(f"✅ Match successfully saved for {summoner_name}")
    else:
        print(f"❌ No match found for {summoner_name}")


@app.route("/", methods=["GET"])
def index():
    matches = get_match_history()
    return render_template("index.html", matches=matches)


@app.route("/start_scraping", methods=["POST"])
def start_scraping():
    data = request.json
    summoner_name = data.get("summoner_name")
    hashtag = data.get("hashtag")
    server = data.get("server")

    print(f"[DEBUG] Received scrape request for {summoner_name}#{hashtag} on {server}")

    if not summoner_name or not hashtag or not server:
        print("[DEBUG] Missing required inputs!")
        return jsonify({"error": "Missing required input"}), 400

    match_data = scrape_match_for_summoner(summoner_name, hashtag, server)
    print(f"[DEBUG] Scraper returned: {match_data}")

    if match_data:
        print("[DEBUG] Calling save_match_data_to_db...")
        save_match_data_to_db(server, match_data)
        print("[DEBUG] Match successfully saved!")

    return jsonify({"status": "Scraping complete!"})


@app.route("/match/<int:match_id>")
def view_match(match_id):
    players = get_match_data(match_id)
    return render_template("match_details.html", players=players)


if __name__ == "__main__":
    app.run(debug=True)
