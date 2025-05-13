import threading
from collections import OrderedDict

import requests
import websocket

import services as service
from api.errors import Error
from api.init import Setup
from api.variables import Variables
from common.data import MetaAccount, MetaInstrument, MetaResult
from common.variables import Variables as var
from display.messages import Message
from services import display_exception

from .api_auth import API_auth
from .error import ErrorStatus


class Mexc(Variables):
    class Account(metaclass=MetaAccount):
        pass

    class Instrument(metaclass=MetaInstrument):
        pass

    class Result(metaclass=MetaResult):
        pass

    def __init__(self):
        self.object = Mexc
        self.name = "Mexc"
        Setup.variables(self)
        self.session = requests.Session() # Https requests.
        self.timefrs: OrderedDict # Define the default time frames
        # set by the exchange.
        self.ws = websocket # Websocket object.
        self.logger = var.logger # Writes to logfile.log.
        self.klines = dict() # Kline (candlestick) data.
        self.setup_orders = list() # Open orders when loading.
        self.account_disp = "" # Exchange name and account number in
        # the Instrument menu.
        self.pinging: str # Used to monitor the connection using ping.
        self.ticker = dict() # Brings the classification of tickers
        # to a single standard, for example ETH_USDT (Deribit API) ->
        # ETH/USDT (Tmatic standard).
        self.instrument_index = OrderedDict() # Used in the Instrument
        # menu to classify instruments into categories and currencies.
        self.api_auth = API_auth # Generates api key headers and signature.
        self.get_error = ErrorStatus # Error codes.

    def setup_session(self):
        """
        Not used in Mexc.
        """
        pass

    def start_ws(self):
        time_out, slp = 5, 0.1
        websocket.setdefaulttimeout(time_out)
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.__on_message,
            on_error=self.__on_error,
            on_close=self.__on_close,
            on_open=self.__on_open,
        )
        newth = threading.Thread(target=lambda: self.ws.run_forever())
        newth.daemon = True
        newth.start()

    def __on_message(self, ws, message):
        pass

    def __on_error(self, ws, error):
        """
        We are here if websocket has fatal errors.
        """
        # self.logger.error(type(error).__name__ + " " + str(error))
        # service.unexpected_error(self)

    def __on_close(self, *args):
        self.logger.info("Websocket closed.")
        service.unexpected_error(self)

    def __on_open(self, ws):
        pass
        # self.__ws_auth()

    def exit(self):
        """
        Closes websocket
        """
        try:
            self.ws.close()
        except Exception:
            pass
        self.api_is_active = False