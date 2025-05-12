import hashlib
import hmac
import time
from urllib.parse import urlparse


class API_auth:
    def generate_headers(
        api_key: str, api_secret: str, method: str, url: str, path: str, data=None
    ) -> dict:
        """
        Called when forming a request - generates api key headers.
        Details in the exchange documentation.
        """
        headers = dict()
        """
        Place the code here.
        """

        return headers

    def generate_signature(
        secret: str, verb: str, url: str, nonce: int, data: str
    ) -> str:
        """
        Generates an API signature. Details in the exchange documentation.
        """
        signature = ""
        """
        Place the code here.
        """

        return signature