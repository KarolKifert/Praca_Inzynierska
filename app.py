from flask import Flask, render_template, request, jsonify
from scraper import scrape_latest_matches, get_combined_player_data
from database import save_match_data, get_match_history, get_match_data

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    """Fetches latest matches, processes them, and displays match history."""
    # Scrape latest 5 matches from Porofessor
    latest_matches = scrape_latest_matches()

    if not latest_matches:
        message = "❌ No matches found!"
        matches = get_match_history()
        return render_template("index.html", message=message, matches=matches)

    for server, nickname in latest_matches:
        print(f"🔄 Processing match: {nickname} on {server}")

        # Scrape player & champion data
        combined_data = get_combined_player_data(server, nickname)
        if not combined_data:
            print(f"❌ Failed to retrieve data for {nickname} on {server}")
            continue  # Skip this match if no data found

        # ✅ Save match data (probabilities now computed in database.py)
        save_match_data(server, combined_data)
        print(f"✅ Match successfully saved for {nickname} on {server}")

    # Fetch the updated match history and display it
    matches = get_match_history()
    message = "✅ Matches processed successfully!"
    return render_template("index.html", message=message, matches=matches)


@app.route("/match/<int:match_id>")
def view_match(match_id):
    """Displays match details."""
    match_data = get_match_data(match_id)
    if match_data:
        return jsonify(match_data)
    return jsonify({"error": "Match not found!"})


if __name__ == "__main__":
    app.run(debug=True)
