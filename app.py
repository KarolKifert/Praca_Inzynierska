from flask import Flask, render_template, request, redirect, url_for
from scraper import scrape_match_for_summoner
from database import save_match_data_to_db, get_match_history, get_match_data, get_match_by_id
from elo_calculator import calculate_team_probabilities
from database import init_db

init_db()

app = Flask(__name__)

@app.route('/')
def index():
    matches = get_match_history()
    return render_template('index.html', matches=matches)

@app.route('/match/<int:match_id>')
def match_details(match_id):
    match = get_match_by_id(match_id)
    players = get_match_data(match_id)
    return render_template("match_details.html", match=match, players=players)


@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    riot_id = request.form['riot_id']
    server = request.form['server']

    if '#' not in riot_id:
        print("❌ Invalid Riot ID format.")
        return redirect(url_for('index'))

    riot_name, tag = riot_id.split('#')

    print(f"🔍 Starting match scan for {riot_name}#{tag} on {server}")
    players_data = scrape_match_for_summoner(riot_name, tag, server)

    if not players_data:
        print("❌ Could not retrieve player data.")
        return redirect(url_for('index'))

    # Calculate win probabilities
    team1 = players_data[:5]
    team2 = players_data[5:]
    weighted, bayesian = calculate_team_probabilities(team1, team2)

    # Save data to DB
    match_id = save_match_data_to_db(players_data, weighted, bayesian, riot_name, server)

    return redirect(url_for('match_details', match_id=match_id))


if __name__ == '__main__':
    app.run(debug=True)
