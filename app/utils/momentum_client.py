"""
MomentumClient Wrapper

A simplified client for communicating with the Momentum housing queue API.
Handles token-based authentication, headers, and basic GET/POST requests.
"""

import requests
from requests import Response


class MomentumClient:
    """
    Client for interacting with Momentum's REST API using token-based headers.
    """

    def __init__(self, base_url: str, api_key: str):
        """
        Initializes the client with base URL and API key.

        Args:
            base_url (str): The base API URL of the Momentum site.
            api_key (str): The public API key required for authentication.
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.headers = {
            "x-api-key": api_key,
            "x-momentum-client": "momentum.se-fastighetminasidor",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def set_token(self, token: str) -> None:
        """
        Sets the OAuth2 access token for authenticated requests.

        Args:
            token (str): The bearer token from login.
        """
        self.headers["Authorization"] = f"Bearer {token}"

    def post(self, path: str, json: dict = None) -> Response:
        """
        Sends a POST request to the API.

        Args:
            path (str): API endpoint path.
            json (dict, optional): JSON payload to send.

        Returns:
            Response: The HTTP response object.
        """
        return self.session.post(f"{self.base_url}{path}", headers=self.headers, json=json)

    def get(self, path: str) -> Response:
        """
        Sends a GET request to the API.

        Args:
            path (str): API endpoint path.

        Returns:
            Response: The HTTP response object.
        """
        return self.session.get(f"{self.base_url}{path}", headers=self.headers)
