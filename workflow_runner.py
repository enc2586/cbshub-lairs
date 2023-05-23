import requests as req
import json
from datetime import datetime as dt
from bs4 import BeautifulSoup
from pprint import pprint
import pytz
import firebase_init

SIGNIN_URL = "http://www.cbshself.kr/sign/actionLogin.do"
APPLY_URL = "http://www.cbshself.kr/self/requestSelfLrn.do"


def clean_up(str):
    strList = str.split()
    result = " ".join(strList)
    return result


KST = pytz.timezone("Asia/Seoul")

today = dt.utcnow().astimezone(KST)
day_of_week_today = str(today.weekday())
if day_of_week_today in ["5", "6"]:
    day_type = "weekends"
else:
    day_type = "weekdays"

db = firebase_init.db()

db.collection("workflow").document("configuration").update({"botState": "running"})
configuration = db.collection("workflow").document("configuration").get().to_dict()
homeroomTeachers = configuration["homeroom"]

workflows_stream = db.collection("workflow").where("type", "==", day_type).stream()

workflows = {}
for document in workflows_stream:
    id = document.id
    workflow = document.to_dict()

    if workflow["user"] in workflows.keys():
        workflows[workflow["user"]][id] = workflow
    else:
        workflows[workflow["user"]] = {id: workflow}

credentials = {}
names = {}
workflow_queue = {}
for uid, workflow_user_sets in workflows.items():
    user = db.collection("user").document(uid).get().to_dict()
    homeroomTeacher = homeroomTeachers[str(user["grade"])][str(user["classNo"])]
    credentials[uid] = user["selfServiceCredential"]
    names[uid] = user["name"]

    user_queue = {}
    for id, workflow in workflow_user_sets.items():
        reservations = workflow["periods"][day_of_week_today].values()
        if sum(reservations) == 0:
            continue
        else:
            self_form = {
                "roomTcherId": homeroomTeacher,
                "cchTcherId": workflow["teacher"],
                "clssrmId": workflow["classroom"],
                "actCode": "ACT999",
                "actCn": workflow["title"] if workflow["title"] != "" else "자율 학습활동 (cbshub)",
                "sgnId": today.strftime(r"%Y%m%d"),
            }
            workflow_period_sets = []
            for index, reserved in enumerate(reservations):
                if reserved:
                    form_with_period = self_form.copy()
                    form_with_period["lrnPd"] = index + 1
                    workflow_period_sets.append(form_with_period)

            user_queue[id] = workflow_period_sets

    if user_queue != {}:
        workflow_queue[uid] = user_queue

batch = db.batch()
for uid, workflow_user_sets in workflow_queue.items():
    print()
    with req.session() as sess:
        try:
            response = sess.post(SIGNIN_URL, data=credentials[uid])
            page = BeautifulSoup(response.content.decode("utf-8"), "lxml")

            if clean_up(page.li.get_text()) == "선생님은 가입해주세요.":
                raise Exception("Failed to sign in")

        except:
            print(f"{names[uid]}({uid}) 로그인 실패")

            for id in workflow_user_sets.keys():
                batch.update(db.collection("workflow").document(id), {"state": "로그인 실패"})

            continue

        print(f"{names[uid]}({uid}) 로그인 성공")
        for id, workflow_period_sets in workflow_user_sets.items():
            apply_successful = True
            for workflow in workflow_period_sets:
                try:
                    response = sess.post(APPLY_URL, data=workflow)
                    responseJson = json.loads(response.content.decode("utf-8"))

                    if responseJson["result"]["success"] == True:
                        print(f"{workflow['lrnPd']}교시 신청 성공({responseJson['slrnNo']})")
                    else:
                        raise Exception("Failed to Apply")

                except:
                    apply_successful = False
                    print(f"{workflow['lrnPd']}교시 신청 실패")
                    batch.update(db.collection("workflow").document(id), {"state": "신청 실패"})

            if apply_successful:
                batch.update(db.collection("workflow").document(id), {"state": "success"})

batch.commit()

db.collection("workflow").document("configuration").update({"botState": "finished"})
