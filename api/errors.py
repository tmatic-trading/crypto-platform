from datetime import datetime, timezone
from enum import Enum

from api.bitmex.error import ErrorStatus as BitmexErrorStatus
from api.bybit.error import ErrorStatus as BybitErrorStatus
from api.deribit.error import ErrorStatus as DeribitErrorStatus
from api.variables import Variables
from common.variables import Variables as var


class HostNameIsInvalid(Exception):
    """
    Exception thrown for Tmatic returned errors if HTTP or WebSocket name is
    incorrect.

    Parameters:
    ----------
    uri: str
        HTTP or Websocket name.
    """

    def __init__(self, uri: str) -> None:
        self.message = f"{uri} host name is invalid"
        self.status_code = 404
        self.code = self.status_code


class GetErrorStatus(Enum):
    Bitmex = BitmexErrorStatus
    Bybit = BybitErrorStatus
    Deribit = DeribitErrorStatus

    def get_status(name, res):
        return GetErrorStatus[name].value.error_status(res)


class Error(Variables):
    def handler(
        self, exception, response: dict = None, verb: str = None, path: str = None
    ) -> str:
        """
        Handling exceptions according to exchange error codes.

        Parameters
        ----------
        self: object
            Bitmex, Bybit, Deribit
        exception: object
            ConnectionError, ReadTimeout, HTTPError ect.
        response: dict
            The response message and error code, if the exception contains
            such information.
        verb: str
            HTTP method: GET, POST, PUT.
        path: str
            HTTP path or method name for Bybit.

        Returns
        -------
        str
            CANCEL  Exchange loading cancelled.
            BLOCK   Trading blocked for this exchange.
            IGNORE  Error ignored, only saved to log file and displayed.
            FATAL   This market will be reloaded.
            RETRY   Retry request (Bitmex, Deribit).
        """
        canceled = f" - {self.name} loading cancelled."
        error_name = exception.__class__.__name__
        prefix = f"{self.name} - {error_name} - "
        if error_name in ["ConnectionError", "ReadTimeout"]:
            status = "RETRY"
            error_message = prefix + error_name + ". Unable to contact API"
        elif error_name == "InvalidChannelTypeError":
            status = "BLOCK"
            error_message = prefix + error_name + " " + str(exception)
        elif error_name in ["Timeout", "SSLError", "WebSocketTimeoutException"]:
            status = "FATAL"
            error_message = prefix + error_name + " " + str(exception)
        elif error_name == "UnauthorizedExceptionError":
            status = "CANCEL"
            error_message = prefix + error_name
        elif error_name == "TopicMismatchError":
            status = "IGNORE"
            error_message = prefix + error_name + " " + str(exception)
        elif error_name in [
            "HTTPError",
            "InvalidRequestError",
            "FailedRequestError",
            "WebSocketBadStatusException",
        ]:
            response = try_response(response, exception)
            status_code = response["error"]["code"]
            status = GetErrorStatus.get_status(self.name, response)
            if status:
                try:
                    message = GetErrorStatus[self.name].value[status].value[status_code]
                except Exception:
                    message = response["error"]["message"]
                error_message = f"{prefix}{status_code} {message}"
            else:
                status = "IGNORE"
                error_message = (
                    prefix
                    + "Unexpected "
                    + error_name
                    + " "
                    + response["error"]["message"]
                )
        elif error_name in [
            "MissingSchema",
            "WebSocketAddressException",
            "HostNameIsInvalid",
        ]:
            status = "CANCEL"
            error_message = (
                prefix
                + error_name
                + ". Probably the URL is incorrect. "
                + self.name
                + " loading cancelled."
            )
        else:
            status = "FATAL"
            error_message = prefix + "Unexpected error " + error_name

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
            logger_message += canceled
            self.logger.error(logger_message)
            var.queue_info.put(queue_message)
        if self.logNumFatal == "CANCEL":  # Since the loading process is
            # performed in threads, it may happen that one thread will
            # receive an error like "RETRY" or "FATAL" and another will
            # receive the "CANCEL" error. "CANCEL" has a higher priority and
            # stops the loading process.
            status = "CANCEL"
        self.logNumFatal = status

        return status


def try_response(response, exception):
    try:
        response["error"]["code"]
        return response
    except Exception:
        try:
            code = exception.__dict__["response"].status_code
            message = str(exception.__dict__["response"]._content)
            return {"error": {"code": code, "message": message}}
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
