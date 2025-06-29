import os
import json
import requests
import time

# Define URLs for NHL stat types
urls = {
    "shots_on_goal": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1189/subcategories/12040",
    "points": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1675/subcategories/16213",
    "assists": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1676/subcategories/16215",
    "blocks": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1679/subcategories/16257",
    "saves": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/42133/categories/1064/subcategories/16550"
}

# Ultra-lightweight headers that work on Raspberry Pi
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

# Ensure the 'nhl/data' folder exists
os.makedirs('nhl/data', exist_ok=True)

def fetch_and_save_json(url, filename):
    """
    Ultra-lightweight function to fetch JSON from DraftKings NHL API using requests.
    This approach uses ~99% less CPU and memory compared to Selenium!
    """
    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=15)
        end_time = time.time()
        
        if response.status_code == 200:
            # Parse the JSON response
            parsed_data = response.json()
            
            # Save JSON file inside the 'nhl/data' folder
            filepath = os.path.join('nhl/data', filename)
            with open(filepath, "w", encoding="utf-8") as file:
                json.dump(parsed_data, file, ensure_ascii=False, indent=4)
            
            print(f"✅ {filename}: {len(response.text)} bytes in {end_time - start_time:.2f}s")
            return True
        else:
            print(f"❌ {filename}: HTTP {response.status_code} - {response.text[:100]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ {filename}: Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {filename}: Request failed - {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ {filename}: Invalid JSON response - {e}")
        return False
    except Exception as e:
        print(f"❌ {filename}: Unexpected error - {e}")
        return False

def main():
    """
    Main function to fetch all NHL stats from DraftKings using ultra-lightweight requests.
    Perfect for Raspberry Pi - no browser overhead!
    """
    print("🏒 Starting ultra-lightweight DraftKings NHL scraper...")
    print(f"📊 Fetching {len(urls)} NHL stat categories...")
    
    successful = 0
    failed = 0
    total_start_time = time.time()
    
    # Fetch and save data for all NHL stat types
    for key, url in urls.items():
        filename = f"{key}.json"
        if fetch_and_save_json(url, filename):
            successful += 1
        else:
            failed += 1
    
    total_end_time = time.time()
    
    print(f"\n📈 NHL Summary:")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️ Total time: {total_end_time - total_start_time:.2f} seconds")
    print(f"🎯 Average per request: {(total_end_time - total_start_time) / len(urls):.2f} seconds")
    
    if successful > 0:
        print(f"🏒 NHL data saved to 'nhl/data/' folder - ready for processing!")
    
    return successful > 0

if __name__ == "__main__":
    main()
