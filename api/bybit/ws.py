from api.variables import Variables
from api.init import Setup
import logging

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
        self.ws_category = {"spot": WebSocket, "inverse": WebSocket, "option": WebSocket, "linear": WebSocket}
        self.ws_settleCoin: WebSocket = dict()
        self.ws = WebSocket
        self.logger = logging.getLogger(__name__)
        print("!!!!!!!!!!!!! BYBIT !!!!!!!!!!!")

    def start(self):
        print("-----starting Bybit----")
        self.count = 0

        #self.instruments = self.agent.get_active_instruments(self)
        self.__connect()

    def __connect(self) -> None:
        """
        Connecting to websocket.
        """
        self.logger.info("Connecting to websocket")        
        for category in self.category_list:
            self.ws_category[category] = WebSocket(testnet=self.testnet, channel_type=category)

    def __handle_order(self, message):

        print(message)

    
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

    def transaction(self, **kwargs):
        """
        This method is replaced by transaction() from functions.py after the
        application is launched.
        """
        pass



    #del
    '''def get_active_instruments(self, symbol: tuple):
        return self.agent.get_active_instruments(self, symbol=symbol)'''
