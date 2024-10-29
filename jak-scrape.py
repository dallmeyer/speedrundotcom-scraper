import requests
import json
import math
import re

games = [
    "jak1", "jak1ext", "jak1og", "jak1ogext", "Jak_The_Chicken",
    "jak2", "jak2ext", "jak2og",
    "jak3", "jak3ext",
    "jakx", "jakxext",
    "daxter", "daxterext",
    "jaktlf"
]
check_vars = ["jak1og", "jak1ogext", "Jak_The_Chicken"]

base_url = "https://speedrun.com/api/v1"

start = input("Enter start date (e.g. 2024-09-30): ")
end = input("Enter end date (e.g. 2024-11-01): ")

# remember users to avoid redundant API calls
users = dict()

for g in games:
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
            continue

        # print(f"  Fetching runs for {g}/{c["name"]}")
        variables = None # wait to populate until we find a run
        resp = requests.get(f"{base_url}/runs?game={g}&category={c["id"]}&orderby=date&direction=desc")
        try:
            runs = json.loads(resp.text)["data"]
        except Exception as e:
            print(f"Error while trying to parse runs {e}", resp.text)
            continue

        for r in runs:
            if r["date"] > end:
                # too new, just skip
                continue
            if r["date"] < start:
                # too old, since runs should be in descending order, we can break early
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

            found_run = True

            if variables is None and g in check_vars:
                # fetch variables for this cat
                resp = requests.get(f"{base_url}/categories/{c["id"]}/variables")
                try:
                    vars_tmp = json.loads(resp.text)["data"]
                    variables = dict()
                    for v in vars_tmp:
                        if re.search("cutscene.*skip", v["name"], re.IGNORECASE) or re.search("flut", v["name"], re.IGNORECASE):
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
    
    if found_run:
        print()
        print(f"Found run(s) for {g}")
        for r in ret:
            print(f'{r['runner']}, \'{r['category']}, \'{r['time']}, \'{r['date']}, -, -, {r['link']}')