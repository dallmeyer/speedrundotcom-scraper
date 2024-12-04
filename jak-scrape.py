from asyncio import sleep
import requests
import json
import math
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pynput import keyboard


# You'll probably get rate-limited if you try to run this for all games at once
# Comment/uncomment and run just a few games at a time
games = [
    ["jak1", "jak1ext", "jak1og", "jak1ogext"],
    ["Jak_The_Chicken"],
    ["jak2", "jak2ext", "jak2og"],
    ["jak3", "jak3ext"],
    ["jakx", "jakxext"],
    ["daxter", "daxterext"],
    ["jaktlf"]
]
check_vars = ["jak1ext", "jak1og", "jak1ogext", "Jak_The_Chicken", "jak2ext", "jak3ext"]

_game_idx = 0
_month = datetime.today().replace(day=1)

def game_selection_handler(key):
    global _game_idx
    if key == keyboard.Key.down:
        _game_idx = (_game_idx + 1) % len(games)
        print(f"Select game: {games[_game_idx][0]}             ", end='\r', flush=True)
    elif key == keyboard.Key.up:
        _game_idx = (_game_idx - 1) % len(games)
        print(f"Select game: {games[_game_idx][0]}             ", end='\r', flush=True)
    elif key == keyboard.Key.enter:
        print()
        listener.stop()
    elif key == keyboard.Key.esc:
        exit(1)

def month_selection_handler(key):
    global _month
    if key == keyboard.Key.down:
        _month = _month + relativedelta(months=1)
        print(f"Select month: {_month.strftime('%m/%Y')}", end='\r', flush=True)
    elif key == keyboard.Key.up:
        _month = _month - relativedelta(months=1)
        print(f"Select month: {_month.strftime('%m/%Y')}", end='\r', flush=True)
    elif key == keyboard.Key.enter:
        print()
        listener.stop()
    elif key == keyboard.Key.esc:
        exit(1)

base_url = "https://speedrun.com/api/v1"

print(f"Select game: {games[_game_idx][0]}             ", end='\r', flush=True)
with keyboard.Listener(on_press=game_selection_handler) as listener:
    listener.join()
input()

print(f"Select month: {_month.strftime('%m/%Y')}", end='\r', flush=True)
with keyboard.Listener(on_press=month_selection_handler) as listener:
    listener.join()
input()

start_date = _month - relativedelta(days=1)
start = start_date.strftime('%Y-%m-%d')
end_date = _month + relativedelta(months=1)
end = end_date.strftime('%Y-%m-%d')

print(f"Searching for {games[_game_idx][0]} runs between {start} - {end} ...\n")

# remember users to avoid redundant API calls
users = dict()

for g in games[_game_idx]:
    found_run = False
    ret = []
    # print(f"Fetching categories for {g}")
    resp = requests.get(f"{base_url}/games/{g}/categories")
    try:
        cats = json.loads(resp.text)["data"]
    except Exception as e:
        print(f"Error while trying to parse categories {e}", resp.text)
        continue

    for c in cats:
        if c["type"] == "per-level":
            # skip IL categories
            # print(f"Skipping category {c["name"]} for game {g}")
            continue

        # print(f"  Fetching runs for {g}/{c["name"]}")
        variables = None # wait to populate until we find a run
        offset = 0
        more_pages = True
        while more_pages:
            resp = requests.get(f"{base_url}/runs?game={g}&category={c["id"]}&orderby=date&direction=desc&max=200&offset={offset}")
            try:
                runs = json.loads(resp.text)["data"]
            except Exception as e:
                print(f"Error while trying to parse runs {e}", resp.text)
                continue

            more_pages = len(runs) > 0

            for r in runs:
                # print(f"Considering run {r["id"]} from {r["date"]}")
                if r["date"] > end:
                    # too new, just skip
                    continue
                if r["date"] < start:
                    # too old, since runs should be in descending order, we can break early
                    more_pages = False
                    break

                # who dis
                uid = r["players"][0]["id"]
                if uid not in users:
                    # new user, look em up
                    resp = requests.get(f"{base_url}/users/{uid}")
                    try:
                        user = json.loads(resp.text)["data"]
                        users[uid] = user["names"]["international"]
                    except Exception as e:
                        print(f"Error while trying to parse user {e}", resp.text)
                        continue
                runner = users[uid]

                # no rejected runs
                if r["status"]["status"] == "rejected":
                    print(f"    Ignoring {runner}\"s rejected run {r["weblink"]}")
                    continue

                found_run = True

                if variables is None and g in check_vars:
                    # fetch variables for this cat
                    resp = requests.get(f"{base_url}/categories/{c["id"]}/variables")
                    try:
                        vars_tmp = json.loads(resp.text)["data"]
                        variables = dict()
                        for v in vars_tmp:
                            if re.search("NG\\+ Tab", v["name"], re.IGNORECASE) or re.search("cutscene.*skip", v["name"], re.IGNORECASE) or re.search("flut", v["name"], re.IGNORECASE) or re.search("Act", v["name"], re.IGNORECASE) or re.search("File Type", v["name"], re.IGNORECASE):
                                # cutscene skip or jak/flut variable, track it
                                variables[v["id"]] = dict()
                                for vv in v["values"]["values"]:
                                    n = v["values"]["values"][vv]["label"]
                                    variables[v["id"]][vv] = n
                    except Exception as e:
                        print(f"Error while trying to get variables for cat {e}", resp.text)
                        continue
                
                c_name = c["name"]

                if g in check_vars:
                    # check for cutscene skip variable
                    for v in r["values"]:
                        if v in variables:
                            vv = r["values"][v]
                            c_name += f" ({variables[v][vv]})"

                # make time pretty
                t_sec_tmp = r["times"]["primary_t"] # number of seconds
                t_h = math.floor(t_sec_tmp / (60*60))
                t_sec_tmp -= (t_h * 60*60)
                t_m = math.floor(t_sec_tmp / 60)
                t_s = t_sec_tmp - (t_m * 60)
                time = f"{t_h}:{t_m:02}:{t_s:02}"
                
                # passed our filters, add it!
                ret.append({
                    "runner": runner,
                    "category": c_name,
                    "time": time,
                    "date": r["date"],
                    "link": r["weblink"]
                })

            offset += 200
    
    if found_run:
        print()
        print(f"Found run(s) for {g}")
        for r in ret:
            print(f'{r['runner']}, \'{r['category']}, \'{r['time']}, \'{r['date']}, -, -, {r['link']}')