from datetime import datetime

from api.variables import Variables
from common.variables import Variables as var


class Setup(Variables):
    def variables(self, name: str) -> None:
        if name in var.env:
            tm = datetime.utcnow()
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
            self.full_symbol_list = self.symbol_list.copy()
            tmp_pos = {y: 0 for y in var.name_position}
            self.category_list = list()
            for symbol in self.symbol_list:
                if symbol[1] not in self.category_list:
                    self.category_list.append(symbol[1])
            for symbol in self.symbol_list:
                self.positions[symbol] = tmp_pos.copy()
                self.positions[symbol]["SYMB"] = symbol
                self.positions[symbol]["SYMBOL"] = symbol[0]
                self.positions[symbol]["CAT"] = symbol[1]
