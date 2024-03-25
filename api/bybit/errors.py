import logging
import requests
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
            if func.__name__ != "exit":
                self.logNumFatal = 0
            return result
        except Exception as e:
            if type(e) == requests.exceptions.ConnectionError:
                logger.error(e)
                self.logNumFatal = 1001
            else:
                raise e
            
    return decorator

def ws_exception(text: str, logNumFatal):
    logger.error(text)
