import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Union

import requests

from api.errors import Error
from api.variables import Variables
from common.variables import Variables as var


class Send(Variables):
    """
    Sending HTTP Requests. This class is common to exchanges with the
    exception of Bybit, whose requests are processed by a third-party Pybit
    connector. Each of the exchanges has its own authorization scheme, which
    can be found in the api_auth.py files and located in folders corresponding
    to the names of the exchanges.
    """

    def request(
        self,
        path: str = None,
        verb: str = None,
        postData: dict = None,
        timeout=7,
    ) -> Union[dict, str]:
        """
        Sends a request to the exchange.

        Parameters
        ----------
        self: object
            Markets class instance.
        path: str
            Endpoint path.
        verb: str
            Methods of type GET, POST, PUT.
        postData:
            Payload body of a HTTP request.
        timeout:
            Request timeout.

        Returns
        -------
        dict | None
            Usually requested data in dictionary format. On failure - error
            type.
        """
        url = self.http_url + path
        cur_retries = 1
        while True:
            response = None
            try:
                req = requests.Request(verb, url, json=postData, params=None)
                if isinstance(postData, dict):
                    data = json.dumps(postData)
                else:
                    data = postData
                headers = self.api_auth.generate_headers(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    method=verb,
                    url=url,
                    path=path,
                    data=data,
                )
                req.headers = headers
                prepped = self.session.prepare_request(req)
                response = self.session.send(prepped, timeout=timeout)
                # Make non-200s throw
                response.raise_for_status()
            except Exception as exception:
                if response:
                    response = json.loads(response.text)
                status = Error.handler(
                    self, exception=exception, response=response, verb=verb, path=path
                )
                if status == "RETRY":
                    cur_retries += 1
                else:
                    return status
            else:
                if response:
                    if self.logNumFatal not in ["CANCEL", "BLOCK"]:
                        self.logNumFatal = ""
                    return response.json()
                else:
                    return status
            if cur_retries > self.maxRetryRest:
                self.logger.error(f"{self.name}: Max retries hit. Reboot")
                var.queue_info.put(
                    {
                        "market": self.name,
                        "message": "Max retries hit. Reboot",
                        "time": datetime.now(tz=timezone.utc),
                        "warning": "error",
                    }
                )
                break
            time.sleep(2)
