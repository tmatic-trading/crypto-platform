import logging
from api.variables import Variables

logger = logging.getLogger(__name__)

def http_exception(func):
    """
    Handling HTTP request errors
    """    
    def decorator(*args, **kwargs):
        self: Variables = args[0]
        try:
            result = func(*args, **kwargs)
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
            elif name == "FailedRequestError": # pybit
                logger.error(message)
                self.logNumFatal = 1001
            elif name == "InvalidRequestError": # pybit
                logger.error(message)
                self.logNumFatal = 1001
            else:
                raise exception
            
    return decorator

def ws_exception(text: str, logNumFatal):
    logger.error(text)
