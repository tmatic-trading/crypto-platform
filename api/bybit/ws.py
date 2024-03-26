from api.variables import Variables
from api.init import Setup
import logging

#from .agent import Agent
from .pybit.unified_trading import HTTP
from .pybit.unified_trading import WebSocket
from time import sleep
from api.bybit.errors import ws_exception
import logging


class Bybit(Variables):
    def __init__(self):
        self.name = "Bybit"
        Setup.variables(self, self.name)
        self.session = HTTP(
        api_key=self.api_key,
        api_secret=self.api_secret,
        testnet=self.testnet,
        )
        self.categories = ["spot", "inverse", "option", "linear"]
        self.ws = {"spot": WebSocket, "inverse": WebSocket, "option": WebSocket, "linear": WebSocket}
        self.logger = logging.getLogger(__name__)
        print("!!!!!!!!!!!!! BYBIT !!!!!!!!!!!")

    def start(self):
        print("-----starting Bybit----")
        self.count = 0

        #self.instruments = self.agent.get_active_instruments(self)
        print(self.categories)
        #self.__connect()

    def __connect(self) -> None:
        """
        Connects to websocket.
        """
        self.logger.info("Connecting to websocket")
        
        for category in self.category_list:
            try:
                self.ws[category] = WebSocket(testnet=self.testnet, channel_type=category)
            except Exception as e:
                self.logNumFatal = 2002
                ws_exception(text=e.args[0], logNumFatal=self.logNumFatal)
    
    def exit(self):
        """
        Closes websocket
        """
        for category in self.category_list:
            try:
                self.ws[category].exit()
            except Exception:
                pass
        self.logger.info("Websocket closed")



    #del
    '''def get_active_instruments(self, symbol: tuple):
        return self.agent.get_active_instruments(self, symbol=symbol)'''
