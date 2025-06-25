import json
import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upload_to_github(file_path, content):
    """
    Uploads a file to the specified GitHub repository.
    
    Args:
        file_path (str): Local path to the file being uploaded
        content (str): Content to upload (as string)
    
    Returns:
        bool: True if upload was successful, False otherwise
    """
    # Get GitHub configuration from environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    github_owner = os.getenv('GITHUB_OWNER')
    github_repo = os.getenv('GITHUB_REPO')
    
    # Determine the remote path on GitHub based on the local file_path
    if file_path == 'generated_parlays.json':
        github_file_path = os.getenv('GITHUB_FILE_PATH')
    elif file_path == 'parlay_builder_data.json':
        github_file_path = os.getenv('GITHUB_PARLAY_BUILDER_FILE_PATH', 'parlay_builder_data.json')
    else:
        print(f"Error: Unknown file_path '{file_path}' for GitHub upload.")
        return False

    if not all([github_token, github_owner, github_repo, github_file_path]):
        print("Error: Missing GitHub configuration in .env file for the given file path.")
        return False
    
    # GitHub API URL
    api_url = f"https://api.github.com/repos/{github_owner}/{github_repo}/contents/{github_file_path}"
    
    # Headers for GitHub API
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    try:
        # First, try to get the current file to get its SHA (required for updates)
        response = requests.get(api_url, headers=headers)
        sha = None
        
        if response.status_code == 200:
            sha = response.json().get('sha')
            print(f"Found existing file '{github_file_path}', will update it")
        elif response.status_code == 404:
            print(f"File '{github_file_path}' doesn't exist, will create a new one")
        else:
            print(f"Error checking file existence for '{github_file_path}': {response.status_code} - {response.text}")
            return False
        
        # Encode content to base64
        content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        # Prepare the data for the API request
        data = {
            'message': f'Update {file_path}',
            'content': content_encoded,
            'branch': 'main'
        }
        
        # Include SHA if updating an existing file
        if sha:
            data['sha'] = sha
        
        # Make the API request
        response = requests.put(api_url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            print(f"✅ Successfully uploaded {file_path} to {github_owner}/{github_repo}/{github_file_path}")
            return True
        else:
            print(f"❌ Failed to upload file '{github_file_path}': {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error uploading '{file_path}' to GitHub: {str(e)}")
        return False

def parse_game_from_leg(leg_string):
    """Parses just the game identifier from a leg string."""
    try:
        # Assumes format: "Player, Prop, Odds, Game, Time"
        parts = leg_string.split(',')
        if len(parts) > 3:
            return parts[3].strip()  # Game is the 4th element
        return None
    except Exception:
        return None

def generate_parlay_builder_data():
    """
    Reads all *_lines.json files for each sport to compile a comprehensive
    list of players and all their available props, including lines and odds.
    Saves the data to parlay_builder_data.json.
    """
    sports = ['mlb', 'nhl', 'wnba']
    parlay_builder_data = {}

    for sport in sports:
        lines_dir = Path(sport) / 'lines'
        sport_player_data = {}

        if not lines_dir.exists():
            parlay_builder_data[sport] = {}
            continue

        for lines_file in lines_dir.glob('*_lines.json'):
            prop_name = lines_file.stem.replace('_lines', '')
            try:
                with open(lines_file, 'r') as f:
                    data = json.load(f)
                    for player_data in data:
                        player_name = player_data.get('name')
                        if not player_name:
                            continue
                        
                        if player_name not in sport_player_data:
                            sport_player_data[player_name] = {}
                        
                        prop_details = player_data.copy()
                        del prop_details['name']
                        
                        sport_player_data[player_name][prop_name] = prop_details

            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Could not process {lines_file}: {e}")
                continue
        
        parlay_builder_data[sport] = sport_player_data

    output_filename = 'parlay_builder_data.json'
    
    # Write the file locally
    with open(output_filename, 'w') as f:
        json.dump(parlay_builder_data, f, indent=4)
    
    print(f"Successfully generated parlay builder data in {output_filename}")
    
    # Upload to GitHub
    try:
        with open(output_filename, 'r') as f:
            file_content = f.read()
        
        print(f"Uploading {output_filename} to GitHub...")
        upload_success = upload_to_github(output_filename, file_content)
        
        if upload_success:
            print(f"🎉 {output_filename} has been successfully uploaded to GitHub!")
        else:
            print(f"⚠️ Local file {output_filename} generated, but GitHub upload failed.")
            
    except Exception as e:
        print(f"⚠️ Error during GitHub upload for {output_filename}: {str(e)}")

def generate_parlays():
    """
    Reads the calculated parlays from picks.json for each sport,
    preserves all detailed odds/edge data, and formats it for the frontend.
    """
    sports = ['mlb', 'nhl', 'wnba']
    all_parlays_data = {}

    for sport in sports:
        picks_file = Path(sport) / 'picks.json'
        sport_parlays = []
        
        try:
            with open(picks_file, 'r') as f:
                data = json.load(f)
                
                if 'parlays' not in data or not data['parlays']:
                    all_parlays_data[sport] = []
                    continue

                for parlay_info in data['parlays']:
                    legs = parlay_info.get('parlay', [])
                    if not legs:
                        continue

                    # Check if the parlay is a game stack
                    games_in_parlay = {parse_game_from_leg(leg) for leg in legs}
                    games_in_parlay.discard(None)
                    is_game_stack = len(games_in_parlay) == 1
                    
                    game_name = games_in_parlay.pop() if is_game_stack else ""
                    parlay_name = f"{sport.upper()} Game Stack" if is_game_stack else f"{sport.upper()} {len(legs)}-Leg Parlay"
                        
                    formatted_parlay = {
                        "parlay_name": parlay_name,
                        "legs": legs,
                        "total_odds": int(parlay_info.get("parlay_odds", 0)),
                        "implied_odds": parlay_info.get("implied_odds"),
                        "vig_odds": parlay_info.get("vig_odds"),
                        "edge": parlay_info.get("edge"),
                        "vig_edge": parlay_info.get("vig_edge")
                    }
                    
                    if is_game_stack:
                        formatted_parlay["game"] = game_name
                        
                    sport_parlays.append(formatted_parlay)

        except (FileNotFoundError, json.JSONDecodeError):
            all_parlays_data[sport] = []
            continue

        all_parlays_data[sport] = sport_parlays

    output_filename = 'generated_parlays.json'
    
    # Write the file locally
    with open(output_filename, 'w') as f:
        json.dump(all_parlays_data, f, indent=4)
    
    print(f"Successfully generated parlays with detailed odds in {output_filename}")
    
    # Upload to GitHub
    try:
        with open(output_filename, 'r') as f:
            file_content = f.read()
        
        print("Uploading to GitHub...")
        upload_success = upload_to_github(output_filename, file_content)
        
        if upload_success:
            print("🎉 Parlays have been successfully uploaded to GitHub!")
        else:
            print("⚠️ Local file generated successfully, but GitHub upload failed")
            
    except Exception as e:
        print(f"⚠️ Error during GitHub upload: {str(e)}")

if __name__ == "__main__":
    generate_parlays()
    generate_parlay_builder_data() 