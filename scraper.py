import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape_players_and_champions(server, nickname):
    """Scrapes the live match page to get players and their general winrates + chosen champions."""
    url = f"https://www.op.gg/summoners/{server}/{nickname}/ingame"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    )

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)

    try:
        print(f"Accessing live match page for {nickname} on {server}...")
        driver.get(url)

        wait.until(EC.presence_of_all_elements_located((By.XPATH, '//td[@class="summoner-name"]/a')))
        print("✅ Player table loaded successfully.")

        player_elements = driver.find_elements(By.XPATH, '//td[@class="summoner-name"]/a')

        players_data = []
        champions_in_game = set()

        for player_element in player_elements[:10]:
            player_nickname = player_element.text.strip()
            print(f"🎯 Processing player: {player_nickname}")

            try:
                champion_element = player_element.find_element(By.XPATH, '../../td[@class="champion-image"]/a')
                champion_href = champion_element.get_attribute('href')
                champion_name = champion_href.split('/')[-2].lower()
                champions_in_game.add(champion_name)
            except Exception as e:
                print(f"❌ Error retrieving champion for {player_nickname}: {e}")
                champion_name = "Unknown"

            try:
                rank_element = player_element.find_element(By.XPATH, '../../td[@class="current-rank"]')
                rank = rank_element.text.strip()
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
                # Extract Champion-Specific Winrate (in-game winrate)
                champ_winrate_element = player_element.find_element(By.XPATH, '../../td[@class="champion-info"]/div[@class="winratio"]')
                champ_winrate = champ_winrate_element.text.strip()
            except Exception as e:
                print(f"❌ Error retrieving champion winrate for {player_nickname}: {e}")
                champ_winrate = "N/A"

            try:
                # Extract KDA (inside specific div class)
                kda_element = player_element.find_element(By.XPATH, '../../td[@class="champion-info"]/div[contains(@class, "e1nt9gaq2")]')
                kda = kda_element.text.strip()

                # Remove unnecessary text like "KDA"
                kda = kda.replace(" KDA", "").strip()

                # Convert to float if valid, otherwise set to "N/A"
                kda = float(kda) if kda.replace(".", "").isdigit() else "N/A"
            except Exception as e:
                print(f"❌ Error retrieving KDA for {player_nickname}: {e}")
                kda = "N/A"

            # Clean up player data and ensure "N/A" values are properly handled
            player_data = {
                "nickname": player_nickname,
                "champion": champion_name,
                "rank": rank,
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


def scrape_champion_stats(server, full_nickname, champion):
    """Scrapes the /champions page to get the player's Gold Per Minute and Damage Per Minute for the chosen champion."""

    import urllib.parse
    formatted_nickname = urllib.parse.quote(full_nickname.replace("#", "-"))
    url = f"https://www.op.gg/summoners/{server}/{formatted_nickname}/champions"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    )

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)

    try:
        print(f"Accessing champion stats page for {full_nickname} on {server} (URL: {url})...")
        driver.get(url)
        time.sleep(5)

        wait.until(EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/champions/")]')))
        print("Champion statistics page loaded successfully.")

        # **Normalize champion name for lookup**
        normalized_champion = (
            champion.lower()
            .replace(" ", "")  # Remove spaces
            .replace("'", "")  # Remove apostrophes
            .replace("-", "")  # Remove hyphens
        )

        # **Find all champions in the table**
        champ_elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/champions/") and contains(@href, "/build")]')
        available_champions = {
            el.text.strip().lower().replace(" ", "").replace("'", "").replace("-", ""): el
            for el in champ_elements if el.text.strip() != ""
        }

        print(f"🔍 Available champions on page: {list(available_champions.keys())}")
        print(f"🔍 Looking for champion: {normalized_champion}")

        if normalized_champion not in available_champions:
            print(f"❌ Champion {normalized_champion} not found in player's stats.")
            return {"gold_per_minute": "N/A", "damage_per_minute": "N/A"}

        # **Locate the champion row using direct text match**
        try:
            champ_element = available_champions[normalized_champion]
            champ_row = champ_element.find_element(By.XPATH, "./ancestor::tr")
            print(f"✅ Found champion row for {champion}")
        except Exception as e:
            print(f"❌ Error finding champion row for {champion}: {e}")
            return {"gold_per_minute": "N/A", "damage_per_minute": "N/A"}

        # **Extract Gold Per Minute**
        try:
            gold_element = champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]/div')[1]
            gold_per_minute = gold_element.text.strip().split("/m")[0]  # Remove "/m"
        except Exception as e:
            print(f"❌ Error retrieving Gold/min for {champion}: {e}")
            gold_per_minute = "N/A"

        # **Extract Damage Per Minute**
        try:
            dmg_element = champ_row.find_elements(By.XPATH, './/td[contains(@class, "value")]/div')[0]
            damage_per_minute = dmg_element.text.strip().split("/m")[0]  # Remove "/m"
        except Exception as e:
            print(f"❌ Error retrieving Damage/min for {champion}: {e}")
            damage_per_minute = "N/A"

        print(f"✅ Scraped stats for {champion}: GPM={gold_per_minute}, DPM={damage_per_minute}")

        return {
            "gold_per_minute": gold_per_minute,
            "damage_per_minute": damage_per_minute
        }

    except Exception as e:
        print(f"❌ Error retrieving champion stats: {e}")
        return {"gold_per_minute": "N/A", "damage_per_minute": "N/A"}

    finally:
        driver.quit()




def get_combined_player_data(server, nickname):
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
