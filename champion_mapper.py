import os
import json
import requests
from datetime import datetime, timedelta

CACHE_FILE = "champion_id_map.json"
CACHE_EXPIRY_HOURS = 24

def fetch_champion_id_map():
    print("🔄 Fetching champion ID mapping from Riot Data Dragon...")

    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(version_url).json()
    current_version = versions[0]

    champion_data_url = f"https://ddragon.leagueoflegends.com/cdn/{current_version}/data/en_US/champion.json"
    champions_data = requests.get(champion_data_url).json()["data"]

    champion_id_map = {}
    for champ_key, champ_info in champions_data.items():
        champ_id = int(champ_info['key'])
        champ_name = champ_info['id']
        champion_id_map[champ_id] = champ_name

    # Save to cache
    with open(CACHE_FILE, "w") as f:
        json.dump({
            "fetched_at": datetime.now().isoformat(),
            "version": current_version,
            "data": champion_id_map
        }, f)

    print(f"✅ Champion ID mapping fetched and cached (version {current_version})")
    return champion_id_map

def load_champion_id_map():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            fetched_at = datetime.fromisoformat(cache.get("fetched_at", "1970-01-01T00:00:00"))
            if datetime.now() - fetched_at < timedelta(hours=CACHE_EXPIRY_HOURS):
                return cache["data"]

    return fetch_champion_id_map()

_champion_id_map = load_champion_id_map()

def get_champion_name(champion_id):
    return _champion_id_map.get(champion_id, f"Unknown({champion_id})")
