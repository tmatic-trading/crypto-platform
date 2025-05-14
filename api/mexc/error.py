from enum import Enum


class ErrorStatus(Enum):
    RETRY = {}
    FATAL = {}
    BLOCK = {}
    IGNORE = {}
    CANCEL = {}

    def status(error):
        error_number = error["error"]["code"]
        for status in ErrorStatus:
            if error_number in status.value:
                return status.name
