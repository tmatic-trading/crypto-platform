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
        pass