from pprint import pprint
import firebase_init
from dotenv import load_dotenv

load_dotenv()

db = firebase_init.db()

print("\nClearing workflows...", end=" ")

workflows_stream = db.collection("workflow").stream()

batch = db.batch()
for document in workflows_stream:
    id = document.id
    if id == "configuration":
        continue

    batch.update(db.collection("workflow").document(id), {"state": "idle"})

batch.commit()

db.collection("workflow").document("configuration").update({"botState": "idle"})

print("SUCCESS")
