import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import json
import os

FIREBASE_CONFIG = os.environ["FIREBASE_CONFIG"]


def db():
    cred = credentials.Certificate(json.loads(FIREBASE_CONFIG))

    firebase_admin.initialize_app(cred)
    return firestore.client()
