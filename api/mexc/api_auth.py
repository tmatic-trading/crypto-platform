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
        tstamp = str(int(time.time() * 1000))
        if isinstance(data, dict):
            data = "&".join([f"{k}={v}" for k, v in sorted(data.items())])
        
        headers = dict()
        headers["Signature"] = API_auth.generate_signature(
            api_key=api_key, 
            secret=api_secret,
            tstamp=tstamp, 
            data=data or "",
        )
        headers["Request-Time"] = tstamp
        headers["Content-Type"] = "application/json"
        headers["ApiKey"] = api_key
        
        return headers

    def generate_signature(
        api_key: str,  secret: str, tstamp: str, data: str
    ) -> str:
        """
        Generates an API signature. Details in the exchange documentation.
        """
        data = api_key + tstamp + data
        signature = hmac.new(
            secret.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature
