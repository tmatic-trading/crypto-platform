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
        self.response = dict()
        self.subscriptions = set()
        self.callback_directory = dict()
        self.depth_sub = "sub.depth.full"
        self.depth_push = "push.depth.full"

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
        # print("__________on_message", message["channel"], message)
        if message["channel"] == "push.ticker":
            self.callback_directory["push.ticker"](values=message["data"])
        elif message["channel"] == self.depth_push:
            self.callback_directory[self.depth_push](values=message)
        elif message["channel"] in self.response:
            self.response[message["channel"]] = message["data"]

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
        self.response["rs.login"] = "Pending"
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
            if self.response["rs.login"] == "success":
                del self.response["rs.login"]
                self.logger.info("WebSocket authentication successful.")
                return
            elif self.response["rs.login"] != "Pending":
                message = "WebSocket authentication error. " + self.response["rs.login"]
                del self.response["rs.login"]
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
        self._subscribe_symbols()

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

    def _subscribe_symbols(self) -> None:
        """
        Orderbook and ticker subscription. Called at boot or reboot time.
        """
        for symbol in self.symbol_list:
            # Ticker

            instrument = self.Instrument[symbol]
            params = {"method": "sub.ticker", "param": {"symbol": instrument.ticker}}
            self.ws.send(json.dumps(params))
            channel = "push.ticker"
            self.subscriptions.add((channel, instrument.ticker))
            self.callback_directory[channel] = self._update_ticker
            message = Message.WEBSOCKET_SUBSCRIPTION.format(
                NAME="Ticker", CHANNEL=instrument.ticker
            )
            self._put_message(message=message)

            # Orderbook

            params = {"method": self.depth_sub, "param": {"symbol": instrument.ticker}}
            if self.depth_sub == "sub.depth.full":
                params["param"]["limit"] = 10
            self.ws.send(json.dumps(params))
            channel = self.depth_push
            self.subscriptions.add((channel, instrument.ticker))
            self.callback_directory[channel] = self._update_orderbook
            message = Message.WEBSOCKET_SUBSCRIPTION.format(
                NAME="Orderbook", CHANNEL=instrument.ticker
            )
            self._put_message(message=message)
        # channels = list()
        # for symbol in symbol_list:
        #     instrument = self.Instrument[symbol]
        #     ticker = instrument.ticker
        #     if ticker != "option!":
        #         channel = f"ticker.{ticker}.100ms"
        #         channels.append(channel)
        #     else:
        #         lst = service.select_option_strikes(
        #             index=self.instrument_index, instrument=instrument
        #         )
        #         for option in lst:
        #             channel = f"ticker.{option}.100ms"
        #             channels.append(channel)
        # message = Message.WEBSOCKET_SUBSCRIPTION.format(
        #     NAME="Ticker", CHANNEL=str(channels)
        # )
        # self._put_message(message=message)
        # self.__subscribe_channels(
        #     type="public",
        #     channels=channels,
        #     id="subscription",
        #     callback=self.__update_ticker,
        # )

    def _update_ticker(self, values: dict) -> None:
        print("_____________callback ticker", values)
        symbol = (self.ticker[values["symbol"]], self.name)
        instrument = self.Instrument[symbol]
        instrument.volume24h = values["volume24"]
        instrument.fundingRate = values["fundingRate"] * 100
        # instrument.openInterest
        instrument.bidPrice = values["bid1"]
        instrument.askPrice = values["ask1"]
        # instrument.bidSize
        # instrument.askSize
        # instrument.markPrice
        # instrument.state

    def _update_orderbook(self, values: dict) -> None:
        symbol = (self.ticker[values["symbol"]], self.name)
        instrument = self.Instrument[symbol]
        instrument.asks = list(
            map(
                lambda x: [
                    x[0],
                    round(x[1] * instrument.qtyStep, instrument.precision),
                ],
                values["data"]["asks"],
            )
        )
        instrument.bids = list(
            map(
                lambda x: [
                    x[0],
                    round(x[1] * instrument.qtyStep, instrument.precision),
                ],
                values["data"]["bids"],
            )
        )
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
