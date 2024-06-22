import hashlib
import hmac
import random
import time

from requests.auth import AuthBase


class API_auth(AuthBase):
    def generate_headers(
        api_key: str, api_secret: str, method: str, url: str, path: str, data=None
    ) -> dict:
        """
        Called when forming a request - generates api key headers.
        """
        tstamp = str(int(time.time()) * 1000)
        nonce = str(random.randbytes(15))
        signature = API_auth.generate_signature(
            tstamp=tstamp,
            secret=api_secret,
            verb=method,
            uri=path,
            nonce=nonce,
            msg=data or "",
        )
        authorization = (
            "deri-hmac-sha256 id="
            + api_key
            + ",ts="
            + tstamp
            + ",sig="
            + signature
            + ",nonce="
            + nonce
        )
        headers = {"Authorization": authorization}

        return headers

    def generate_signature(
        tstamp: str, secret: str, verb: str, uri: str, nonce: str, msg: str
    ) -> str:
        """
        # Generates an API signature. Detals:
                                https://docs.deribit.com/#authentication
        """
        request_data = verb + "\n" + uri + "\n" + msg + "\n"
        stringToSign: str = tstamp + "\n" + nonce + "\n" + request_data
        byte_key = secret.encode()
        message = stringToSign.encode()
        signature = hmac.new(byte_key, message, hashlib.sha256).hexdigest()

        return signature
