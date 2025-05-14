import json
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone

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
        self.session = requests.Session()  # Https requests.
        self.timefrs: OrderedDict  # Define the default time frames
        # set by the exchange.
        self.ws = websocket  # Websocket object.
        self.logger = var.logger  # Writes to logfile.log.
        self.klines = dict()  # Kline (candlestick) data.
        self.setup_orders = list()  # Open orders when loading.
        self.account_disp = ""  # Exchange name and account number in
        # the Instrument menu.
        self.pinging: str  # Used to monitor the connection using ping.
        self.ticker = dict()  # Brings the classification of tickers
        # to a single standard, for example ETH_USDT (Deribit API) ->
        # ETH/USDT (Tmatic standard).
        self.instrument_index = OrderedDict()  # Used in the Instrument
        # menu to classify instruments into categories and currencies.
        self.api_auth = API_auth  # Generates api key headers and signature.
        self.get_error = ErrorStatus  # Error codes.
        self.subscriptions = dict()

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
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )
        newth = threading.Thread(target=lambda: self.ws.run_forever())
        newth.daemon = True
        newth.start()

        while (not self.ws.sock or not self.ws.sock.connected) and time_out >= 0:
            time.sleep(slp)
            time_out -= slp
        if time_out <= 0:
            self.logger.error("Couldn't connect to websocket!")
            return service.unexpected_error(self)
        self.logger.info("Connected to websocket.")
        if self._ws_auth() == "error":
            return service.unexpected_error(self)
        
        return ""

    def _on_message(self, ws, message):
        message = json.loads(message)
        print("__________on_message", message, type(message))
        if message["channel"] in self.subscriptions:
            self.subscriptions[message["channel"]] = message["data"]

    def _on_error(self, ws, error):
        """
        We are here if websocket has fatal errors.
        """
        self.logger.error(type(error).__name__ + " " + str(error))
        service.unexpected_error(self)

    def _on_close(self, *args):
        self.logger.info("Websocket closed.")
        service.unexpected_error(self)

    def _on_open(self, ws):
        pass

    def _ws_auth(self):
        tstamp = str(int(time.time() * 1000))
        signature = API_auth.generate_signature(
            api_key=self.api_key,
            secret=self.api_secret,
            tstamp=tstamp,
        )
        self.subscriptions["rs.login"] = "Pending"
        self.ws.send(
            json.dumps(
                {
                    "subscribe": True,
                    "method": "login",
                    "param": {
                        "apiKey": self.api_key,
                        "reqTime": tstamp,
                        "signature": signature,
                    },
                }
            )
        )
        time_out, slp = 5, 0.1
        while time_out >= 0:
            time.sleep(slp)
            time_out -= slp
            if self.subscriptions["rs.login"] == "success":
                del self.subscriptions["rs.login"]
                self.logger.info("WebSocket authentication successful.")
                return
            elif self.subscriptions["rs.login"] != "Pending":
                message = (
                    "WebSocket authentication error. " + self.subscriptions["rs.login"]
                )
                del self.subscriptions["rs.login"]
                self._put_message(message=message)
                return "error"

        message = "WebSocket authentication timed out."
        self._put_message(message=message)

        return "error"


    def exit(self):
        """
        Closes websocket
        """
        try:
            self.ws.close()
        except Exception:
            pass
        self.api_is_active = False

    def setup_streams(self) -> str:
        for symbol in self.symbol_list:
            instrument = self.Instrument[symbol]
            if "linear" in instrument.category:
                self.Result[(instrument.quoteCoin, self.name)]
            elif "inverse" in instrument.category:
                self.Result[(instrument.baseCoin, self.name)]
        if not self.logNumFatal:
            self._subscribe()
            # res = self._confirm_subscription()
            # if not res:
            #     self.logger.info("All subscriptions are successful. Continuing.")
        else:
            return self.logNumFatal

    def _subscribe(self):
        self.subscriptions = list()
        params = {"method": "sub.ticker", "param": {"symbol": "BTC_USDT"}}
        params = {"method": "ping"}
        self.ws.send(json.dumps(params))
        print("____________________________subs")

        # try:
        #     if not self.logNumFatal:
        #         # Subscribes symbol by symbol to all tables given
        #         for symbol in self.symbol_list:
        #             subscriptions = []
        #             for sub in self.table_subscription:
        #                 subscriptions += [sub + ":" + self.Instrument[symbol].ticker]
        #             self.logger.info("ws subscribe - " + str(subscriptions))
        #             self.ws.send(json.dumps({"op": "subscribe", "args": subscriptions}))
        # except Exception as exception:
        #     display_exception(exception)
        #     message = "Exception while connecting to websocket."
        #     if not self.logNumFatal:
        #         message += " Reboot."
        #         service.unexpected_error(self)
        #     self.logger.error(message)
        #     return self.logNumFatal
        # if not self.logNumFatal:
        #     self.__wait_for_tables(self.symbol_list)
        #     if not self.logNumFatal:
        #         self.logger.info("Data received. Continuing.")
        #         self.pinging = "pong"

        return ""

    def _put_message(self, message: str, warning=None, info=True) -> None:
        """
        Places an information message into the queue and the logger.
        """
        if info:
            var.queue_info.put(
                {
                    "market": self.name,
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": warning,
                }
            )
        if not warning:
            self.logger.info(self.name + " - " + message)
        elif warning == "warning":
            self.logger.warning(self.name + " - " + message)
        else:
            self.logger.error(self.name + " - " + message)
