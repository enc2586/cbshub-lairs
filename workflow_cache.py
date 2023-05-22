import firebase_init
from firebase_admin import firestore

import requests as req
from bs4 import BeautifulSoup

import os

SIGNIN_URL = "http://www.cbshself.kr/sign/actionLogin.do"
TCRINFO_URL = "http://www.cbshself.kr/self/writeSelfLrnReqst.do"
ROOMINFO_URL = "http://www.cbshself.kr/clssrm/buldDrw.do"

print("\nUpdating workflow cache... ", end=" ")

CBSHSELF_ID = os.environ["CBSHSELF_ID"]
CBSHSELF_PW = os.environ["CBSHSELF_PW"]

db = firebase_init.db()


def cleanUp(str):
    strList = str.split()
    result = " ".join(strList)
    return result


cred = {"id": CBSHSELF_ID, "password": CBSHSELF_PW}

with req.session() as sess:
    res = sess.post(SIGNIN_URL, data=cred)
    pgdata_raw = BeautifulSoup(res.content.decode("utf-8"), "lxml")
    login_chk = cleanUp(pgdata_raw.li.get_text())

    if login_chk == "선생님은 가입해주세요.":
        print("로그인 실패")

    reqest = sess.get(TCRINFO_URL)
    res = reqest.content.decode("utf-8")
    site_data = BeautifulSoup(res, "html.parser")

    res = sess.get(ROOMINFO_URL)
    response = BeautifulSoup(res.content.decode("utf-8"), "html.parser")

    rawlst = response.select("div > div > div > div.data-list.custom-list > table > tbody > tr")

tcr = {}
for element in site_data.find_all("option"):
    if element["value"]:
        tcr[element.get_text()] = element["value"]

tcr["지도교사없음"] = ""


rmlst = {}

for rawhtml in rawlst:
    datalst = rawhtml.select("td")
    name = datalst[1].get_text()
    if "삭제" not in name:
        rmlst[name] = {
            "floor": datalst[0].get_text(),
            "maxppl": cleanUp(datalst[3].get_text()),
            "tcher": datalst[2].get_text(),
            "id": datalst[4].select_one("div > input")["value"],
        }


configRef = db.collection("workflow").document("configuration")

formerConfig = configRef.get().to_dict()
configRef.update({"teachers": tcr, "classes": rmlst, "lastUpdated": firestore.SERVER_TIMESTAMP})

print("SUCCESS")
print(
    f"teachers(total: {len(tcr)}, delta: {len(tcr)-len(formerConfig['teachers'])}), classes(total: {len(rmlst.keys())}, delta: {len(rmlst.keys()) - len(formerConfig['classes'])})"
)
