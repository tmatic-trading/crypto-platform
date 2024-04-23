import logging

from api.variables import Variables
from common.variables import Variables as var
from display.variables import Tables

logger = logging.getLogger(__name__)


def exception(method):
    """
    Handling HTTP request and websocket errors
    """

    def decorator(*args, **kwargs):
        self: Variables = args[0]
        try:
            result = method(*args, **kwargs)
            if self.logNumFatal < 0:
                self.logNumFatal = 0
            return result
        except Exception as exception:
            name = exception.__class__.__name__
            message = name + " - " + str(exception)
            if name == "ConnectionError":  # requests module
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "SSLError":  # requests module
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "ReadTimeout":  # requests module
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "FailedRequestError":  # pybit http
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "InvalidRequestError":  # pybit http
                logger.error(message)
                if exception.status_code == 10004:  # error sign!
                    self.logNumFatal = 2001
                elif exception.status_code in [
                    110007,
                    170131,
                ]:  # Insufficient available balance
                    self.logNumFatal = 2
                elif (
                    exception.status_code == 181001
                ):  # category only support linear or option
                    self.logNumFatal = 3
                elif exception.status_code == 170135: # Order quantity exceeded upper limit
                    pass
                elif exception.status_code == 10001: # The number of contracts exceeds maximum limit allowed
                    pass
                elif exception.status_code == 170193: # Buy order price cannot be higher
                    pass
                elif exception.status_code == 110094: # Order does not meet minimum order value
                    pass
                elif exception.status_code == 110003: # price is out of range
                    pass
                elif exception.status_code == 110001: # Order does not exist
                    pass
                else:
                    self.logNumFatal = 1001
            elif name == "InvalidChannelTypeError":  # pybit ws
                logger.error(message)
                self.logNumFatal = 2002
            elif name == "UnauthorizedExceptionError":  # pybit ws
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "TopicMismatchError":  # pybit ws
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "WebSocketTimeoutException":  # pybit ws
                logger.error(message)
                self.logNumFatal = 1001
            else:
                print("_____________", name)
                raise exception

    return decorator
