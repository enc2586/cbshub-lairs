import requests
import urllib.parse
import os
import re
import datetime as dt
from pprint import pprint

import firebase_init

from dotenv import load_dotenv

load_dotenv()

today = dt.datetime.today()
max_date = today + dt.timedelta(weeks=8)
min_date = today - dt.timedelta(weeks=8)

db = firebase_init.db()

BASE_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo?"
params = {
    "KEY": os.getenv("NEIS_KEY"),
    "Type": "json",
    "ATPT_OFCDC_SC_CODE": "M10",
    "SD_SCHUL_CODE": "8000075",
    "MLSV_FROM_YMD": min_date.strftime("%Y%m%d"),
    "MLSV_TO_YMD": max_date.strftime("%Y%m%d"),
}
encoded_params = urllib.parse.urlencode(params)

target = BASE_URL + encoded_params
response = requests.get(target)

meals = response.json()["mealServiceDietInfo"][1]["row"]

allergy_regex = r"\(\d+(\.\d+)*\.\)$"

data = {}

meal_variant_dict = {"조식": 0, "중식": 1, "석식": 2}

count = 0

for meal in meals:
    meal_type = meal["MMEAL_SC_NM"]
    if meal_type in ("조식", "중식", "석식"):
        meal_no = meal_variant_dict[meal_type]
    else:
        continue

    count += 1

    id = meal["MLSV_YMD"]

    menu_list = []
    menus = meal["DDISH_NM"].split("<br/>")
    for menu in menus:
        menu_string = menu.strip()
        m = re.search(allergy_regex, menu_string)
        if m:
            menu_list.append(
                {
                    "name": menu_string[: m.start()].strip(),
                    "allergy": list(map(int, m.group()[1:-1].split(".")[:-1])),
                }
            )
        else:
            menu_list.append({"name": menu_string, "allergy": []})

    calorie = float(meal["CAL_INFO"][:-5])

    set = {"type": meal_type, "menu": menu_list, "calorie": calorie}

    if id in data.keys():
        data[id]["data"][meal_no] = set
    else:
        temp_list = [None, None, None]
        temp_list[meal_no] = set
        data[id] = {"data": temp_list}

batch = db.batch()
meal_ref = db.collection("meal")

for id, meal_set in data.items():
    meal_set["date"] = dt.datetime.strptime(id, "%Y%m%d")
    batch.set(meal_ref.document(id), meal_set)

batch.commit()

print(
    f'Processed {count} meals between {min_date.strftime("%Y%m%d")} and {max_date.strftime("%Y%m%d")}.'
)
