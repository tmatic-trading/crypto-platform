from datetime import datetime

from api.variables import Variables
from common.variables import Variables as var
import requests


class Setup(Variables):
    def variables(self) -> None:
        tm = datetime.utcnow()
        if var.env["TESTNET"] == "True":
            testnet = "TESTNET_"
        else:
            testnet = "TESTNET_"
            self.testnet = False
        self.api_key = var.env[self.name][testnet + "API_KEY"]
        self.api_secret = var.env[self.name][testnet + "API_SECRET"]
        self.ws_url = var.env[self.name][testnet + "WS_URL"]
        self.http_url = var.env[self.name][testnet + "HTTP_URL"]
        self.symbol_list = var.env[self.name]["SYMBOLS"]
        self.currencies = var.env[self.name]["CURRENCIES"]
        self.full_symbol_list = self.symbol_list.copy()        
        tmp_pos = {y: 0 for y in var.name_pos}
        #tmp_instr = {y: 0 for y in var.name_instruments}
        for symbol in self.symbol_list:
            self.ticker[symbol] = {
                "bid": 0,
                "ask": 0,
                "bidSize": 0,
                "askSize": 0,
                "open_bid": 0,
                "open_ask": 0,
                "hi": 0,
                "lo": 0,
                "time": tm,
            }
            self.positions[symbol] = tmp_pos.copy()
            #self.instruments[symbol] = tmp_instr.copy()
        for cur in self.currencies:
            self.accounts[cur] = {y: 0 for y in var.name_acc}
            self.accounts[cur]["SUMREAL"] = 0

