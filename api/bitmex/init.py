import requests


class Init:
    session = requests.Session()
    session.headers.update({"user-agent": "Tmatic"})
    session.headers.update({"content-type": "application/json"})
    session.headers.update({"accept": "application/json"})