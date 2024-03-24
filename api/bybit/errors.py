import logging
import requests
from api.variables import Variables

def exceptions_manager(func):
    """
    Handling HTTP request errors
    """
    logger = logging.getLogger(__name__)
    def decorator(*args, **kwargs):
        self: Variables = args[0]
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            if type(e) == requests.exceptions.ConnectionError:
                logger.error(e)
                self.logNumFatal = 1001
            else:
                raise e
            
    return decorator