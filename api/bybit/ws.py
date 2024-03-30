from api.variables import Variables
from api.init import Setup
import logging
from collections import OrderedDict

#from .agent import Agent
from .pybit.unified_trading import HTTP
from .pybit.unified_trading import WebSocket
from time import sleep
import logging
from services import exceptions_manager


@exceptions_manager
class Bybit(Variables):
    def __init__(self):
        self.name = "Bybit"
        Setup.variables(self, self.name)
        self.session = HTTP(
        api_key=self.api_key,
        api_secret=self.api_secret,
        testnet=self.testnet,
        )
        self.settlCurrency_list = list()
        self.settleCoin_list = list()
        self.ws = {"spot": WebSocket, "inverse": WebSocket, "option": WebSocket, "linear": WebSocket}
        self.ws_private = WebSocket
        self.logger = logging.getLogger(__name__)
        if self.depth == "quote":
            self.orderbook_depth = 1
        else:
            self.orderbook_depth = 50
        print("!!!!!!!!!!!!! BYBIT !!!!!!!!!!!")

    def start(self):
        print("-----starting Bybit----")
        self.count = 0
        self.data[self.depth] = OrderedDict()
        self.data["margin"] = OrderedDict()
        self.__connect()


    def __connect(self) -> None:
        """
        Connecting to websocket.
        """
        self.logger.info("Connecting to websocket")        
        for category in self.category_list:
            self.ws[category] = WebSocket(testnet=self.testnet, channel_type=category)
            for symbol in self.symbol_list:
                self.ws[category].orderbook_stream(
                    depth=self.orderbook_depth,
                    symbol=symbol[0],
                    callback=lambda x: self.__handle_orderbook(message=x, category=category)
                )
                self.data[self.depth][symbol] = dict()
                self.data[self.depth][symbol]["symbol"] = symbol[0]
                self.data[self.depth][symbol]["bids"] = list()
                self.data[self.depth][symbol]["asks"] = list()
        self.ws_private = WebSocket(testnet=self.testnet, channel_type="private", api_key=self.api_key, api_secret=self.api_secret,)
        self.ws_private.wallet_stream(callback=self.__handle_wallet)

    def __handle_orderbook(self, message: dict, category: str):
        symbol = (message["topic"].split(".")[-1], category)
        if self.depth == "quote":
            self.data[self.depth]["bidPrice"] = message["data"]["b"][0]
            self.data[self.depth]["askPrice"] = message["data"]["a"][0]
            self.data[self.depth]["bidSize"] = message["data"]["b"][1]
            self.data[self.depth]["askSize"] = message["data"]["a"][1]
        else:
            self.data[self.depth][symbol]["bids"] = message["data"]["b"]
            self.data[self.depth][symbol]["asks"] = message["data"]["a"]

    def __handle_wallet(message):
        print(message)

    def __handle_order(self, message):
        pass

    
    def exit(self):
        """
        Closes websocket
        """
        for category in self.category_list:
            try:
                self.ws[category].exit()
            except Exception:
                pass
        try:
            self.ws_private.exit()
        except Exception:
            pass
        self.logger.info("Websocket closed")

    def transaction(self, **kwargs):
        """
        This method is replaced by transaction() from functions.py after the
        application is launched.
        """
        pass



    #del
    '''def get_active_instruments(self, symbol: tuple):
        return self.agent.get_active_instruments(self, symbol=symbol)'''
