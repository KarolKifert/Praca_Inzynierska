from flask import Flask, render_template, request
from scraper import get_combined_player_data  # Import your scraper functions

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        nickname_input = request.form["nickname"]
        server = request.form["server"]

        # Validate input
        if not nickname_input or not server:
            return render_template("index.html", error="Please fill in all fields.")

        # Extract nickname and hashtag
        if "-" in nickname_input:
            nickname, hashtag = nickname_input.split("-", 1)
        else:
            return render_template("index.html", error="Invalid nickname format. Use nickname-hashtag.")

        # Process input (run the scraper)
        try:
            player_data = get_combined_player_data(server, nickname_input)  # Pass full input
        except Exception as e:
            return render_template("index.html", error=f"Scraping error: {str(e)}")

        return render_template("index.html", player_data=player_data)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
