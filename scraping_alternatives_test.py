import time
import asyncio
import requests

# --- Method 1: requests-html ---
# A good middle-ground. It uses requests for speed but can render JavaScript
# when needed. It's often simpler than a full browser automation tool.
# It uses Pyppeteer (a port of Puppeteer) in the background.
# from requests_html import AsyncHTMLSession

# async def test_requests_html(url, site_name):
#     """
#     Demonstrates scraping a JS-heavy page with requests-html.
#     """
#     print(f"--- Testing requests-html on {site_name} ---")
#     asession = AsyncHTMLSession()
#     try:
#         start_time = time.time()
#         # Use a common user-agent to avoid immediate blocks
#         r = await asession.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
#         # Sportsbooks are complex, give them time to render
#         await r.html.arender(sleep=5, keep_page=True, timeout=60)
#         end_time = time.time()
        
#         print(f"URL: {url}")
#         print(f"Page title: {r.html.title}")
#         print(f"HTML content length: {len(r.html.raw_html)}")
#         print(f"requests-html took: {end_time - start_time:.2f} seconds")

#         if "draftkings" in url and "access denied" in r.html.title.lower():
#              print("⚠️ DraftKings may have blocked the request. This is common with automated tools.")
#         else:
#              print("✅ Page seems to have loaded some content.")
        
#     except Exception as e:
#         print(f"❌ An error occurred with requests-html: {e}")
#         print("Please note: requests-html might require a one-time setup.")
#         print("You might need to run: python -m pyppeteer.install")
#     finally:
#         await asession.close()


# --- Method 2: Playwright with optimizations ---
# A modern, powerful browser automation tool. Can be lighter than Selenium
# if optimized. Here we block loading unnecessary resources like images/css.
# This can significantly reduce CPU/RAM usage.
from playwright.async_api import async_playwright

async def test_playwright(url, site_name):
    """
    Demonstrates scraping with Playwright, with MAXIMUM optimizations to reduce
    CPU and memory usage for resource-constrained devices like Raspberry Pi.
    """
    print(f"\n--- Testing Playwright (Ultra-Lightweight) on {site_name} ---")
    async with async_playwright() as p:
        
        # Launch browser with memory/CPU optimizations
        browser = await p.webkit.launch(
            headless=True,
            args=[
                # Memory optimizations
                '--memory-pressure-off',           # Disable memory pressure detection
                '--max_old_space_size=512',        # Limit heap size to 512MB
                '--disable-dev-shm-usage',         # Use /tmp instead of /dev/shm
                '--disable-gpu',                   # Disable GPU acceleration
                '--disable-software-rasterizer',   # Disable software rasterizer
                
                # CPU optimizations  
                '--single-process',                # Use single process (less overhead)
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                
                # Network/Security optimizations (less processing)
                '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-default-apps',
                '--disable-sync',
                
                # Rendering optimizations
                '--disable-web-security',          # Skip some security checks
                '--disable-features=VizDisplayCompositor',
                '--run-all-compositor-stages-before-draw',
            ]
        )
        
        # More aggressive resource blocking
        async def ultra_lightweight_blocking(route):
            resource_type = route.request.resource_type
            url = route.request.url
            
            # Block almost everything except the main document and essential scripts
            if resource_type in {
                "image", "stylesheet", "font", "media", "websocket", 
                "manifest", "other", "eventsource", "texttrack"
            }:
                await route.abort()
            elif resource_type == "script":
                # Only allow scripts from the main domain, block analytics/tracking
                if any(blocked in url.lower() for blocked in [
                    'google-analytics', 'googletagmanager', 'facebook', 'twitter',
                    'doubleclick', 'adsystem', 'amazon-adsystem', 'googlesyndication'
                ]):
                    await route.abort()
                else:
                    await route.continue_()
            else:
                await route.continue_()

        try:
            # Create context with minimal features
            context = await browser.new_context(
                viewport={'width': 800, 'height': 600},  # Smaller viewport = less rendering
                java_script_enabled=True,  # We need JS for SPAs, but we'll limit it
                ignore_https_errors=True,
                user_agent='Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # Apply ultra-aggressive resource blocking
            await page.route("**/*", ultra_lightweight_blocking)
            
            # Disable unnecessary features that consume CPU/memory
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
                
                // Disable console logging to reduce overhead
                console.log = console.warn = console.error = () => {};
                
                // Disable some heavy features
                if (window.performance && window.performance.mark) {
                    window.performance.mark = () => {};
                    window.performance.measure = () => {};
                }
                
                // Disable intersection observer if not needed
                if (window.IntersectionObserver) {
                    window.IntersectionObserver = class {
                        constructor() {}
                        observe() {}
                        unobserve() {}
                        disconnect() {}
                    };
                }
            """)

            start_time = time.time()
            
            # Use a shorter timeout and don't wait for network idle (faster)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Give minimal time for essential JS to run
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"⚠️ Page load warning: {e}")
                # Continue anyway, we might have partial content
            
            end_time = time.time()

            title = await page.title()
            content = await page.content()
            
            print(f"URL: {url}")
            print(f"Page title: {title}")
            print(f"HTML content length: {len(content)}")

            # Check if we got meaningful content
            if len(content) < 1000:
                print("⚠️ Very small content size - page might not have loaded properly")
            elif "access denied" in title.lower() or "blocked" in content.lower():
                print("⚠️ Site may have blocked the request")
            else:
                print("✅ Page loaded with reasonable content size")

            print(f"Ultra-lightweight Playwright took: {end_time - start_time:.2f} seconds")
            
            # Memory usage info (if available)
            try:
                metrics = await page.evaluate("() => performance.memory")
                if metrics:
                    print(f"JS Heap: {metrics.get('usedJSHeapSize', 0) / 1024 / 1024:.1f}MB used of {metrics.get('totalJSHeapSize', 0) / 1024 / 1024:.1f}MB")
            except:
                pass

        except Exception as e:
            print(f"❌ An error occurred with Ultra-lightweight Playwright: {e}")
        finally:
            await browser.close()

# Add a simple requests test for comparison
async def test_simple_requests(url, site_name):
    """
    Test if a simple requests call works (most lightweight option).
    """
    print(f"\n--- Testing Simple Requests on {site_name} ---")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=10)
        end_time = time.time()
        
        print(f"URL: {url}")
        print(f"Status Code: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        print(f"Content type: {response.headers.get('content-type', 'unknown')}")
        
        if response.status_code == 200:
            if 'application/json' in response.headers.get('content-type', ''):
                print("✅ Got JSON response - this is likely an API endpoint!")
                # Try to parse and show a sample
                try:
                    import json
                    data = response.json()
                    print(f"JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Array with ' + str(len(data)) + ' items'}")
                except:
                    print("JSON parsing failed, but content-type suggests it's JSON")
            else:
                print("✅ Got HTML response")
        else:
            print(f"⚠️ Non-200 status code: {response.status_code}")
            
        print(f"Simple requests took: {end_time - start_time:.2f} seconds")
        
    except Exception as e:
        print(f"❌ Requests failed: {e}")

async def main():
    # Test the DraftKings API endpoint we discovered
    dk_url = "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnc/v1/leagues/84240/categories/743/subcategories/17406"

    print("Testing different approaches for maximum efficiency on Raspberry Pi.\n")

    print("=== Test 1: Simple Requests (Most Lightweight) ===")
    await test_simple_requests(dk_url, "DraftKings API")

    print("\n=== Test 2: Ultra-Lightweight Playwright ===")
    await test_playwright(dk_url, "DraftKings")

    print("\n=== Summary ===")
    print("1. Simple requests: Fastest, lowest resource usage, but only works if no JS is needed")
    print("2. Ultra-lightweight Playwright: Heavier but handles JS, optimized for minimal resource usage")
    print("3. For your Pi: Try requests first, fall back to optimized Playwright only when necessary")


if __name__ == "__main__":
    # In some environments, especially Windows, you might need this for playwright.
    # On Linux/macOS it's often not needed.
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main()) 