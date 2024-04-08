import logging
from api.variables import Variables

logger = logging.getLogger(__name__)

def exception(method):
    """
    Handling HTTP request and websocket errors
    """    
    def decorator(*args, **kwargs):
        self: Variables = args[0]
        try:
            result = method(*args, **kwargs)
            self.logNumFatal = 0
            return result
        except Exception as exception:
            name = exception.__class__.__name__
            message = name + " - " + str(exception)
            if name == "ConnectionError": # requests module
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "SSLError": # requests module
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "ReadTimeout": # requests module
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "FailedRequestError": # pybit http
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "InvalidRequestError": # pybit http
                logger.error(message)
                if exception.status_code == 10004: # error sign!
                    self.logNumFatal = 2001
                else:
                    self.logNumFatal = 1001
            elif name == "InvalidChannelTypeError": # pybit ws
                logger.error(message)
                self.logNumFatal = 2002
            elif name == "UnauthorizedExceptionError": # pybit ws
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "TopicMismatchError": # pybit ws
                logger.error(message)
                self.logNumFatal = 1001
            else:
                print("_____________", name)
                raise exception
            
    return decorator
