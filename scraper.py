import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape_champion_winrates(champions_to_scrape):
    url = "https://www.op.gg/statistics/champions"
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
        print("Accessing champion statistics page...")
        driver.get(url)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.css-1o9zu66 tbody')))
        print("Champion statistics table loaded successfully.")

        rows = driver.find_elements(By.CSS_SELECTOR, 'table.css-1o9zu66 tbody tr')

        champion_winrates = {}
        for row in rows:
            try:
                champion_name_element = row.find_element(By.CSS_SELECTOR, 'td.css-1ufme2f strong')
                champion_name = champion_name_element.text.strip().lower()

                if champion_name not in champions_to_scrape:
                    continue

                # **Handle dynamic class names for win rate**
                try:
                    winrate_element = row.find_element(By.XPATH, ".//div[contains(@class, 'qzg52u') or contains(@class, '1xqka05')]")
                    winrate = winrate_element.text.strip()
                except Exception:
                    winrate = "Unknown"

                champion_winrates[champion_name] = winrate
                print(f"Scraped winrate for {champion_name}: {winrate}")

                if len(champion_winrates) == len(champions_to_scrape):
                    break

            except Exception as e:
                print(f"Error processing champion {champion_name}: {e}")

        print("Champion winrates scraped successfully.")
        return champion_winrates

    except Exception as e:
        print(f"Error retrieving champion winrates: {e}")
        return {}

    finally:
        driver.quit()





def scrape_players_and_champions(server, nickname):
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
            nickname = player_element.text.strip()
            print(f"Processing player: {nickname}")

            try:
                champion_element = player_element.find_element(By.XPATH, '../../td[@class="champion-image"]/a')
                champion_href = champion_element.get_attribute('href')
                champion_name = champion_href.split('/')[-2].lower()
                champions_in_game.add(champion_name)
            except Exception as e:
                print(f"Error retrieving champion for {nickname}: {e}")
                champion_name = "Unknown"

            try:
                winrate_element = player_element.find_element(By.XPATH, '../../td[@class="winratio"]/strong')
                winrate = winrate_element.text.strip() + "%"
            except Exception as e:
                print(f"Error retrieving winrate for {nickname}: {e}")
                winrate = "No matches played"

            try:
                rank_element = player_element.find_element(By.XPATH, '../../td[@class="current-rank"]')
                rank = rank_element.text.strip()
            except Exception as e:
                print(f"Error retrieving rank for {nickname}: {e}")
                rank = "Unranked"

            players_data.append({
                "nickname": nickname,
                "champion": champion_name,
                "winrate": winrate,
                "rank": rank
            })

        return players_data, champions_in_game

    except Exception as e:
        print(f"Error during scraping: {e}")
        return [], set()

    finally:
        driver.quit()


def get_combined_player_data(server, nickname):
    players_data, champions_in_game = scrape_players_and_champions(server, nickname)

    if not players_data or not champions_in_game:
        print("No player or champion data found.")
        return []

    print(f"Scraping win rates for champions in the game: {champions_in_game}")
    champion_winrates = scrape_champion_winrates(champions_in_game)

    for player in players_data:
        champion = player["champion"]

        # **Normalize the champion name before lookup**
        normalized_champion = champion.lower().replace("'", "").replace(" ", "")

        player["champion_winrate"] = champion_winrates.get(champion, "No data")

    print("Final player data with winrates:", players_data)  # Debugging
    return players_data


# ✅ Remove manual input - The web interface will handle inputs
if __name__ == "__main__":
    print("This script is designed to be imported into Flask, not run directly.")
