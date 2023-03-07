import json

with open("key.json") as f:
    key = json.load(f)

text = json.dumps(key)

with open("key.txt", mode="w") as file:
    file.write(text)
