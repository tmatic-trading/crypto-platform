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
from datetime import datetime
from common.data import MetaPosition, MetaInstrument


@exceptions_manager
class Bybit(Variables):
    class Position(metaclass=MetaPosition): pass
    class Instrument(metaclass=MetaInstrument): pass
    def __init__(self):
        self.name = "Bybit"
        Setup.variables(self, self.name)
        self.session = HTTP(
        api_key=self.api_key,
        api_secret=self.api_secret,
        testnet=self.testnet,
        )
        self.categories = ["spot", "inverse", "option", "linear"]
        self.settlCurrency_list = {"spot": [], "inverse": [], "option": [], "linear": []}
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
                    callback=lambda x: self.__handle_orderbook(message=x, symbol=symbol)
                )
                self.data[self.depth][symbol] = dict()
                self.data[self.depth][symbol]["symbol"] = symbol[0]
                self.data[self.depth][symbol]["bids"] = list()
                self.data[self.depth][symbol]["asks"] = list()
                self.ws[category].ticker_stream(
                    symbol=symbol[0],
                    callback=lambda x: self.__handle_ticker(message=x, category=category)
                )
        self.ws_private = WebSocket(testnet=self.testnet, channel_type="private", api_key=self.api_key, api_secret=self.api_secret,)
        self.ws_private.wallet_stream(callback=self.__handle_wallet)

    def __handle_orderbook(self, message: dict, symbol: tuple):
        if self.depth == "quote":
            self.data[self.depth][symbol]["bidPrice"] = message["data"]["b"][0]
            self.data[self.depth][symbol]["askPrice"] = message["data"]["a"][0]
            self.data[self.depth][symbol]["bidSize"] = message["data"]["b"][1]
            self.data[self.depth][symbol]["askSize"] = message["data"]["a"][1]
        else:
            asks = message["data"]["a"]
            bids = message["data"]["b"]
            asks = list(map(lambda x: [float(x[0]), float(x[1])], asks))
            bids = list(map(lambda x: [float(x[0]), float(x[1])], bids))
            asks.sort(key=lambda x: x[0])       
            bids.sort(key=lambda x: x[0], reverse=True)            
            self.data[self.depth][symbol]["bids"] = bids
            self.data[self.depth][symbol]["asks"] = asks

    def __handle_ticker(self, message: dict, category: str):
        self.message_counter += 1
        pass
        #print(category, message)

    def __handle_wallet(message):
        pass

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
