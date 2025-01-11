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
                # Extract the champion name
                champion_name_element = row.find_element(By.CSS_SELECTOR, 'td.css-1ufme2f strong')
                champion_name = champion_name_element.text.strip().lower()  # Normalize name to lowercase

                # If the champion is not in our list, skip it
                if champion_name not in champions_to_scrape:
                    continue

                # Extract the winrate
                winrate_element = row.find_element(By.CSS_SELECTOR, 'div.css-1xqka05')
                winrate = winrate_element.text.strip()

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

            players_data.append({
                "nickname": nickname,
                "champion": champion_name,
                "winrate": winrate
            })

        return players_data

    except Exception as e:
        print(f"Error during scraping: {e}")
        return []

    finally:
        driver.quit()


def get_combined_player_data(server, nickname):
    # Step 1: Scrape players and their champions
    players_data = scrape_players_and_champions(server, nickname)

    # Step 2: Extract unique champion names (normalized to lowercase) from players_data
    champions_to_scrape = {player["champion"].lower() for player in players_data}

    # Step 3: Scrape winrates for the extracted champions
    champion_winrates = scrape_champion_winrates(champions_to_scrape)

    # Step 4: Combine data
    for player in players_data:
        champion = player["champion"].lower()
        player["champion_winrate"] = champion_winrates.get(champion, "No data")

    return players_data



# Example usage
server = "eune"
nickname = "tyrant-1vall"
combined_data = get_combined_player_data(server, nickname)

if combined_data:
    print("\nCombined Data:")
    for player in combined_data:
        print(f"Nickname: {player['nickname']}, Champion: {player['champion']}, "
              f"Winrate: {player['winrate']}, Champion Winrate: {player['champion_winrate']}")
else:
    print("No data combined.")
