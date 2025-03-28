import requests


class MomentumClient:
    def __init__(self, base_url, api_key, device_key):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.headers = {
            "x-api-key": api_key,
            "x-momentum-client": "momentum.se-fastighetminasidor",
            "x-momentum-device-key": device_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def set_token(self, token):
        self.headers["Authorization"] = f"Bearer {token}"

    def post(self, path, json=None):
        return self.session.post(f"{self.base_url}{path}", headers=self.headers, json=json)

    def get(self, path):
        return self.session.get(f"{self.base_url}{path}", headers=self.headers)
