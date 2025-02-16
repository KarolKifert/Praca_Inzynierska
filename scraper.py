import time
import urllib
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

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
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)


def scrape_latest_matches():
    """Scrapes the first live match from Porofessor."""
    url = "https://porofessor.gg/pl/"
    driver = setup_selenium_driver()
    wait = WebDriverWait(driver, 30)

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.XPATH, '//ul[@class="cards-list no-margin-top no-margin-bottom"]/li')))

        match_element = driver.find_element(By.XPATH, '//ul[@class="cards-list no-margin-top no-margin-bottom"]/li[1]')
        link_element = match_element.find_element(By.XPATH, './/a[contains(@class, "liveGameLink")]')
        match_href = link_element.get_attribute("href")

        match_parts = match_href.split("/")[-2:]
        server = match_parts[0]
        nickname, hashtag = match_parts[1].rsplit("-", 1)

        return [(server, f"{nickname}-{hashtag}")]

    except Exception as e:
        print(f"❌ Error scraping match: {e}")
        return []

    finally:
        driver.quit()


def scrape_players_and_champions(server, nickname):
    """Scrapes the live match page for player details."""
    url = f"https://www.op.gg/summoners/{server}/{nickname}/ingame"
    driver = setup_selenium_driver()

    try:
        print(f"🌐 Opening OP.GG live match page: {url}")
        driver.get(url)
        time.sleep(5)

        player_elements = driver.find_elements(By.XPATH, '//td[@class="summoner-name"]/a')

        if not player_elements:
            print(f"❌ ERROR: No player elements found on {url}!")
            return [], set()

        print(f"✅ Found {len(player_elements)} players!")

        players_data = []
        champions_in_game = set()

        for player_element in player_elements[:10]:
            player_nickname = player_element.text.strip()
            print(f"🎯 Processing player: {player_nickname}")

            try:
                # ✅ Scraping Champion
                champion_element = player_element.find_element(By.XPATH, '../../td[@class="champion-image"]/a')
                champion_href = champion_element.get_attribute('href')
                champion_name = champion_href.split('/')[-2]
                champions_in_game.add(champion_name)
                print(f"✅ Champion found: {champion_name}")

            except Exception as e:
                print(f"❌ Error retrieving champion for {player_nickname}: {e}")
                champion_name = "Unknown"

            try:
                # ✅ Scraping Rank
                rank_element = player_element.find_element(By.XPATH, '../../td[@class="current-rank"]')
                rank = rank_element.text.strip()
                print(f"🏅 Rank for {player_nickname}: {rank}")

            except Exception as e:
                print(f"❌ Error retrieving rank for {player_nickname}: {e}")
                rank = "Unranked"

            # Placeholder for KDA and winrate (potentially missing here)
            player_data = {
                "nickname": player_nickname,
                "champion": champion_name,
                "rank": rank,
                "champion_winrate": "N/A",
                "kda": "N/A"
            }

            # If KDA or champion winrate are missing, they'll be fetched later in scrape_champion_stats
            players_data.append(player_data)

        return players_data, champions_in_game

    except Exception as e:
        print(f"❌ Error scraping match: {e}")
        return [], set()

    finally:
        driver.quit()



def extract_numeric_value(element):
    """Extracts the first numeric value from the first div inside td."""
    try:
        divs = element.find_elements(By.TAG_NAME, "div")  # ✅ Get all divs inside td
        if divs:
            value_text = divs[0].text.strip().split("\n")[0]  # ✅ Only take the first value before \n
            value_text = value_text.replace(" ", "").replace(",", ".").replace("/m", "").replace("%", "")
            return float(value_text)  # ✅ Convert to float now that we have a clean value
        return 0.0  # ⬅️ Return 0.0 if no divs found
    except Exception as e:
        print(f"❌ Error extracting numeric value: {e}")
        return 0.0  # ⬅️ Return 0.0 instead of crashing


def scrape_champion_stats(server, full_nickname, champion):
    """Scrapes champion performance stats or fetches from the top 3 played champions if missing."""
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

        champ_winrate, champ_kda = "N/A", "N/A"
        gold, damage_per_minute = "N/A", "N/A"

        if normalized_champion in available_champions:
            champ_element = available_champions[normalized_champion]
            champ_row = champ_element.find_element(By.XPATH, "./ancestor::tr")

            gold = extract_numeric_value(
                champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]')[6]
            )
            damage_per_minute = extract_numeric_value(
                champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]')[3]
            )

            try:
                champ_winrate = champ_row.find_element(By.XPATH, './/div[@class="winratio-graph"]/following-sibling::span').text.strip()
            except:
                champ_winrate = "N/A"

            try:
                champ_kda = champ_row.find_element(By.XPATH, './/strong[contains(@class, "e5ndxls1")]').text.strip()
            except:
                champ_kda = "N/A"

        # Fallback: If any value is still missing, scrape from top 3 most played champions
        if champ_winrate == "N/A" or champ_kda == "N/A" or gold == "N/A" or damage_per_minute == "N/A":
            print(f"⚠️ Missing data for {champion}. Scraping top 3 most played champions instead.")
            champ_elements_sorted = champ_elements[:3]
            winrates, kdas, gold_values, damage_values = [], [], [], []

            for champ in champ_elements_sorted:
                champ_row = champ.find_element(By.XPATH, "./ancestor::tr")

                dmg_value = extract_numeric_value(
                    champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]')[3]
                )
                gold_value = extract_numeric_value(
                    champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]')[6]
                )

                try:
                    wr = champ_row.find_element(By.XPATH, './/div[@class="winratio-graph"]/following-sibling::span').text.strip()
                    if wr != "N/A":
                        winrates.append(float(wr.replace("%", "")))
                except:
                    pass

                try:
                    kda_text = champ_row.find_element(By.XPATH, './/strong[contains(@class, "e5ndxls1")]').text.strip()
                    kda_value = float(kda_text.split(":")[0]) if ":" in kda_text else None
                    if kda_value:
                        kdas.append(kda_value)
                except:
                    pass

                if dmg_value is not None:
                    damage_values.append(dmg_value)
                if gold_value is not None:
                    gold_values.append(gold_value)

            # Compute means only if data exists; otherwise, assign defaults
            champ_winrate = f"{round(np.mean(winrates), 2)}%" if winrates else "50%"
            champ_kda = round(np.mean(kdas), 2) if kdas else 2.5
            gold = round(np.mean(gold_values), 2) if gold_values else 500
            damage_per_minute = round(np.mean(damage_values), 2) if damage_values else 500

        # Ensure KDA formatting is correct (remove trailing ':1' if present)
        if isinstance(champ_kda, str) and ":" in champ_kda:
            champ_kda = float(champ_kda.split(":")[0])

        return {
            "gold_per_minute": gold if gold is not None else 0.0,
            "damage_per_minute": damage_per_minute if damage_per_minute is not None else 0.0,
            "champion_winrate": champ_winrate,
            "kda": champ_kda
        }

    except Exception as e:
        print(f"❌ Error retrieving champion stats: {e}")
        return {"gold_per_minute": 0.0, "damage_per_minute": 0.0, "champion_winrate": 0.0, "kda": 0.0}

    finally:
        driver.quit()


def get_combined_player_data(server, nickname):
    """Scrapes player data one by one instead of all at once."""
    print(f"🔵 Fetching player data for {nickname} on {server}...")

    players_data, champions_in_game = scrape_players_and_champions(server, nickname)

    if not players_data:
        print(f"❌ No player data found for {nickname}!")
        return []

    final_players_data = []
    for player in players_data:
        champion = player["champion"]
        print(f"🔍 Fetching stats for {player['nickname']} playing {champion}...")

        champ_stats = scrape_champion_stats(server, player["nickname"], champion)
        player.update(champ_stats)
        final_players_data.append(player)

    print(f"✅ Player data fetched: {final_players_data}")
    return final_players_data



if __name__ == "__main__":
    print("This script is designed to be imported into Flask, not run directly.")
