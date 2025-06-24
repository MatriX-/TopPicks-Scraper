from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import uuid
import time
from selenium.webdriver.chrome.options import Options
import os

# Define URLs for NHL stat types
urls = {
    "shots_on_goal": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1189/subcategories/12040",
    "points": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1675/subcategories/16213",
    "assists": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1676/subcategories/16215",
    "blocks": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1679/subcategories/16257",
    "saves": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1064/subcategories/16550"
}

# Initialize the WebDriver
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument(f"--user-data-dir=/tmp/chrome-user-data-nhl-{uuid.uuid4()}")
driver = webdriver.Chrome(options=chrome_options)

# Ensure the 'nhl/data' folder exists
if not os.path.exists('nhl/data'):
    os.makedirs('nhl/data')

# Function to fetch JSON from a URL and save it to a file in the 'nhl/data' folder
def fetch_and_save_json(url, filename):
    driver.get(url)
    json_data = driver.find_element(By.TAG_NAME, "pre").text
    parsed_data = json.loads(json_data)
    
    # Save JSON file inside the 'nhl/data' folder
    filepath = os.path.join('nhl/data', filename)
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(parsed_data, file, ensure_ascii=False, indent=4)
    print(f"✅ JSON data saved successfully to 'nhl/data/{filename}'")

# Fetch and save data for all NHL stat types
for key, url in urls.items():
    filename = f"{key}.json"
    fetch_and_save_json(url, filename)

# Close the WebDriver
driver.quit()
