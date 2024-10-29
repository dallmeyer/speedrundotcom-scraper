import requests
import json
import math

games = [
    "jak1", "jak1ext", "jak1og", "jak1ogext", "Jak_The_Chicken",
    "jak2", "jak2ext", "jak2og",
    "jak3", "jak3ext",
    "jakx", "jakxext",
    "daxter", "daxterext",
    "jaktlf"
]

ret = dict()

base_url = "https://speedrun.com/api/v1"

start = input("Enter start date (e.g. 2024-09-30): ")
end = input("Enter end date (e.g. 2024-11-01): ")

for g in games:
    ret[g] = []
    print(f"Fetching categories for {g}")
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
        resp = requests.get(f"{base_url}/runs?game={g}&category={c["id"]}&orderby=date&direction=desc")
        try:
            runs = json.loads(resp.text)["data"]
        except Exception as e:
            print(f"Error while trying to parse runs {e}", resp.text)
            continue

        found_run = False
        for r in runs:
            if r["date"] > end:
                # too new, just skip
                continue
            if r["date"] < start:
                # too old, since runs should be in descending order, we can break early
                break

            # who dis
            uid = r["players"][0]["id"]
            resp = requests.get(f"{base_url}/users/{uid}")
            try:
                user = json.loads(resp.text)["data"]
                runner = user["names"]["international"]
            except Exception as e:
                print(f"Error while trying to parse user {e}", resp.text)
                continue

            # no rejected runs
            if r["status"]["status"] == "rejected":
                print(f"    Ignoring {runner}\"s rejected run {r["weblink"]}")

            found_run = True

            # make time pretty
            t_sec_tmp = r["times"]["primary_t"] # number of seconds
            t_h = math.floor(t_sec_tmp / (60*60))
            t_sec_tmp -= (t_h * 60*60)
            t_m = math.floor(t_sec_tmp / 60)
            t_s = t_sec_tmp - (t_m * 60)
            time = f"{t_h:02}:{t_m:02}:{t_s:02}"
            
            # passed our filters, add it!
            ret[g].append({
                "runner": runner,
                "category": c["name"],
                "time": time,
                "date": r["date"],
                "link": r["weblink"]
            })
        
        if found_run:
            print(f"  Found run(s) for {g}/{c["name"]}")

print(json.dumps(ret, indent=2))