import hashlib
import hmac
import json
import time
from urllib.parse import urlparse


class API_auth:
    def generate_headers(
        api_key: str, api_secret: str, method: str, url: str, path: str, data=None
    ) -> dict:
        """
        Called when https requesting - generates api key headers.
        """
        if isinstance(data, dict):
            data = json.dumps(data)
        headers = dict()
        expires = int(round(time.time()) + 5)
        url = url.replace(" ", "%20")
        headers["api-key"] = api_key
        headers["api-expires"] = str(expires)
        headers["api-signature"] = API_auth.generate_signature(
            secret=api_secret,
            verb=method,
            url=url,
            nonce=expires,
            data=data or "",
        )

        return headers

    def generate_signature(
        secret: str, verb: str, url: str, nonce: int, data: str
    ) -> str:
        """
        Generates an API signature. Detals: https://www.bitmex.com/app/apiKeysUsage
        """
        parsed_url = urlparse(url)
        path = parsed_url.path
        if parsed_url.query:
            path = path + "?" + parsed_url.query
        if isinstance(data, (bytes, bytearray)):
            data = data.decode("utf8")
        message = verb + path + str(nonce) + data
        signature = hmac.new(
            bytes(secret, "utf8"), bytes(message, "utf8"), digestmod=hashlib.sha256
        ).hexdigest()

        return signature
