from flask import Flask, render_template, request, jsonify
from scraper import get_combined_player_data
from database import save_match_data, get_match_history, get_match_data
from elo_calculator import calculate_match_probability

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        server = request.form["server"]
        nickname = request.form["nickname"]

        combined_data = get_combined_player_data(server, nickname)

        if combined_data:
            team1 = combined_data[:5]
            team2 = combined_data[5:]

            match_probabilities = calculate_match_probability(team1, team2)

            save_match_data(server, combined_data, match_probabilities)

            message = "Match data successfully saved!"
        else:
            message = "Failed to retrieve match data."

        return render_template("index.html", message=message, matches=get_match_history())

    return render_template("index.html", matches=get_match_history())

@app.route("/match/<int:match_id>")
def view_match(match_id):
    match_data = get_match_data(match_id)
    if match_data:
        return jsonify(match_data)
    return jsonify({"error": "Match not found!"})

if __name__ == "__main__":
    app.run(debug=True)
