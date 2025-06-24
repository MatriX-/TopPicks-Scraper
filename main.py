import subprocess
import threading
import time

def run_script(script_path):
    """Executes a Python script and waits for it to complete."""
    print(f"Running {script_path}...")
    try:
        process = subprocess.Popen(['python', script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            print(f"Successfully finished {script_path}.")
        else:
            print(f"Error running {script_path}:")
            print(stderr.decode())
    except FileNotFoundError:
        print(f"Error: Script not found at {script_path}")
    except Exception as e:
        print(f"An unexpected error occurred with {script_path}: {e}")

def run_parallel(scripts):
    """Runs a list of scripts in parallel using threading."""
    threads = []
    for script in scripts:
        thread = threading.Thread(target=run_script, args=(script,))
        threads.append(thread)
        thread.start()
        # Stagger the start times slightly to avoid rate-limiting issues
        time.sleep(2)

    for thread in threads:
        thread.join()

def main():
    """Main function to orchestrate the scraping process."""
    print("Starting the scraping process...")

    # Define the order of execution
    # WNBA
    wnba_p6 = 'wnba/ScrapeP6.py'
    wnba_dk = 'wnba/ScrapeDK.py'
    wnba_fetch = 'wnba/Fetch.py'
    wnba_picks = 'wnba/Picks.py'
    wnba_selection = 'wnba/Selection.py'
    wnba_locks = 'wnba/Locks.py'

    # MLB
    mlb_p6 = 'mlb/ScrapeP6.py'
    mlb_dk = 'mlb/ScrapeDK.py'
    mlb_fetch = 'mlb/Fetch.py'
    mlb_picks = 'mlb/Picks.py'
    mlb_selection = 'mlb/Selection.py'
    mlb_locks = 'mlb/Locks.py'

    # NHL
    nhl_p6 = 'nhl/ScrapeP6.py'
    nhl_dk = 'nhl/ScrapeDK.py'
    nhl_fetch = 'nhl/Fetch.py'
    nhl_picks = 'nhl/Picks.py'
    nhl_selection = 'nhl/Selection.py'
    nhl_locks = 'nhl/Locks.py'

    # Run PrizePicks and DraftKings scraping in parallel for all sports
    print("\n----- Scraping PrizePicks and DraftKings -----")
    parallel_scrape_scripts = [wnba_p6, wnba_dk, mlb_p6, mlb_dk, nhl_p6, nhl_dk]
    run_parallel(parallel_scrape_scripts)

    # Run Fetch scripts in parallel
    print("\n----- Fetching Player Data -----")
    parallel_fetch_scripts = [wnba_fetch, mlb_fetch, nhl_fetch]
    run_parallel(parallel_fetch_scripts)

    # Run Picks scripts in parallel
    print("\n----- Generating Picks -----")
    parallel_picks_scripts = [wnba_picks, mlb_picks, nhl_picks]
    run_parallel(parallel_picks_scripts)

    # Run Selection scripts in parallel
    print("\n----- Generating Selections -----")
    parallel_selection_scripts = [wnba_selection, mlb_selection, nhl_selection]
    run_parallel(parallel_selection_scripts)

    # Run Locks scripts in parallel
    print("\n----- Generating Locks -----")
    parallel_locks_scripts = [wnba_locks, mlb_locks, nhl_locks]
    run_parallel(parallel_locks_scripts)

    # Generate premade parlays
    print("\n----- Generating Premade Parlays -----")
    run_script('generate_parlays.py')

    print("\nScraping process completed!")

if __name__ == "__main__":
    main() 