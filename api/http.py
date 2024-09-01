import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Union

import requests

from api.bitmex.api_auth import API_auth as Bitmex_API_auth
from api.bitmex.error import ErrorStatus as BitmexErrorStatus
from api.deribit.api_auth import API_auth as Deribit_API_auth
from api.deribit.error import ErrorStatus as DeribitErrorStatus
from api.variables import Variables
from common.variables import Variables as var


class GetErrorStatus(Enum):
    Bitmex = BitmexErrorStatus
    Deribit = DeribitErrorStatus

    def get_status(name, res):
        return GetErrorStatus[name].value.error_status(res)


class Auth(Enum):
    Bitmex = Bitmex_API_auth
    Deribit = Deribit_API_auth


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
        postData=None,
        timeout=7,
        theorPrice=None,
    ) -> Union[dict, list, None]:
        """
        Sends a request to the exchange.
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
                headers = Auth[self.name].value.generate_headers(
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
                exception = exception.__class__.__name__
                if exception in ["ConnectionError", "ReadTimeout"]:
                    status = "RETRY"
                    error_message = exception + ". Unable to contact API"
                elif exception == "Timeout":
                    status = "FATAL"
                    error_message = exception
                elif exception == "HTTPError":
                    res = json.loads(response.text)
                    status = GetErrorStatus.get_status(self.name, res)
                    if status:
                        error_message = res["error"]["message"]
                    else:
                        status = "IGNORE"
                        error_message = (
                            "Unexpected HTTPError" + " " + res["error"]["message"]
                        )
                else:
                    status = "FATAL"
                    error_message = "Unexpected error " + exception
                logger_message = "On request %s %s - error - %s" % (
                    verb,
                    path,
                    error_message,
                )
                queue_message = {
                    "market": self.name,
                    "message": logger_message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": True,
                }
                wait = 2
                if status == "RETRY":
                    cur_retries += 1
                    logger_message += f" - wait {wait} sec"
                    self.logger.warning(logger_message)
                elif status == "FATAL":
                    logger_message += " - fatal. Reboot"
                    queue_message["message"] = logger_message
                    self.logger.error(logger_message)
                    var.queue_info.put(queue_message)
                    self.logNumFatal = status
                    return status
                elif status == "IGNORE":
                    self.logger.warning(logger_message)
                    var.queue_info.put(queue_message)
                    return status
                elif status == "BLOCK":
                    logger_message += ". Trading stopped."
                    self.logger.warning(logger_message)
                    var.queue_info.put(queue_message)
                    self.logNumFatal = status
                    return status
            else:
                if response:
                    self.logNumFatal = ""
                    return response.json()
                else:
                    return None
            if cur_retries > self.maxRetryRest:
                self.logger.error(f"{self.name}: Max retries hit. Reboot")
                var.queue_info.put(
                    {
                        "market": self.name,
                        "message": "Max retries hit. Reboot",
                        "time": datetime.now(tz=timezone.utc),
                        "warning": True,
                    }
                )
                break
            time.sleep(wait)
