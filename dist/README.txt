🏆 League of Legends Match Predictor
------------------------------------

This app predicts win probabilities in a live LoL match using Riot's API.

✅ Shows both teams
✅ Calculates win probabilities (weighted & Bayesian)
✅ Based on real-time ranks and performance stats
✅ No installation needed — just double-click

------------------------------------
📦 How to use:

1. Extract this folder (if zipped)
2. Make sure these files/folders are together:
   - app.exe
   - .env
   - templates/
   - static/
3. Double-click launch.bat (or app.exe)

Your browser will open to http://localhost:5000

------------------------------------
🔐 Riot API Key setup (required!):

1. Go to https://developer.riotgames.com
2. Log in and copy your Development API Key
3. Open the `.env.example` file in Notepad
4. Paste your key like this:

RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

5. Save the file as: `.env` (no `.txt` extension)

❗ If this file is missing or invalid, the app will show an error and exit.

------------------------------------
💡 Tips:

- The key expires every 24 hours (Dev keys)
- You can request a Production Key for unlimited usage
- Works only when the Riot ID is in an active match

------------------------------------
Made with ❤️ by Karol Kifert :)
