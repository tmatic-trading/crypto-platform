import hashlib
import hmac
import json
import random
import time
from datetime import datetime, timezone
from typing import Union

import requests

from api.variables import Variables
from common.variables import Variables as var


class Send(Variables):
    def request(
        self,
        path: str = None,
        verb: str = None,
        postData=None,
        timeout=7,
        theorPrice=None,
    ) -> Union[dict, list, None]:
        """
        Sends a request to the exchange
        """

        def info_warn_err(whatNow, textNow, codeNow=0):
            if whatNow == "INFO":
                self.logger.info(textNow)
            elif whatNow == "WARN":
                self.logger.warning(textNow)
                if codeNow > self.logNumFatal:
                    self.logNumFatal = codeNow
            else:
                self.logger.error(textNow)
                if codeNow > self.logNumFatal:
                    var.queue_info.put(
                        {
                            "market": self.name,
                            "message": textNow,
                            "time": datetime.now(tz=timezone.utc),
                            "warning": True,
                        }
                    )
                    if codeNow == 3:
                        self.logNumFatal = 0
                    else:
                        self.logNumFatal = codeNow

        cur_retries = 1
        tstamp = str(int(time.time()) * 1000)
        nonce = str(random.randbytes(15))
        request_data = verb + "\n" + path + "\n" + json.dumps(postData) + "\n"
        stringToSign: str = tstamp + "\n" + nonce + "\n" + request_data
        byte_key = self.api_secret.encode()
        message = stringToSign.encode()
        signature = hmac.new(byte_key, message, hashlib.sha256).hexdigest()
        url = self.http_url + path
        req = requests.Request(verb, url, json=postData, params=None)
        authorization = (
            "deri-hmac-sha256 id="
            + self.api_key
            + ",ts="
            + tstamp
            + ",sig="
            + signature
            + ",nonce="
            + nonce
        )
        req.headers = {"Authorization": authorization}
        prepped = self.session.prepare_request(req)
        print(authorization, url)
        try:
            print(url[1], url[2], url[3], url[4])
            if theorPrice is None:
                info_warn_err(
                    "INFO",
                    "("
                    + url[:5]
                    + ") sending %s to %s: %s"
                    % (verb, path, json.dumps(postData or "")),
                )
            else:
                info_warn_err(
                    "INFO",
                    "("
                    + url[:5]
                    + ") sending %s to %s: %s, theor: %s"
                    % (
                        verb,
                        path,
                        json.dumps(postData or ""),
                        theorPrice,
                    ),
                )
            response = self.session.send(prepped, timeout=timeout)
        except requests.exceptions.HTTPError as error:
            print("________+", error)
            pass
        except requests.exceptions.ConnectionError as error:
            info_warn_err(
                "ERROR",
                "Unable to contact API: %s. %s: %s"
                % (error, url, json.dumps(postData or "")),
                1002,
            )
            var.queue_info.put(
                {
                    "market": self.name,
                    "message": "Websocket. Unable to contact API",
                    "time": datetime.now(tz=timezone.utc),
                    "warning": True,
                }
            )
            cur_retries += 1

        return response
