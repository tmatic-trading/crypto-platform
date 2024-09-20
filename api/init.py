from urllib.parse import urlparse

import services as service
from api.errors import Error, HostNameIsInvalid
from api.variables import Variables
from common.variables import Variables as var


def URI_validator(uri: str):
    """
    Checks if a URI is valid.
    """
    try:
        result = urlparse(uri)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False


class Setup(Variables):
    def variables(self) -> None:
        """
        Configures variables related to the API for a specific exchange.
        """
        name = self.name
        if name in var.env:
            if var.env[name]["TESTNET"] == "YES":
                testnet = "TESTNET_"
            else:
                testnet = ""
                self.testnet = False
            self.api_key = var.env[name][testnet + "API_KEY"]
            self.api_secret = var.env[name][testnet + "API_SECRET"]
            self.ws_url = var.env[name][testnet + "WS_URL"]
            self.http_url = var.env[name][testnet + "HTTP_URL"]
            self.symbol_list = var.env[name]["SYMBOLS"].copy()
            if not URI_validator(self.ws_url):
                exception = HostNameIsInvalid(uri=self.ws_url)
                Error.handler(self, exception=exception, verb="Host name check")
                service.cancel_market(market=self.name)
            if not URI_validator(self.http_url):
                exception = HostNameIsInvalid(uri=self.http_url)
                Error.handler(self, exception=exception, verb="Host name check")
                service.cancel_market(market=self.name)
