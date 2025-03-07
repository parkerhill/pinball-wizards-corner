import requests
import json
import os
from datetime import datetime


def fetch_nm_nacs_standings():
    """Fetch NACS 2025 standings for New Mexico using the IFPA API"""
    url = "https://api.ifpapinball.com/series/NACS/standings"
    api_key = "5655812d8d292a864b0785b565b73e59"  # API key
    headers = {
        "X-API-Key": api_key
    }
    params = {
        "year": 2025,
        "region_code": "NM"
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract standings data
        standings = data.get('standings', [])
        print(f"Fetched {len(standings)} NACS standings for New Mexico in 2025")

        # Save to a JSON file
        os.makedirs('static/data', exist_ok=True)
        with open('static/data/nm_nacs_standings_2025.json', 'w') as f:
            json.dump({
                'updated': datetime.now().strftime('%Y-%m-%d'),
                'standings': standings
            }, f, indent=2)

        print(f"Successfully saved NACS standings for New Mexico to static/data/nm_nacs_standings_2025.json")
        return standings

    except Exception as e:
        print(f"Error fetching NACS standings: {e}")
        return []


def fetch_nm_players():
    """
    Fetch all players who are either from New Mexico
    OR who have NACS standings in New Mexico
    """

    # First get the NACS standings to know which player IDs to include
    nacs_standings = fetch_nm_nacs_standings()
    nacs_player_ids = [standing['player_id'] for standing in nacs_standings]

    # IFPA API endpoint for country rankings
    url = "https://api.ifpapinball.com/rankings/country"

    # Your API key
    api_key = "5655812d8d292a864b0785b565b73e59"

    # Headers with your API key
    headers = {
        "X-API-Key": api_key
    }

    # Initialize variables for pagination
    all_us_players = []
    current_position = 1
    batch_size = 500  # Maximum allowed by the API
    more_players = True

    try:
        # Loop to fetch all US players in batches
        while more_players:
            # Parameters for the current batch
            params = {
                "country": "US",
                "count": batch_size,
                "start_pos": current_position
            }

            # Make the API request
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Get the current batch of players
            batch_players = data.get('rankings', [])
            batch_count = len(batch_players)

            print(f"Fetched batch of {batch_count} players starting at position {current_position}")

            # Add to our collection
            all_us_players.extend(batch_players)

            # If we received fewer players than requested, we've reached the end
            if batch_count < batch_size:
                more_players = False
            else:
                # Move to next batch
                current_position += batch_size

        print(f"Total US players fetched: {len(all_us_players)}")

        # Filter players from New Mexico OR with NACS standings in NM
        nm_players = []
        for player in all_us_players:
            if player.get('stateprov') == 'NM' or player.get('player_id') in nacs_player_ids:
                nm_players.append(player)

        print(f"Found {len(nm_players)} players from New Mexico or with NM NACS standings")

        # Now, fetch individual data for any NACS players we didn't find in the US rankings
        # (This could happen if they're international or not in current rankings)
        missing_player_ids = [pid for pid in nacs_player_ids if pid not in [p.get('player_id') for p in nm_players]]

        for player_id in missing_player_ids:
            try:
                # Fetch the individual player data
                player_url = f"https://api.ifpapinball.com/player/{player_id}"
                player_response = requests.get(player_url, headers=headers)
                player_response.raise_for_status()
                player_data = player_response.json().get('player', {})

                # Get the player's ranking data
                player_stats = player_data.get('player_stats', {})

                # Create a player record similar to what we'd get from the rankings API
                player_record = {
                    'player_id': player_id,
                    'name': player_data.get('first_name', '') + ' ' + player_data.get('last_name', ''),
                    'current_wppr_rank': player_stats.get('current_wppr_rank', '-'),
                    'wppr_points': player_stats.get('wppr_points', 0),
                    'city': player_data.get('city', ''),
                    'stateprov': player_data.get('state', ''),
                    'countryname': player_data.get('country_name', '')
                }

                nm_players.append(player_record)
                print(f"Added individual player data for {player_record['name']} (ID: {player_id})")
            except Exception as e:
                print(f"Error fetching individual player data for ID {player_id}: {e}")

        # Sort by WPPR rank (current_wppr_rank)
        nm_players.sort(key=lambda x: int(x.get('current_wppr_rank', '999999')))

        # Create directory if it doesn't exist
        os.makedirs('static/data', exist_ok=True)

        # Save to a JSON file
        with open('static/data/nm_players.json', 'w') as f:
            json.dump({
                'updated': datetime.now().strftime('%Y-%m-%d'),
                'players': nm_players
            }, f, indent=2)

        print(f"Successfully saved {len(nm_players)} players to static/data/nm_players.json")

        # Print the first few NM players to verify
        if nm_players:
            print("\nTop 5 New Mexico players:")
            for i, player in enumerate(nm_players[:5], 1):
                print(
                    f"{i}. {player.get('name')} - Rank: {player.get('current_wppr_rank')}, City: {player.get('city')}")

        return nm_players

    except Exception as e:
        print(f"Error fetching player data: {e}")
        return []


def fetch_nm_players_with_nacs():
    """Fetch NM players with both WPPR and NACS rankings"""
    # Fetch WPPR rankings for NM players (including those with NACS standings)
    wppr_players = fetch_nm_players()

    # Fetch NACS standings for NM
    nacs_standings = fetch_nm_nacs_standings()

    # Create a dictionary of WPPR players by player_id for easy lookup
    wppr_dict = {player['player_id']: player for player in wppr_players}

    # Merge NACS standings with WPPR data
    combined_players = []
    for standing in nacs_standings:
        player_id = standing['player_id']
        if player_id in wppr_dict:
            # Player exists in both datasets
            combined_player = wppr_dict[player_id].copy()
            combined_player['series_rank'] = standing['series_rank']  # Add NACS rank
            combined_player['nacs_wppr_points'] = standing['wppr_points']  # NACS-specific WPPR points
            combined_player['nacs_event_count'] = standing['event_count']
            combined_player['nacs_win_count'] = standing['win_count']
            combined_players.append(combined_player)
        else:
            # This should be rare now, but handle just in case
            print(f"Warning: Player {standing.get('player_name')} (ID: {player_id}) not found in WPPR data")

    # Sort by NACS series_rank (state ranking)
    combined_players.sort(key=lambda x: int(x['series_rank']))

    # Save combined data
    os.makedirs('static/data', exist_ok=True)
    with open('static/data/nm_combined_rankings_2025.json', 'w') as f:
        json.dump({
            'updated': datetime.now().strftime('%Y-%m-%d'),
            'players': combined_players
        }, f, indent=2)

    print(f"Successfully saved combined NM rankings (NACS + WPPR) to static/data/nm_combined_rankings_2025.json")
    return combined_players


if __name__ == "__main__":
    fetch_nm_players_with_nacs()