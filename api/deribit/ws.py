import json
import threading
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

    def start(self):
        """for symbol in self.symbol_list:
        instrument = self.Instrument[symbol]
        if instrument.category == "linear":
            self.Result[(instrument.quoteCoin, self.name)]
        elif instrument.category == "inverse":
            self.Result[(instrument.baseCoin, self.name)]
        elif instrument.category == "spot":
            self.Result[(instrument.baseCoin, self.name)]
            self.Result[(instrument.quoteCoin, self.name)]"""

        self.__connect()

    def __connect(self) -> None:
        """
        Connecting to websocket.
        """
        self.logger.info("Connecting to websocket")

    def exit(self):
        """
        Closes websocket
        """
        try:
            self.ws.close()
        except Exception:
            pass
        self.logNumFatal = -1
