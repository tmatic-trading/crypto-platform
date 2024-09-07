from api.errors import Error
from api.variables import Variables


class Unify(Variables):
    def error_handler(self, exception, verb: str, path: str) -> str:
        """
        Unifies response parameters with the Error.handler method.
        """
        parameters = exception.__dict__
        if parameters:
            response = {
                "error": {
                    "message": parameters["message"],
                    "code": parameters["status_code"],
                }
            }
        else:
            response = None

        status = Error.handler(
            self, exception=exception, response=response, verb=verb, path=path
        )
        if status == "RETRY":
            status = "FATAL"
            self.logNumFatal = status

        return status
