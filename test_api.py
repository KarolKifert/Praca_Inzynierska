import os
import requests
from urllib.parse import quote
from dotenv import load_dotenv


load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
HEADERS = {"X-Riot-Token": RIOT_API_KEY}

print("🔑 RIOT_API_KEY (from .env):", repr(RIOT_API_KEY))


def lookup_riot_account(riot_name, tag, match_region):
    encoded_name = quote(riot_name)
    encoded_tag = quote(tag)

    url = f"https://{match_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    print(f"🔗 Requesting: {url}")

    response = requests.get(url, headers=HEADERS)
    print(f"📡 Status Code: {response.status_code}")

    try:
        print("📦 Response JSON:", response.json())
    except Exception as e:
        print("❌ Error parsing JSON:", e)
        print("🔻 Raw response:", response.text)


if __name__ == "__main__":
    # 🔁 EXAMPLE INPUT (you can change this!)
    riot_name = "xBoczek"
    tag = "EUW"
    match_region = "europe"  # based on server: "euw" → "europe", "na" → "americas", etc.

    lookup_riot_account(riot_name, tag, match_region)
