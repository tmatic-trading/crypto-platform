import json
from datetime import datetime, timezone

from api.variables import Variables
from common.variables import Variables as var


class HostNameIsInvalid(Exception):
    """
    Exception thrown for Tmatic returned errors if HTTP or WebSocket name is
    incorrect.

    Parameters
    ----------
    uri: str
        HTTP or Websocket name.
    """

    def __init__(self, uri: str) -> None:
        self.message = f"{uri} host name is invalid"
        self.status_code = 404
        self.code = self.status_code


class Error(Variables):
    def handler(
        self, exception, response: dict = None, verb: str = None, path: str = None
    ) -> str:
        """
        Handling exceptions according to exchange error codes.

        Parameters
        ----------
        self: object
            Bitmex, Bybit, Deribit, Mexc
        exception: object
            ConnectionError, ReadTimeout, HTTPError ect.
        response: dict
            The response message and error code, if the exception contains
            such information.
        verb: str
            HTTP method: GET, POST, PUT.
        path: str
            HTTP path or method name.

        Returns
        -------
        str
            CANCEL  Exchange loading cancelled.
            BLOCK   Trading blocked for this exchange.
            IGNORE  Error ignored, only saved to log file and displayed.
            FATAL   This market will be reloaded.
            RETRY   Retry the request.
        """

        # canceled = f" - {self.name} loading cancelled."
        error_name = exception.__class__.__name__
        prefix = f"{self.name} - {error_name} - "
        if error_name in ["ConnectionError", "ReadTimeout"]:
            status = "RETRY"
            error_message = prefix + "Unable to contact API"
        elif error_name == "InvalidChannelTypeError":
            status = "BLOCK"
            error_message = prefix + " " + str(exception)
        elif error_name in ["Timeout", "SSLError", "WebSocketTimeoutException"]:
            status = "FATAL"
            error_message = prefix + " " + str(exception)
        elif error_name == "UnauthorizedExceptionError":
            status = "CANCEL"
            error_message = prefix
        elif error_name == "TopicMismatchError":
            status = "IGNORE"
            error_message = prefix + " " + str(exception)
        elif error_name in [
            "HTTPError",
            "InvalidRequestError",
            "FailedRequestError",
            "WebSocketBadStatusException",
        ] or (response and "error" in response):
            response = try_response(response, exception)
            status_code = response["error"]["code"]
            status = self.get_error.status(response)
            if status:
                try:
                    message = self.get_error.value[status].value[status_code]
                except Exception:
                    message = response["error"]["message"]
                error_message = f"{prefix}{status_code} {message}"
            else:
                status = "IGNORE"
                error_message = (
                    prefix
                    + "Unexpected error "
                    + response["error"]["message"]
                    + " - "
                    + str(exception)
                )
        elif error_name in [
            "MissingSchema",
            "WebSocketAddressException",
            "HostNameIsInvalid",
        ]:
            status = "CANCEL"
            error_message = (
                prefix + "Probably the URL is incorrect or bad internet connection."
            )
        else:
            status = "FATAL"
            error_message = prefix + "Unexpected error - " + str(exception)

        logger_message = "On request %s %s - error - %s" % (
            verb,
            path,
            error_message,
        )
        queue_message = {
            "market": self.name,
            "message": logger_message,
            "time": datetime.now(tz=timezone.utc),
            "warning": "error",
        }
        wait = 2
        if status == "RETRY":
            logger_message += f" - wait {wait} sec"
            self.logger.warning(logger_message)
        elif status == "FATAL":
            logger_message += " - fatal. Reboot"
            queue_message["message"] = logger_message
            self.logger.error(logger_message)
            var.queue_info.put(queue_message)
        elif status == "IGNORE":
            self.logger.warning(logger_message)
            queue_message["warning"] = "warning"
            var.queue_info.put(queue_message)
        elif status == "BLOCK":
            logger_message += ". Trading stopped."
            self.logger.warning(logger_message)
            queue_message["warning"] = "warning"
            var.queue_info.put(queue_message)
        elif status == "CANCEL":
            # logger_message += canceled
            self.logger.error(logger_message)
            var.queue_info.put(queue_message)
        if self.logNumFatal == "CANCEL":  # Since the loading process is
            # performed in threads, it may happen that one thread will
            # receive an error like "RETRY" or "FATAL" and another will
            # receive the "CANCEL" error. "CANCEL" has a higher priority and
            # stops the loading process.
            status = "CANCEL"
        if status in ["CANCEL", "BLOCK", "FATAL"]:
            self.logNumFatal = status

        return status


def try_response(response, exception):
    try:
        response["error"]["code"]
        return response
    except Exception:
        try:
            code = exception.__dict__["response"].status_code
            message = exception.__dict__["response"]._content
            message = json.loads(message)["error"]
            if "code" not in message:
                message["code"] = code
            return {"error": message}
        except Exception:
            pass
        try:
            code = exception.status_code
            if hasattr(exception, "message"):
                message = exception.message
            else:
                message = ""
            return {"error": {"code": code, "message": message}}
        except Exception:
            pass
        try:
            # Bitmex HTTPError: 530 Server Error
            code = response.status_code
            return {"error": {"code": code, "message": str(exception)}}
        except Exception:
            pass

        # Save error in error.log when try_response failed.

        error = f"try_response failed {datetime.now()}\n#\n"
        error += f"{exception.__class__.args}\n#\n"
        error += f"___exception {exception}\n#\n"
        error += f"___exception.__class__.__name__ {exception.__class__.__name__}\n#\n"
        try:
            error += f"___exception.__class__.args {exception.__class__.args}\n#\n"
        except Exception:
            error += "exception.__class__.args\n#\n"
        error += f"___exception.__dict__ {exception.__dict__}\n#\n"
        try:
            error += f"___exception.status_code {exception.status_code}\n#\n"
        except Exception:
            error += "no exception.status_code\n#\n"
        try:
            error += f"___exception.message {exception.message}\n#\n"
        except Exception:
            error += "no exception.message\n#\n"
        try:
            error += f"___ exception.args {exception.args}\n#\n"
        except Exception:
            error += "no exception.args\n#\n"
        error += f"___response {response}\n#\n"
        try:
            error += f"___ response.__dict__ {response.__dict__}\n#\n"
        except Exception:
            error += "no response.__dict__\n#\n"
        try:
            error += f"___ response.status_code {response.status_code}\n#\n"
        except Exception:
            error += "no response.status_code\n#\n"
        try:
            error += f"___response.message {response.message}\n#\n"
        except Exception:
            error += "no response.message\n#\n"
        try:
            error += f"___ response.args {response.args}\n#\n"
        except Exception:
            error += "no response.args\n#\n"
        error += "#\n#\n"
        with open("error.log", "a") as f:
            f.write(error)

        return {"error": {"code": 0, "message": ""}}
