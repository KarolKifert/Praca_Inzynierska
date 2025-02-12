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
        wait.until(EC.presence_of_all_elements_located(
            (By.XPATH, '//ul[@class="cards-list no-margin-top no-margin-bottom"]/li')))

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

            players_data.append({
                "nickname": player_nickname,
                "champion": champion_name,
                "rank": rank  # ✅ Adding rank to player data
            })

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
            value_text = value_text.replace(" ", "").replace(",", ".").replace("/m", "").replace("%", "")  # ✅ Clean formatting
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

        if champ_winrate == "N/A" or champ_kda == "N/A":
            print(f"❌ Champion {champion} not found, retrieving top 3 played champions...")

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

            champ_winrate = f"{round(np.mean(winrates), 2)}%" if winrates else "N/A"
            champ_kda = round(np.mean(kdas), 2) if kdas else "N/A"

        return {
            "gold_per_minute": gold if gold is not None else "N/A",
            "damage_per_minute": damage_per_minute if damage_per_minute is not None else "N/A",
            "champion_winrate": champ_winrate,
            "kda": champ_kda
        }

    except Exception as e:
        print(f"❌ Error retrieving champion stats: {e}")
        return {"gold_per_minute": "N/A", "damage_per_minute": "N/A", "champion_winrate": "N/A", "kda": "N/A"}

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
