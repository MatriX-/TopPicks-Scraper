import os
import json
import time
import re
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# Regex to match "Pick <Name> for Less than"
player_regex = re.compile(r"^Pick\s+(.*?)\s+for\s+Less than", re.IGNORECASE)

# WNBA-specific stat URLs and their labels
urls = {
    "points": ("Points", "https://pick6.draftkings.com/?sport=WNBA&stat=PTS"),
    "threes": ("3-Pointers Made", "https://pick6.draftkings.com/?sport=WNBA&stat=3PM"),
    "rebounds": ("Rebounds", "https://pick6.draftkings.com/?sport=WNBA&stat=REB"),
    "pra": ("Points + Rebounds + Assists", "https://pick6.draftkings.com/?sport=WNBA&stat=P%2BR%2BA"),
    "assists": ("Assists", "https://pick6.draftkings.com/?sport=WNBA&stat=AST"),
    "pa": ("Points + Assists", "https://pick6.draftkings.com/?sport=WNBA&stat=PTS%2BAST"),
    "pr": ("Points + Rebounds", "https://pick6.draftkings.com/?sport=WNBA&stat=PTS%2BREB")
}

def normalize_to_initial_format(full_name):
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {' '.join(parts[1:])}"
    return full_name

def clear_stats_files():
    os.makedirs("wnba/options", exist_ok=True)
    os.makedirs("wnba/data_p6", exist_ok=True)  # WNBA-specific data folder
    with open("locked.json", "w", encoding="utf-8") as f:
        json.dump([], f)
    for stat_name in urls:
        with open(f"wnba/options/{stat_name}_options.json", "w", encoding="utf-8") as f:
            json.dump([], f)

async def scrape_with_ultra_lightweight_playwright(stat_name, stat_label, url):
    """
    Ultra-lightweight Playwright scraper optimized for Raspberry Pi - WNBA version.
    Uses all the performance optimizations we discovered.
    """
    async with async_playwright() as p:
        # Launch browser with maximum optimizations for Pi
        browser = await p.webkit.launch(
            headless=True,
            args=[
                # Memory optimizations
                '--memory-pressure-off',
                '--max_old_space_size=256',  # Even smaller heap for Pi
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-software-rasterizer',
                
                # CPU optimizations  
                '--single-process',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                
                # Network/Security optimizations
                '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
            ]
        )
        
        # Ultra-aggressive resource blocking
        async def block_unnecessary_resources(route):
            resource_type = route.request.resource_type
            url_path = route.request.url
            
            # Block almost everything except essential content
            if resource_type in {
                "image", "stylesheet", "font", "media", "websocket", 
                "manifest", "other", "eventsource", "texttrack"
            }:
                await route.abort()
            elif resource_type == "script":
                # Block analytics and tracking scripts
                if any(blocked in url_path.lower() for blocked in [
                    'google-analytics', 'googletagmanager', 'facebook', 'twitter',
                    'doubleclick', 'adsystem', 'amazon-adsystem', 'googlesyndication',
                    'hotjar', 'mixpanel', 'segment', 'amplitude'
                ]):
                    await route.abort()
                else:
                    await route.continue_()
            else:
                await route.continue_()

        try:
            # Create minimal context
            context = await browser.new_context(
                viewport={'width': 800, 'height': 600},
                java_script_enabled=True,
                ignore_https_errors=True,
                user_agent='Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # Apply resource blocking
            await page.route("**/*", block_unnecessary_resources)
            
            # Disable heavy features
            await page.add_init_script("""
                // Disable animations and transitions
                const style = document.createElement('style');
                style.textContent = `
                    *, *::before, *::after {
                        animation-duration: 0s !important;
                        animation-delay: 0s !important;
                        transition-duration: 0s !important;
                        transition-delay: 0s !important;
                    }
                `;
                document.head.appendChild(style);
                
                // Disable console logging
                console.log = console.warn = console.error = () => {};
                
                // Disable performance monitoring
                if (window.performance && window.performance.mark) {
                    window.performance.mark = () => {};
                    window.performance.measure = () => {};
                }
            """)

            start_time = time.time()
            
            # Navigate to page
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Check if stat type is available
            try:
                await page.wait_for_selector(f'text="{stat_label}"', timeout=5000)
            except:
                print(f"⚠️ {stat_label} not found on page. Skipping.")
                return
            
            # Wait for player cards to load
            try:
                await page.wait_for_selector('[data-testid="playerStatCard"]', timeout=15000)
                # Give a moment for dynamic content
                await page.wait_for_timeout(3000)
            except:
                print(f"⚠️ {stat_label}: Player cards didn't load in time")
                return

            # Get page content
            html = await page.content()
            end_time = time.time()
            
            print(f"🏀 {stat_label}: Page loaded in {end_time - start_time:.2f}s")
            
            # Save HTML for debugging (WNBA-specific path)
            with open(f"wnba/data_p6/{stat_name}_p6.json", "w", encoding="utf-8") as f:
                json.dump({"html": html}, f)

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Get locked players
            locked_players_set = set()
            for card in soup.select('[data-testid="playerStatCard"]'):
                name_tag = card.select_one('[data-testid="player-name"]')
                if not name_tag:
                    continue
                name = name_tag.get_text(strip=True)
                if card.find("use", {"href": "#lock-icon"}):
                    locked_players_set.add(name)

            # Get "Less than" players using page.evaluate for more reliable extraction
            valid_players_set = set()
            try:
                buttons_data = await page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button[aria-label*="for Less than"]'));
                        return buttons.map(btn => btn.getAttribute('aria-label')).filter(label => label);
                    }
                """)
                
                for aria_label in buttons_data:
                    match = player_regex.search(aria_label)
                    if match:
                        name = match.group(1).strip()
                        if name != "Contest Fill":
                            valid_players_set.add(name)
            except Exception as e:
                print(f"⚠️ {stat_label}: Error extracting player buttons - {e}")

            # Exclude locked players
            unlocked_valid_players = sorted([
                name for name in valid_players_set
                if normalize_to_initial_format(name) not in locked_players_set
            ])

            # Save results (WNBA-specific path)
            with open(f"wnba/options/{stat_name}_options.json", "w", encoding="utf-8") as f:
                json.dump(unlocked_valid_players, f, indent=4)

            # Update locked.json globally
            locked_file = "locked.json"
            if os.path.exists(locked_file):
                with open(locked_file, "r", encoding="utf-8") as f:
                    existing_locked = set(json.load(f))
            else:
                existing_locked = set()

            all_locked = sorted(existing_locked.union(locked_players_set))
            with open(locked_file, "w", encoding="utf-8") as f:
                json.dump(all_locked, f, indent=4)

            print(f"✅ {stat_label}: {len(unlocked_valid_players)} options, {len(locked_players_set)} locked")

        except Exception as e:
            print(f"❌ Error scraping {stat_label}: {e}")
        finally:
            await browser.close()

def scrape_and_save(stat_name, stat_label, url):
    """
    Wrapper function to run the async scraper.
    """
    try:
        asyncio.run(scrape_with_ultra_lightweight_playwright(stat_name, stat_label, url))
    except Exception as e:
        print(f"❌ Fatal error for {stat_label}: {e}")

def run_scraping():
    """
    Main function to orchestrate the WNBA PrizePicks scraping with ultra-lightweight approach.
    """
    print("🏀 Starting ultra-lightweight WNBA PrizePicks scraper...")
    print("🎯 Optimized for Raspberry Pi with minimal resource usage")
    
    clear_stats_files()
    
    start_time = time.time()
    
    # Use fewer workers to reduce memory pressure on Pi
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(scrape_and_save, stat, label, url) 
            for stat, (label, url) in urls.items()
        ]
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"Thread error: {e}")
    
    end_time = time.time()
    print(f"\n🎉 WNBA PrizePicks scraping completed in {end_time - start_time:.2f} seconds")
    print("📁 Results saved to 'wnba/options/' and 'wnba/data_p6/' folders")

if __name__ == "__main__":
    run_scraping()
