import os
import requests
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

print("🔑 Loaded API Key:", RIOT_API_KEY)

if not RIOT_API_KEY:
    raise RuntimeError("❌ RIOT_API_KEY not loaded from .env")

HEADERS = {"X-Riot-Token": RIOT_API_KEY}

REGION_ROUTING = {
    "euw": "euw1", "na": "na1", "kr": "kr", "eune": "eun1",
    "lan": "la1", "las": "la2", "oce": "oc1", "ru": "ru", "tr": "tr1", "jp": "jp1"
}

MATCH_REGION = {
    "euw": "europe", "eune": "europe", "na": "americas", "lan": "americas",
    "las": "americas", "oce": "sea", "kr": "asia", "jp": "asia", "ru": "europe", "tr": "europe"
}


def scrape_match_for_summoner(riot_name, tag, server):
    region = REGION_ROUTING.get(server.lower())
    match_region = MATCH_REGION.get(server.lower())
    if not region or not match_region:
        print(f"❌ Invalid server region: {server}")
        return None

    try:
        # 1. Get PUUID from Riot ID
        name_enc = quote(riot_name)
        tag_enc = quote(tag)
        acc_url = f"https://{match_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name_enc}/{tag_enc}"
        acc_res = requests.get(acc_url, headers=HEADERS)
        if acc_res.status_code != 200:
            print(f"❌ Failed to fetch Riot ID: {acc_res.text}")
            return None
        puuid = acc_res.json()["puuid"]

        # 2. Get Live Game Info using PUUID
        live_url = f"https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        live_res = requests.get(live_url, headers=HEADERS)
        if live_res.status_code != 200:
            print("❌ Summoner is not in a live game.")
            return None

        game_data = live_res.json()
        participants = game_data["participants"]
        players_data = []

        for participant in participants:
            name = participant.get("summonerName", "Unknown")
            summoner_id = participant["summonerId"]
            player_puuid = participant["puuid"]
            champ_id = participant["championId"]
            champ_name = get_champion_name_by_id(champ_id)

            print(f"🔍 Processing Player: {name} ({player_puuid}) playing {champ_name}")

            # 1️⃣ Get Ranked Stats (League-V4 by summonerId)
            rank, general_winrate = get_rank_info(summoner_id, region)

            # 2️⃣ Get Recent Match Stats (Match-V5 by puuid)
            stats = asyncio.run(get_recent_match_stats_async(player_puuid, match_region, champ_id))

            # 3️⃣ Build Player Data Entry
            players_data.append({
                "nickname": name,
                "champion": champ_name,
                "rank": rank,
                "general_winrate": round(general_winrate, 2),
                "champion_winrate": round(stats["champion_winrate"], 2),
                "kda": round(stats["kda"], 2),
                "gold_per_minute": round(stats["gold_per_minute"], 2),
                "damage_per_minute": round(stats["damage_per_minute"], 2),
                "champ_games": stats.get("champ_games", 0)  # ✅ Sample size info
            })

        return players_data

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def get_rank_info(summoner_id, region):
    url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return "Unranked", 50.0

    for entry in res.json():
        if entry["queueType"] == "RANKED_SOLO_5x5":
            tier = entry["tier"].capitalize()
            div = entry["rank"]
            lp = entry["leaguePoints"]
            wins = entry["wins"]
            losses = entry["losses"]
            wr = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 50.0
            return f"{tier} {div} ({lp} LP)", wr

    return "Unranked", 50.0


import asyncio
import aiohttp

async def fetch_match_detail(session, url, headers, puuid):
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            print(f"❌ Failed to fetch match {url}: {resp.status}")
            return None
        data = await resp.json()
        participant = next((p for p in data["info"]["participants"] if p["puuid"] == puuid), None)
        return participant

async def get_recent_match_stats_async(puuid, match_region, champ_id, match_count=20):
    match_ids_url = f"https://{match_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={match_count}"

    async with aiohttp.ClientSession() as session:
        async with session.get(match_ids_url, headers=HEADERS) as ids_res:
            if ids_res.status != 200:
                print(f"❌ Failed to fetch match IDs: {ids_res.status}")
                return default_stats()

            match_ids = await ids_res.json()

        # Batch fetch match details concurrently
        tasks = []
        for match_id in match_ids:
            match_url = f"https://{match_region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            tasks.append(fetch_match_detail(session, match_url, HEADERS, puuid))

        participants_data = await asyncio.gather(*tasks)

        # Process stats
        total_kills = total_deaths = total_assists = 0
        total_gpm = total_dpm = 0
        champ_games = champ_wins = 0

        for participant in participants_data:
            if not participant:
                continue

            total_kills += participant.get("kills", 0)
            total_deaths += max(participant.get("deaths", 1), 1)
            total_assists += participant.get("assists", 0)
            total_gpm += participant["goldEarned"] / (participant["timePlayed"] / 60)
            total_dpm += participant["totalDamageDealtToChampions"] / (participant["timePlayed"] / 60)

            if participant["championId"] == champ_id:
                champ_games += 1
                if participant.get("win"):
                    champ_wins += 1

        games_played = len([p for p in participants_data if p])

        return {
            "kda": (total_kills + total_assists) / total_deaths if total_deaths else 2.5,
            "gold_per_minute": total_gpm / games_played if games_played else 400,
            "damage_per_minute": total_dpm / games_played if games_played else 500,
            "champion_winrate": (champ_wins / champ_games) * 100 if champ_games else 50.0,
            "champ_games": champ_games
        }

def default_stats():
    return {
        "kda": 2.5,
        "gold_per_minute": 400,
        "damage_per_minute": 500,
        "champion_winrate": 50.0,
        "champ_games": 0
    }




def get_champion_name_by_id(champ_id):
    CHAMPION_ID_MAP = {
        1: "Annie", 2: "Olaf", 3: "Galio", 4: "TwistedFate", 5: "XinZhao",
        6: "Urgot", 7: "LeBlanc", 8: "Vladimir", 9: "Fiddlesticks", 10: "Kayle",
        11: "MasterYi", 12: "Alistar", 13: "Ryze", 14: "Sion", 15: "Sivir",
        16: "Soraka", 17: "Teemo", 18: "Tristana", 19: "Warwick", 20: "Nunu",
        21: "MissFortune", 22: "Ashe", 23: "Tryndamere", 24: "Jax", 25: "Morgana",
        26: "Zilean", 27: "Singed", 28: "Evelynn", 29: "Twitch", 30: "Karthus",
        31: "Chogath", 32: "Amumu", 33: "Rammus", 34: "Anivia", 35: "Shaco",
        36: "DrMundo", 37: "Sona", 38: "Kassadin", 39: "Irelia", 40: "Janna",
        41: "Gangplank", 42: "Corki", 43: "Karma", 44: "Taric", 45: "Veigar",
        48: "Trundle", 50: "Swain", 51: "Caitlyn", 53: "Blitzcrank", 54: "Malphite",
        55: "Katarina", 56: "Nocturne", 57: "Maokai", 58: "Renekton", 59: "JarvanIV",
        60: "Elise", 61: "Orianna", 62: "Wukong", 63: "Brand", 64: "LeeSin",
        67: "Vayne", 68: "Rumble", 69: "Cassiopeia", 72: "Skarner", 74: "Heimerdinger",
        75: "Nasus", 76: "Nidalee", 77: "Udyr", 78: "Poppy", 79: "Gragas",
        80: "Pantheon", 81: "Ezreal", 82: "Mordekaiser", 83: "Yorick", 84: "Akali",
        85: "Kennen", 86: "Garen", 89: "Leona", 90: "Malzahar", 91: "Talon",
        92: "Riven", 96: "KogMaw", 98: "Shen", 99: "Lux", 101: "Xerath",
        102: "Shyvana", 103: "Ahri", 104: "Graves", 105: "Fizz", 106: "Volibear",
        107: "Rengar", 110: "Varus", 111: "Nautilus", 112: "Viktor", 113: "Sejuani",
        114: "Fiora", 115: "Ziggs", 117: "Lulu", 119: "Draven", 120: "Hecarim",
        121: "Khazix", 122: "Darius", 126: "Jayce", 127: "Lissandra", 131: "Diana",
        133: "Quinn", 134: "Syndra", 136: "AurelionSol", 141: "Kayn", 142: "Zoe",
        143: "Zyra", 145: "Kaisa", 147: "Seraphine", 150: "Gnar", 154: "Zac",
        157: "Yasuo", 161: "Velkoz", 163: "Taliyah", 164: "Camille", 166: "Akshan",
        200: "Belveth", 201: "Braum", 202: "Jhin", 203: "Kindred", 222: "Jinx",
        234: "Viego", 235: "Senna", 236: "Lucian", 238: "Zed", 240: "Kled",
        245: "Ekko", 246: "Qiyana", 254: "Vi", 266: "Aatrox", 267: "Nami",
        268: "Azir", 350: "Yuumi", 360: "Samira", 412: "Thresh", 420: "Illaoi",
        421: "RekSai", 427: "Ivern", 429: "Kalista", 432: "Bard", 497: "Rakan",
        498: "Xayah", 516: "Ornn", 517: "Sylas", 518: "Neeko", 523: "Aphelios",
        526: "Rell", 555: "Pyke", 711: "Vex", 777: "Yone", 875: "Sett",
        876: "Lillia", 887: "Gwen", 888: "Renata", 895: "Nilah", 902: "Milio",
        897: "KSante", 910: "Hwei", 901: "Briar", 223: "TahmKench", 147: "Seraphine",
        164: "Camille", 221: "Zeri", 80: "Pantheon", 517: "Sylas", 895: "Nilah",
        800: "Mel", 950: "Naafiri"
    }
    return CHAMPION_ID_MAP.get(champ_id, f"Unknown({champ_id})")

