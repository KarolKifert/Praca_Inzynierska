import os
import json
import requests
from datetime import datetime, timedelta

CACHE_FILE = "champion_id_map.json"
CACHE_EXPIRY_HOURS = 24  # Refresh cache once a day

def fetch_champion_id_map():
    print("🔄 Fetching champion mapping from Riot Data Dragon...")
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(version_url).json()
    current_version = versions[0]

    champ_data_url = f"https://ddragon.leagueoflegends.com/cdn/{current_version}/data/en_US/champion.json"
    champions = requests.get(champ_data_url).json()["data"]

    # Build mapping: champ_id (as str) -> champion name
    champion_id_map = {info["key"]: info["id"] for info in champions.values()}

    with open(CACHE_FILE, "w") as f:
        json.dump({
            "fetched_at": datetime.now().isoformat(),
            "version": current_version,
            "data": champion_id_map
        }, f)

    print(f"✅ Champion mapping cached (version {current_version})")
    return champion_id_map

def load_champion_id_map():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            fetched_at = datetime.fromisoformat(cache.get("fetched_at", "1970-01-01T00:00:00"))
            if datetime.now() - fetched_at < timedelta(hours=CACHE_EXPIRY_HOURS):
                return cache["data"]
    # Cache missing or expired → fetch fresh
    return fetch_champion_id_map()

# Load once at import
_champion_id_map = load_champion_id_map()

def get_champion_name(champ_id):
    return _champion_id_map.get(str(champ_id), f"Unknown({champ_id})")

# For manual refresh (optional)
def refresh_champion_map():
    global _champion_id_map
    _champion_id_map = fetch_champion_id_map()
    print("✅ Champion mapping refreshed manually.")

# Example test run
if __name__ == "__main__":
    print(get_champion_name(64))  # Should print 'LeeSin'
    print(get_champion_name(555))  # Should print 'Pyke'
