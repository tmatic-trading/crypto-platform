from api.variables import Variables
from common.variables import Variables as var


class Setup(Variables):
    def variables(self) -> None:
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
            self.symbol_list = var.env[name]["SYMBOLS"]
            # self.currencies = var.env[name]["CURRENCIES"]
