import json
import os
import threading
import time
from collections import OrderedDict

import requests
import websocket

import services as service
from api.init import Setup
from api.variables import Variables
from common.data import MetaAccount, MetaInstrument, MetaResult
from common.variables import Variables as var
from services import exceptions_manager


class Deribit(Variables):
    class Account(metaclass=MetaAccount):
        pass

    class Instrument(metaclass=MetaInstrument):
        pass

    class Result(metaclass=MetaResult):
        pass

    def __init__(self):
        self.name = "Deribit"
        self.api_version = "/api/v2/"
        Setup.variables(self, self.name)
        self.session = requests.Session()
        self.symbol_category = dict()
        self.define_category = {
            "future linear": "future L",
            "future reversed": "future R",
            "future_combo reversed": "future CR",
            "spot linear": "spot L",
            "option linear": "option L",
            "option reversed": "option R",
            "option_combo reversed": "option CR",
        }
        self.settleCoin_list = list()
        self.ws = websocket
        self.logger = var.logger
        if self.depth == "quote":
            self.orderbook_depth = 1
        else:
            self.orderbook_depth = 50
        self.robots = OrderedDict()
        self.frames = dict()
        self.robot_status = dict()
        self.setup_orders = list()
        self.account_disp = ""
        self.orders = dict()
        self.access_token = ""

    def start(self):
        for symbol in self.symbol_list:
            instrument = self.Instrument[symbol]
            if "linear" in instrument.category:
                self.Result[(instrument.quoteCoin, self.name)]
            elif "reversed" in instrument.category:
                self.Result[(instrument.baseCoin, self.name)]
            elif "spot" in instrument.category:
                self.Result[(instrument.baseCoin, self.name)]
                self.Result[(instrument.quoteCoin, self.name)]
            elif "option" in instrument.category:
                self.Result[(instrument.baseCoin, self.name)]
        self.__connect()

    def __connect(self) -> None:
        """
        Connecting to websocket.
        """
        self.logger.info("Connecting to websocket")
        self.ws = websocket.WebSocketApp(
            self.ws_url + self.api_version,
            on_message=self.__on_message,
            on_error=self.__on_error,
            on_close=self.__on_close,
            on_open=self.__on_open,
        )
        newth = threading.Thread(target=lambda: self.ws.run_forever())
        newth.daemon = True
        newth.start()
        while not self.access_token:
            time.sleep(0.05)
        print("______________________ access_token received", self.access_token)
        os.abort()

    def __on_message(self, ws, message):
        message = json.loads(message)
        print(message)
        if "result" in message:
            if "access_token" in message["result"]:
                self.access_token = message["result"]["access_token"]
                self.refresh_token = message["result"]["refresh_token"]
        """if "id" in message:
            self.response[message["id"]] = message["result"]"""

    def __on_error(self, ws, error):
        print(error)

    def __on_close(self, ws):
        print("close")

    def __ws_auth(self) -> None:
        """
        Requests DBT's `public/auth` to
        authenticate the WebSocket Connection.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": 9929,
            "method": "public/auth",
            "params": {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
            },
        }
        self.ws.send(json.dumps(msg))

    def __on_open(self, ws):
        self.__ws_auth()

    def __subscribe_public():
        pass

    def __subscribe_private():
        pass

    def exit(self):
        """
        Closes websocket
        """
        try:
            self.ws.close()
        except Exception:
            pass
        self.logNumFatal = -1
