import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Database import init_db
from Database import save_data_to_db

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
                champion_name = champion_name_element.text.strip().lower()  # Normalize name to lowercase

                if champion_name not in champions_to_scrape:
                    continue

                winrate_parent_div = row.find_element(By.CSS_SELECTOR, 'div.css-ed0c12')
                winrate_child_div = winrate_parent_div.find_element(By.CSS_SELECTOR, 'div[font-weight="bold"]')
                winrate = winrate_child_div.text.strip()

                print(f"Scraped winrate for {champion_name}: {winrate}")  # Debugging
                champion_winrates[champion_name] = winrate
            except Exception as e:
                print(f"Error processing a row: {e}")

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
        print("Accessing live match page...")
        driver.get(url)

        wait.until(EC.presence_of_all_elements_located((By.XPATH, '//td[@class="summoner-name"]/a')))
        print("Player table loaded successfully.")

        player_elements = driver.find_elements(By.XPATH, '//td[@class="summoner-name"]/a')

        players_data = []
        for player_element in player_elements[:10]:
            nickname = player_element.text.strip()
            print(f"Processing player: {nickname}")

            try:
                champion_element = player_element.find_element(By.XPATH, '../../td[@class="champion-image"]/a')
                champion_href = champion_element.get_attribute('href')
                champion_name = champion_href.split('/')[-2]
            except Exception as e:
                print(f"Error retrieving champion for {nickname}: {e}")
                champion_name = "Unknown"

            try:
                winrate_element = player_element.find_element(By.XPATH, '../../td[@class="winratio"]/strong')
                winrate = winrate_element.text.strip()
            except Exception as e:
                print(f"Error retrieving winrate for {nickname}: {e}")
                winrate = "No matches played"

            try:
                rank_element = player_element.find_element(By.XPATH, '../../td[@class="current-rank"]/div')
                rank = rank_element.text.strip()
            except Exception as e:
                print(f"Error retrieving rank for {nickname}: {e}")
                rank = "No matches played"

            players_data.append({
                "nickname": nickname,
                "champion": champion_name,
                "winrate": winrate,
                "rank": rank
            })

        return players_data

    except Exception as e:
        print(f"Error during scraping: {e}")
        return []

    finally:
        driver.quit()


def get_combined_player_data(server, nickname):
    players_data = scrape_players_and_champions(server, nickname)

    champions_to_scrape = {player["champion"].lower() for player in players_data}

    champion_winrates = scrape_champion_winrates(champions_to_scrape)

    for player in players_data:
        champion = player["champion"].lower()
        player["champion_winrate"] = champion_winrates.get(champion, "No data")

    return players_data

server = "eune"
nickname = "bot nie sfeeduj-eune"
combined_data = get_combined_player_data(server, nickname)

init_db()

if combined_data:
    print("\nCombined Data:")
    for player in combined_data:
        print(f"Nickname: {player['nickname']}, Champion: {player['champion']}, "
              f"Winrate: {player['winrate']}, Champion Winrate: {player['champion_winrate']}, Rank: {player['rank']}")

        save_data_to_db(combined_data)

else:
    print("No data combined.")
