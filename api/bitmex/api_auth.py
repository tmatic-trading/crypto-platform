import hashlib
import hmac
import time
from urllib.parse import urlparse

from requests.auth import AuthBase


class API_auth(AuthBase):
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key
        self.api_secret = api_secret

    def __call__(self, req):
        """
        Called when forming a request - generates api key headers.
        """
        expires = int(round(time.time()) + 5)
        req.headers["api-key"] = self.api_key
        req.headers["api-expires"] = str(expires)
        req.headers["api-signature"] = generate_signature(
            secret=self.api_secret,
            verb=req.method,
            url=req.url,
            nonce=expires,
            data=req.body or "",
        )

        return req


def generate_signature(secret: str, verb: str, url: str, nonce: int, data: str) -> str:
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
