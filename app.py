from flask import Flask, render_template, request, jsonify
from scraper import scrape_players_and_champions
from elo_calculator import calculate_match_probability, pop_means, pop_std
from database import save_match, get_match_history

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        server = request.form["server"]
        nickname = request.form["nickname"]

        # Scrape match data
        players_data, _ = scrape_players_and_champions(server, nickname)

        if not players_data:
            return render_template("index.html", message="Error: Could not fetch match data.")

        # Split into two teams (assuming first 5 players are team 1, next 5 are team 2)
        team1, team2 = players_data[:5], players_data[5:]

        # Calculate match probability
        match_probability = calculate_match_probability(team1, team2, pop_means, pop_std)

        # Save match data
        match_id = save_match(players_data, match_probability)

        return render_template("index.html", match_data=players_data, match_probability=match_probability, match_id=match_id)

    # Fetch match history
    match_history = get_match_history()
    return render_template("index.html", match_history=match_history)

if __name__ == "__main__":
    app.run(debug=True)
