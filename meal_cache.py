import requests
import urllib.parse
import os
import re
import datetime as dt

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

for meal in meals:
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
    meal_type = meal["MMEAL_SC_NM"]
    meal_no = meal["MMEAL_SC_CODE"]

    set = {"type": meal_type, "menu": menu_list, "calorie": calorie}

    if id in data.keys():
        data[id][meal_no] = set
    else:
        data[id] = {meal_no: set}

batch = db.batch()
meal_ref = db.collection("meal")

for id, meal_set in data.items():
    batch.set(meal_ref.document(id), meal_set)

batch.commit()
