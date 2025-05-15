import os
import requests
from urllib.parse import quote
from dotenv import load_dotenv
from champion_mapper import get_champion_name

import asyncio
import aiohttp

load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

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

semaphore = asyncio.Semaphore(5)

async def fetch_match_detail(session, url, headers, puuid):
    async with semaphore:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Failed to fetch match {url}: {resp.status}")
                return None

            data = await resp.json()
            participant = next((p for p in data["info"]["participants"] if p["puuid"] == puuid), None)

            await asyncio.sleep(1.5)  # Throttle requests
            return participant

async def get_recent_match_stats_async(puuid, match_region, champ_id, match_count=10):
    match_ids_url = f"https://{match_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={match_count}"

    async with aiohttp.ClientSession() as session:
        async with session.get(match_ids_url, headers=HEADERS) as ids_res:
            if ids_res.status != 200:
                print(f"❌ Failed to fetch match IDs: {ids_res.status}")
                return default_stats()

            match_ids = await ids_res.json()

        tasks = []
        for match_id in match_ids:
            match_url = f"https://{match_region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            tasks.append(fetch_match_detail(session, match_url, HEADERS, puuid))

        participants_data = await asyncio.gather(*tasks)

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

# ✅ ASYNC compatible wrapper
async def scrape_match_for_summoner(riot_name, tag, server):
    region = REGION_ROUTING.get(server.lower())
    match_region = MATCH_REGION.get(server.lower())
    if not region or not match_region:
        print(f"❌ Invalid server region: {server}")
        return None

    try:
        # Get PUUID
        name_enc = quote(riot_name)
        tag_enc = quote(tag)
        acc_url = f"https://{match_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name_enc}/{tag_enc}"
        acc_res = requests.get(acc_url, headers=HEADERS)
        if acc_res.status_code != 200:
            print(f"❌ Failed to fetch Riot ID: {acc_res.text}")
            return None
        puuid = acc_res.json()["puuid"]

        # Get Active Game
        live_url = f"https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        live_res = requests.get(live_url, headers=HEADERS)
        if live_res.status_code != 200:
            print("❌ Summoner is not in a live game.")
            return None

        game_data = live_res.json()
        participants = game_data.get("participants", [])

        players_data = []

        for participant in participants:
            print(f"\n🟡 Raw participant data: {participant}")

            name = participant.get("summonerName", "Unknown")
            summoner_id = participant.get("summonerId")
            player_puuid = participant.get("puuid")
            champ_id = participant.get("championId")
            champ_name = get_champion_name(champ_id)

            print(f"→ Summoner: {name} | Champ: {champ_name}")

            rank, general_winrate = get_rank_info(summoner_id, region)
            print(f"✅ Rank: {rank}, WR: {general_winrate}%")

            stats = await get_recent_match_stats_async(player_puuid, match_region, champ_id)
            print(f"✅ Stats: KDA {stats['kda']}, GPM {stats['gold_per_minute']}, Champ WR {stats['champion_winrate']} ({stats['champ_games']} games)")

            players_data.append({
                "nickname": name,
                "champion": champ_name,
                "rank": rank,
                "general_winrate": round(general_winrate, 2),
                "champion_winrate": round(stats["champion_winrate"], 2),
                "kda": round(stats["kda"], 2),
                "gold_per_minute": round(stats["gold_per_minute"], 2),
                "damage_per_minute": round(stats["damage_per_minute"], 2),
                "champ_games": stats.get("champ_games", 0)
            })

        return players_data

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
