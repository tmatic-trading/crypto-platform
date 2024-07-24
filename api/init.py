from api.variables import Variables
from common.variables import Variables as var


class Setup(Variables):
    def variables(self, name: str) -> None:
        if name in var.env:
            if var.env["TESTNET"] == "True":
                testnet = "TESTNET_"
            else:
                testnet = "TESTNET_"
                self.testnet = False
            self.api_key = var.env[name][testnet + "API_KEY"]
            self.api_secret = var.env[name][testnet + "API_SECRET"]
            self.ws_url = var.env[name][testnet + "WS_URL"]
            self.http_url = var.env[name][testnet + "HTTP_URL"]
            self.symbol_list = var.env[name]["SYMBOLS"]
            self.currencies = var.env[name]["CURRENCIES"]
            # d tmp_pos = {y: 0 for y in var.name_position}
            # d for symbol in self.symbol_list:
            # d    self.positions[symbol] = {"POS": 0}
            # d self.positions[symbol] = tmp_pos.copy()
            # d self.positions[symbol]["SYMB"] = symbol
            # d self.positions[symbol]["POS"] = 0
            # d self.positions[symbol]["SYMBOL"] = symbol[0]
            # d self.positions[symbol]["CAT"] = "None"
