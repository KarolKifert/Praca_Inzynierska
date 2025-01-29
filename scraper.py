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
        print("Player table loaded successfully.")

        player_elements = driver.find_elements(By.XPATH, '//td[@class="summoner-name"]/a')

        players_data = []
        champions_in_game = set()

        for player_element in player_elements[:10]:
            player_nickname = player_element.text.strip()
            print(f"Processing player: {player_nickname}")

            try:
                champion_element = player_element.find_element(By.XPATH, '../../td[@class="champion-image"]/a')
                champion_href = champion_element.get_attribute('href')
                champion_name = champion_href.split('/')[-2].lower()
                champions_in_game.add(champion_name)
            except Exception as e:
                print(f"Error retrieving champion for {player_nickname}: {e}")
                champion_name = "Unknown"

            try:
                rank_element = player_element.find_element(By.XPATH, '../../td[@class="current-rank"]')
                rank = rank_element.text.strip()
            except Exception as e:
                print(f"Error retrieving rank for {player_nickname}: {e}")
                rank = "Unranked"

            try:
                general_winrate_element = player_element.find_element(By.XPATH, '../../td[@class="winratio"]/strong')
                general_winrate = general_winrate_element.text.strip() + "%"
            except Exception as e:
                print(f"Error retrieving general winrate for {player_nickname}: {e}")
                general_winrate = "No matches played"

            players_data.append({
                "nickname": player_nickname,
                "champion": champion_name,
                "rank": rank,
                "general_winrate": general_winrate
            })

        return players_data, champions_in_game

    except Exception as e:
        print(f"Error during scraping: {e}")
        return [], set()

    finally:
        driver.quit()


def scrape_champion_stats(server, nickname, champion):
    """Scrapes the /champions page to get the player's stats for the chosen champion."""
    url = f"https://www.op.gg/summoners/{server}/{nickname}/champions"
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
        print(f"Accessing champion stats page for {nickname} on {server}...")
        driver.get(url)

        wait.until(EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/champions/")]')))
        print("Champion statistics page loaded successfully.")

        # **DEBUG: Print all champion names found**
        champion_links = driver.find_elements(By.XPATH, '//a[contains(@href, "/champions/") and contains(@href, "/build")]')
        available_champions = [link.get_attribute("href").split("/")[-2] for link in champion_links]

        print(f"🔍 Available champions on page for {nickname}: {available_champions}")
        print(f"🔍 Looking for champion: {champion}")

        # **Find the section for the selected champion**
        try:
            champ_row = driver.find_element(By.XPATH, f'//a[contains(@href, "/champions/{champion}/build")]/parent::td/parent::tr')
            print(f"✅ Found champion row for {champion}")
        except Exception as e:
            print(f"❌ Champion {champion} not found in player's stats: {e}")
            return {"champion_winrate": "N/A", "kda": "N/A", "gold_per_minute": "N/A", "damage_per_minute": "N/A"}

        # **Extract Champion Winrate**
        try:
            champ_winrate_element = champ_row.find_element(By.XPATH, './/div[contains(@class, "winratio-graph")]/span')
            champion_winrate = champ_winrate_element.text.strip() + "%"
        except Exception as e:
            print(f"Error retrieving champion winrate for {champion}: {e}")
            champion_winrate = "N/A"

        # **Extract KDA**
        try:
            kda_element = champ_row.find_element(By.XPATH, './/strong[contains(@class, "e1uh0vzh1")]')
            kda = kda_element.text.strip()
        except Exception as e:
            print(f"Error retrieving KDA for {champion}: {e}")
            kda = "N/A"

        # **Extract Gold Per Minute**
        try:
            gold_element = champ_row.find_elements(By.XPATH, './/td[contains(@class, "eyczova1")]/div')[3]
            gold_per_minute = gold_element.text.strip()
        except Exception as e:
            print(f"Error retrieving Gold/min for {champion}: {e}")
            gold_per_minute = "N/A"

        # **Extract Damage Per Minute**
        try:
            dmg_element = champ_row.find_elements(By.XPATH, './/td[contains(@class, "eyczova1")]/div')[4]
            damage_per_minute = dmg_element.text.strip()
        except Exception as e:
            print(f"Error retrieving Damage/min for {champion}: {e}")
            damage_per_minute = "N/A"

        return {
            "champion_winrate": champion_winrate,
            "kda": kda,
            "gold_per_minute": gold_per_minute,
            "damage_per_minute": damage_per_minute
        }

    except Exception as e:
        print(f"Error retrieving champion stats: {e}")
        return {"champion_winrate": "N/A", "kda": "N/A", "gold_per_minute": "N/A", "damage_per_minute": "N/A"}

    finally:
        driver.quit()


def get_combined_player_data(server, nickname):
    """Combines data from both live match and champion stats pages."""
    players_data, champions_in_game = scrape_players_and_champions(server, nickname)

    if not players_data or not champions_in_game:
        print("No player or champion data found.")
        return []

    print(f"Scraping champion-specific stats for players...")

    for player in players_data:
        champion = player["champion"]
        champ_stats = scrape_champion_stats(server, player["nickname"], champion)

        player.update(champ_stats)

    print("Final player data:", players_data)  # Debugging
    return players_data


if __name__ == "__main__":
    print("This script is designed to be imported into Flask, not run directly.")
