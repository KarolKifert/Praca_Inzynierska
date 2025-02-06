import time
import urllib
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ✅ Champion Name Fix Mapping for OP.GG discrepancies
CHAMPION_NAME_FIXES = {
    "MonkeyKing": "Wukong",
    "FiddleSticks": "Fiddlesticks",
    "ChoGath": "Cho'Gath",
    "VelKoz": "Vel'Koz",
    "KhaZix": "Kha'Zix",
    "Nunu": "Nunu & Willump",
    "JarvanIV": "Jarvan IV",
    "RekSai": "Rek'Sai",
    "DrMundo": "Dr. Mundo",
}

def setup_selenium_driver():
    """Sets up Selenium WebDriver with proper options."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    )
    return webdriver.Chrome(options=options)

def scrape_latest_matches():
    """Scrapes the latest 5 live matches from Porofessor."""
    url = "https://porofessor.gg/pl/"
    driver = setup_selenium_driver()
    wait = WebDriverWait(driver, 30)

    try:
        print(f"🔄 Accessing Porofessor live matches page...")
        driver.get(url)
        wait.until(EC.presence_of_all_elements_located((By.XPATH, '//ul[@class="cards-list no-margin-top no-margin-bottom"]/li')))

        match_elements = driver.find_elements(By.XPATH, '//ul[@class="cards-list no-margin-top no-margin-bottom"]/li')

        matches_data = []
        for match in match_elements[:5]:  # ✅ Process only the first 5 matches
            try:
                link_element = match.find_element(By.XPATH, './/a[contains(@class, "liveGameLink")]')
                match_href = link_element.get_attribute("href")  # Example: "/pl/live/euw/Qnoxs-17165"

                # ✅ Extracting `server`, `nickname`, and `hashtag`
                match_parts = match_href.split("/")[-2:]  # Extract last two elements: ["euw", "Qnoxs-17165"]
                server = match_parts[0]  # "euw"
                nickname, hashtag = match_parts[1].rsplit("-", 1)  # "Qnoxs", "17165"

                print(f"✅ Scraped match: Server={server}, Nickname={nickname}, Hashtag={hashtag}")
                matches_data.append((server, f"{nickname}-{hashtag}"))

            except Exception as e:
                print(f"❌ Error extracting match details: {e}")

        return matches_data

    except Exception as e:
        print(f"❌ Error scraping matches: {e}")
        return []

    finally:
        driver.quit()


def scrape_players_and_champions(server, nickname):
    """Scrapes the live match page to get players, their general winrates, ranks, and chosen champions."""
    url = f"https://www.op.gg/summoners/{server}/{nickname}/ingame"
    driver = setup_selenium_driver()
    wait = WebDriverWait(driver, 30)

    try:
        print(f"🔄 Accessing live match page for {nickname} on {server}...")
        driver.get(url)
        wait.until(EC.presence_of_all_elements_located((By.XPATH, '//td[@class="summoner-name"]/a')))
        print("✅ Player table loaded successfully.")

        player_elements = driver.find_elements(By.XPATH, '//td[@class="summoner-name"]/a')

        players_data = []
        champions_in_game = set()

        for player_element in player_elements[:10]:  # Limit to 10 players in match
            player_nickname = player_element.text.strip()
            print(f"🎯 Processing player: {player_nickname}")

            try:
                champion_element = player_element.find_element(By.XPATH, '../../td[@class="champion-image"]/a')
                champion_href = champion_element.get_attribute('href')
                champion_name = champion_href.split('/')[-2]

                # 🛠 Fix champion name if needed
                if champion_name in CHAMPION_NAME_FIXES:
                    print(f"🛠 Fixing champion name: {champion_name} -> {CHAMPION_NAME_FIXES[champion_name]}")
                    champion_name = CHAMPION_NAME_FIXES[champion_name]

                champions_in_game.add(champion_name)
            except Exception as e:
                print(f"❌ Error retrieving champion for {player_nickname}: {e}")
                champion_name = "Unknown"

            # ✅ FIXED: **Ensure Rank is correctly scraped**
            try:
                rank_element = player_element.find_element(By.XPATH, '../../td[@class="current-rank"]')
                rank = rank_element.text.strip()
                print(f"🏅 Rank for {player_nickname}: {rank}")
            except Exception as e:
                print(f"❌ Error retrieving rank for {player_nickname}: {e}")
                rank = "Unranked"

            try:
                general_winrate_element = player_element.find_element(By.XPATH, '../../td[@class="winratio"]/strong')
                general_winrate = general_winrate_element.text.strip()
            except Exception as e:
                print(f"❌ Error retrieving general winrate for {player_nickname}: {e}")
                general_winrate = "N/A"

            try:
                champ_winrate_element = player_element.find_element(By.XPATH, '../../td[@class="champion-info"]/div[@class="winratio"]')
                champ_winrate = champ_winrate_element.text.strip()
            except Exception as e:
                print(f"❌ Error retrieving champion winrate for {player_nickname}: {e}")
                champ_winrate = "N/A"

            try:
                kda_element = player_element.find_element(By.XPATH, '../../td[@class="champion-info"]/div[contains(@class, "e1nt9gaq2")]')
                kda = kda_element.text.strip().replace(" KDA", "").strip()
                kda = float(kda) if kda.replace(".", "").isdigit() else "N/A"
            except Exception as e:
                print(f"❌ Error retrieving KDA for {player_nickname}: {e}")
                kda = "N/A"

            player_data = {
                "nickname": player_nickname,
                "champion": champion_name,
                "rank": rank,  # ✅ FIXED: Rank is now correctly stored
                "general_winrate": general_winrate,
                "champion_winrate": champ_winrate,
                "kda": kda
            }

            # Remove "N/A" values before storing
            player_data = {k: v for k, v in player_data.items() if v != "N/A"}

            players_data.append(player_data)

        return players_data, champions_in_game

    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        return [], set()

    finally:
        driver.quit()


def extract_numeric_value(element):
    """Extracts and cleans numeric values from the second div inside a td."""
    try:
        divs = element.find_elements(By.TAG_NAME, "div")
        if len(divs) > 1:
            value_text = divs[-1].text.strip()
            value_text = value_text.replace(",", ".").replace("/m", "")
            return float(value_text)
        return None
    except Exception:
        return None

def scrape_champion_stats(server, full_nickname, champion):
    """Scrapes champion performance stats or averages top 3 played champions."""
    formatted_nickname = urllib.parse.quote(full_nickname.replace("#", "-"))
    url = f"https://www.op.gg/summoners/{server}/{formatted_nickname}/champions"

    driver = setup_selenium_driver()
    wait = WebDriverWait(driver, 30)

    try:
        print(f"🔄 Accessing champion stats page for {full_nickname} on {server} (URL: {url})...")
        driver.get(url)
        time.sleep(5)

        wait.until(EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/champions/")]')))

        normalized_champion = champion.lower().replace(" ", "").replace("'", "").replace("-", "")

        champ_elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/champions/") and contains(@href, "/build")]')
        available_champions = {
            el.text.strip().lower().replace(" ", "").replace("'", "").replace("-", ""): el
            for el in champ_elements if el.text.strip() != ""
        }

        if normalized_champion in available_champions:
            champ_element = available_champions[normalized_champion]
            champ_row = champ_element.find_element(By.XPATH, "./ancestor::tr")

            damage_per_minute = extract_numeric_value(
                champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]')[4]
            )
            gold_per_minute = extract_numeric_value(
                champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]')[6]
            )

            return {
                "gold_per_minute": gold_per_minute if gold_per_minute is not None else "N/A",
                "damage_per_minute": damage_per_minute if damage_per_minute is not None else "N/A"
            }

        print(f"❌ Champion {normalized_champion} not found, retrieving top 3 played champions...")
        champ_elements_sorted = champ_elements[:3]
        gold_values = []
        damage_values = []

        for champ in champ_elements_sorted:
            champ_row = champ.find_element(By.XPATH, "./ancestor::tr")
            dmg_value = extract_numeric_value(
                champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]')[4]
            )
            gold_value = extract_numeric_value(
                champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]')[6]
            )

            if dmg_value is not None:
                damage_values.append(dmg_value)
            if gold_value is not None:
                gold_values.append(gold_value)

        return {
            "gold_per_minute": round(np.mean(gold_values), 2) if gold_values else "N/A",
            "damage_per_minute": round(np.mean(damage_values), 2) if damage_values else "N/A"
        }

    except Exception as e:
        print(f"❌ Error retrieving champion stats: {e}")
        return {"gold_per_minute": "N/A", "damage_per_minute": "N/A"}

    finally:
        driver.quit()



def get_combined_player_data(server, nickname):
    """Combines player data with champion statistics."""
    players_data, champions_in_game = scrape_players_and_champions(server, nickname)

    if not players_data or not champions_in_game:
        print("❌ No player or champion data found.")
        return []

    print(f"✅ Scraping champion-specific stats for players...")

    for player in players_data:
        champion = player["champion"]
        print(f"🔍 Fetching stats for {player['nickname']} playing {champion}")

        champ_stats = scrape_champion_stats(server, player["nickname"], champion)

        player.update(champ_stats)

    print("✅ Final player data:", players_data)
    return players_data


if __name__ == "__main__":
    print("This script is designed to be imported into Flask, not run directly.")