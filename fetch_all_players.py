import requests
import json
import os
from datetime import datetime

def fetch_all_players():
    """Fetch all players using the IFPA API v1 endpoint"""
    url = "https://api.ifpapinball.com/v1/rankings"
    api_key = "5655812d8d292a864b0785b565b73e59"
    headers = {"X-API-Key": api_key}
    all_players = []
    current_position = 1
    batch_size = 500
    more_players = True

    while more_players:
        params = {"start_pos": current_position, "count": batch_size}
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        # Correctly extract player data from the 'rankings' dictionary
        batch_players = list(data.get('rankings', {}).values())
        all_players.extend(batch_players)
        if len(batch_players) < batch_size:
            more_players = False
        else:
            current_position += batch_size

    # Save to a JSON file
    with open('static/data/all_players.json', 'w') as f:
        json.dump({
            'updated': datetime.now().strftime('%Y-%m-%d'),
            'players': all_players
        }, f, indent=2)

    print(f"Successfully saved {len(all_players)} players to static/data/all_players.json")
    return all_players

if __name__ == "__main__":
    fetch_all_players()
