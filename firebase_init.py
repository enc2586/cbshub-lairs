import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import json
import os
from dotenv import load_dotenv

load_dotenv()


def db():
    cred = credentials.Certificate(os.getenv("FIREBASE_CONFIG"))

    firebase_admin.initialize_app(cred)
    return firestore.client()
