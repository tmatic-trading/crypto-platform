import json
import threading
import time
import traceback
from collections import OrderedDict
from time import sleep

import requests
import websocket

import services as service
from api.init import Setup
from api.variables import Variables
from common.data import MetaAccount, MetaInstrument, MetaResult
from common.variables import Variables as var
from services import display_exception

from .api_auth import API_auth


class Bitmex(Variables):
    class Account(metaclass=MetaAccount):
        pass

    class Instrument(metaclass=MetaInstrument):
        pass

    class Result(metaclass=MetaResult):
        pass

    def __init__(self):
        self.name = "Bitmex"
        self.data = dict()
        self.Api_auth = API_auth
        Setup.variables(self, self.name)
        self.session = requests.Session()
        depth = "quote"
        if self.depth != "quote":
            depth = "orderBook10"
        self.session.headers.update({"user-agent": "Tmatic"})
        self.session.headers.update({"content-type": "application/json"})
        self.session.headers.update({"accept": "application/json"})
        self.table_subscription = {
            "margin",
            "execution",
            "instrument",
            "position",
            depth,
            # "order",
            # "trade",
        }
        self.currency_divisor = {
            "XBt": 100000000,
            "USDt": 1000000,
            "BMEx": 1000000,
            "MATIc": 1000000,
        }  # MATIc is probably incorrect
        self.timefrs = {1: "1m", 5: "5m", 60: "1h"}
        self.logger = var.logger
        self.klines = dict()
        self.robot_status = dict()
        self.setup_orders = list()
        self.account_disp = ""
        self.pinging = "pong"
        self.ticker = dict()
        self.kline_set = set()

    def start(self):
        if not self.logNumFatal:
            for symbol in self.symbol_list:
                instrument = self.Instrument[symbol]
                if instrument.settlCurrency:
                    self.Result[(instrument.settlCurrency[0], self.name)]
            self.__reset()
            self.__connect(self.__get_url())
            if not self.logNumFatal:
                self.logger.info("Connected to websocket.")
                self.__wait_for_tables()
                if not self.logNumFatal:
                    self.logger.info("Data received. Continuing.")
                    self.pinging = "pong"

    def __connect(self, url: str) -> None:
        try:
            """
            Connects to websocket in a thread.
            """
            self.logger.info("Connecting to websocket")
            self.logger.debug("Starting a new thread")
            self.ws = websocket.WebSocketApp(
                url,
                on_open=self.__on_open,
                on_close=self.__on_close,
                header=self.__get_auth(),
                on_message=self.__on_message,
                on_error=self.__on_error,
            )
            newth = threading.Thread(target=lambda: self.ws.run_forever())
            newth.daemon = True
            newth.start()
            self.logger.debug("Thread started")
            # Waits for connection established
            time_out = 5
            while (not self.ws.sock or not self.ws.sock.connected) and time_out >= 0:
                sleep(0.1)
                time_out -= 0.1
            if time_out <= 0:
                self.logger.error("Couldn't connect to websocket!")
                self.logNumFatal = "SETUP"
            else:
                # Subscribes symbol by symbol to all tables given
                for symbol in self.symbol_list:
                    subscriptions = []
                    for sub in self.table_subscription:
                        subscriptions += [sub + ":" + self.Instrument[symbol].ticker]
                    self.logger.info("ws subscribe - " + str(subscriptions))
                    self.ws.send(json.dumps({"op": "subscribe", "args": subscriptions}))
        except Exception as exception:
            display_exception(exception)
            self.logger.error("Exception while connecting to websocket. Restarting...")
            self.logNumFatal = "SETUP"

    def subscribe_symbol(self, symbol: tuple) -> None:
        subscriptions = []
        for sub in self.table_subscription:
            subscriptions += [sub + ":" + self.Instrument[symbol].ticker]
        self.logger.info("ws subscribe - " + str(subscriptions))
        self.ws.send(json.dumps({"op": "subscribe", "args": subscriptions}))
        self.__wait_for_tables()  # subscription confirmation

    def unsubscribe_symbol(self, symbol: str) -> None:
        subscriptions = []
        for sub in self.table_subscription:
            subscriptions += [sub + ":" + symbol]
        self.logger.info("ws unsubscribe - " + subscriptions)
        self.ws.send(json.dumps({"op": "unsubscribe", "args": subscriptions}))
        self.__wait_for_tables()  # unsubscription confirmation

    def __get_url(self) -> str:
        """
        Prepares URL before subscribing.
        """

        return self.ws_url + "?subscribe=margin"

    def __get_auth(self) -> list:
        """
        Authenticates with API key.
        """
        try:
            if self.api_key:
                self.logger.info("Authenticating with API key.")
                nonce = int(round(time.time() * 1000))
                return [
                    "api-nonce: " + str(nonce),
                    "api-signature: "
                    + API_auth.generate_signature(
                        self.api_secret, "GET", "/realtime", nonce, ""
                    ),
                    "api-key:" + self.api_key,
                ]
            else:
                self.logger.info("No authentication with API key.")
                return []
        except Exception:
            self.logger.error("Exception while authenticating. Restarting...")
            self.logNumFatal = "SETUP"
            return []

    def __wait_for_tables(self) -> None:
        """
        Waiting for data to be loaded from the websocket. If not all data is
        received after the timeout expires, the websocket is rebooted.
        """
        count = 0
        while not self.table_subscription <= set(self.keys):
            count += 1
            if count > 30:  # fails after 3 seconds
                table_lack = self.table_subscription.copy()
                for table in self.keys.keys():
                    if table in self.table_subscription:
                        table_lack.remove(table)
                self.logger.info(
                    "Timeout expired. Not all tables has been loaded. "
                    + str(table_lack)
                    + " - missing."
                )
                self.logNumFatal = "SETUP"
                return
            sleep(0.1)
        count = 0
        while len(self.data["instrument"]) != len(self.symbol_list):
            count += 1
            if count > 30:  # fails after 3 seconds
                instr_lack = self.symbol_list.copy()
                for instrument in self.data["instrument"].values():
                    if instrument["symbol"] in self.symbol_list:
                        instr_lack.remove(instrument["symbol"])
                self.logger.info(
                    "Timeout expired. Not all instruments has been loaded. "
                    + str(instr_lack)
                    + " - missing in the instrument table."
                )
                self.logNumFatal = "SETUP"
                return
            sleep(0.1)

    def __on_message(self, ws, message) -> None:
        """
        Parses websocket messages.
        """
        if message == "pong":
            self.pinging = "pong"
            return

        def generate_key(keys: list, val: dict) -> tuple:
            val["market"] = self.name
            return tuple((val[key]) for key in keys)

        message = json.loads(message)
        action = message["action"] if "action" in message else None
        table = message["table"] if "table" in message else None
        try:
            if action:
                table_name = "orderBook" if table == "orderBook10" else table
                if table_name not in self.data:
                    self.data[table_name] = OrderedDict()
                if action == "partial":  # table snapshot
                    self.keys[table] = message["keys"]
                    if table == "quote":
                        self.keys[table] = ["symbol", "market"]
                    elif table == "trade":
                        self.keys[table] = ["trdMatchID"]
                    elif table == "execution":
                        self.keys[table] = ["execID"]
                    elif table == "margin":
                        self.keys[table] = ["currency", "market"]
                    elif table in ["instrument", "orderBook10", "position"]:
                        self.keys[table].append("market")

                    for val in message["data"]:
                        for key in self.keys[table]:
                            if key not in ["market"]:
                                if key not in val:
                                    break
                        else:
                            key = generate_key(self.keys[table], val)
                            self.data[table_name][key] = val
                            if table == "orderBook10":
                                self.__update_orderbook(symbol=key, values=val)
                            elif table == "quote":
                                self.__update_orderbook(
                                    symbol=key, values=val, quote=True
                                )
                            elif table == "margin":
                                self.__update_account(
                                    settlCurrency=key,
                                    values=val,
                                )
                elif action == "insert":
                    for val in message["data"]:
                        key = generate_key(self.keys[table], val=val)
                        if table == "quote":
                            self.__update_orderbook(symbol=key, values=val, quote=True)
                        elif table == "execution":
                            val["ticker"] = val["symbol"]
                            val["symbol"] = (
                                self.ticker[val["symbol"]],
                                self.name,
                            )
                            val["market"] = self.name
                            instrument = self.Instrument[val["symbol"]]
                            val["category"] = instrument.category
                            if instrument.category == "spot":
                                if val["side"] == "Buy":
                                    val["settlCurrency"] = (
                                        instrument.quoteCoin,
                                        self.name,
                                    )
                                else:
                                    val["settlCurrency"] = (
                                        instrument.baseCoin,
                                        self.name,
                                    )
                            else:
                                val["settlCurrency"] = (val["settlCurrency"], self.name)
                            val["transactTime"] = service.time_converter(
                                time=val["transactTime"], usec=True
                            )
                            if "lastQty" in val:
                                val["lastQty"] *= instrument.valueOfOneContract
                            if "leavesQty" in val:
                                val["leavesQty"] *= instrument.valueOfOneContract
                            if val["execType"] == "Funding":
                                if val["foreignNotional"] > 0:
                                    val["lastQty"] = -val["lastQty"]
                                    val["commission"] = -val["commission"]
                            elif val["execType"] == "Settlement":
                                val["execType"] = "Delivery"
                            val["execFee"] = None
                            if instrument.category != "spot":
                                self.transaction(row=val)
                            else:
                                message = (
                                    "Tmatic does not support spot trading on Bitmex. The execution entry with execID "
                                    + val["execID"]
                                    + " was ignored."
                                )
                                self.logger.warning(message)
                        else:
                            self.data[table_name][key] = val
                elif action == "update":
                    for val in message["data"]:
                        key = generate_key(self.keys[table], val=val)
                        if key not in self.data[table_name]:
                            return  # No key to update
                        if table == "orderBook10":
                            self.__update_orderbook(symbol=key, values=val)
                        elif table == "instrument":
                            self.__update_instrument(symbol=key, values=val)
                        elif table == "position":
                            self.__update_position(key, values=val)
                        elif table == "margin":
                            self.__update_account(settlCurrency=key, values=val)
                        elif table == "order":
                            self.data[table_name][key].update(val)
                            if self.data[table_name][key]["leavesQty"] <= 0:
                                # Removes cancelled or filled orders
                                self.data[table_name].pop(key)
                elif action == "delete":
                    for val in message["data"]:
                        key = generate_key(self.keys[table], val)
                        self.data[table_name].pop(key)
        except Exception:
            print("_____________keys", self.keys)
            self.logger.error(
                traceback.format_exc()
            )  # Error in api.py. Take a look in logfile.log. Restarting...
            self.logNumFatal = "SETUP"

    def __on_error(self, ws, error) -> None:
        """
        We are here if websocket has fatal errors.
        """
        self.logger.error("Error: %s" % error)
        self.logNumFatal = "SETUP"

    def __on_open(self, ws) -> None:
        self.logger.debug("Websocket opened")

    def __on_close(self, *args) -> None:
        self.logger.info(self.name + " - Websocket closed")
        self.logNumFatal = "SETUP"

    def __reset(self) -> None:
        """
        Resets internal data.
        """
        self.data = {}
        self.keys = {}

    def kline_hi_lo_values(self, symbol: tuple) -> None:
        if symbol in self.klines:
            for timeframe in self.klines[symbol].values():
                if timeframe["data"]:
                    instrument = self.Instrument[symbol]
                    ask = instrument.asks[0][0]
                    bid = instrument.bids[0][0]
                    if ask > timeframe["data"][-1]["hi"]:
                        timeframe["data"][-1]["hi"] = ask
                    if bid < timeframe["data"][-1]["lo"]:
                        timeframe["data"][-1]["lo"] = bid

    def __update_orderbook(self, symbol: tuple, values: dict, quote=False) -> None:
        """
        There is only one Instrument array for the "instrument", "position",
        "quote", "orderBook10" websocket streams.
        """
        symbol = (self.ticker[symbol[0]], self.name)
        instrument = self.Instrument[symbol]
        if quote:
            if "askPrice" in values:
                instrument.asks = [
                    [
                        values["askPrice"],
                        values["askSize"] * instrument.valueOfOneContract,
                    ]
                ]
            if "bidPrice" in values:
                instrument.bids = [
                    [
                        values["bidPrice"],
                        values["bidSize"] * instrument.valueOfOneContract,
                    ]
                ]
        else:
            if "asks" in values:
                for ask in values["asks"]:
                    ask[1] *= instrument.valueOfOneContract
                instrument.asks = values["asks"]
            if "bids" in values:
                for bid in values["bids"]:
                    bid[1] *= instrument.valueOfOneContract
                instrument.bids = values["bids"]
        self.kline_hi_lo_values(symbol=symbol)

    def __update_position(self, key, values: dict) -> None:
        """
        There is only one Instrument array for the "instrument", "position",
        "quote", "orderBook10" websocket streams.
        """
        symbol = (self.ticker[values["symbol"]], self.name)
        instrument = self.Instrument[symbol]
        if "currentQty" in values:
            if values["currentQty"]:
                instrument.currentQty = (
                    values["currentQty"] * instrument.valueOfOneContract
                )
        if instrument.currentQty == 0:
            instrument.avgEntryPrice = 0
            instrument.marginCallPrice = 0
            instrument.unrealisedPnl = 0
        else:
            if "avgEntryPrice" in values:
                instrument.avgEntryPrice = values["avgEntryPrice"]
            if "unrealisedPnl" in values:
                instrument.unrealisedPnl = (
                    values["unrealisedPnl"]
                    / self.currency_divisor[instrument.settlCurrency[0]]
                )
            if "marginCallPrice" in values:
                if values["marginCallPrice"] == 100000000:
                    instrument.marginCallPrice = "inf"
                else:
                    instrument.marginCallPrice = values["marginCallPrice"]

    def __update_instrument(self, symbol: tuple, values: dict):
        symbol = (self.ticker[values["symbol"]], self.name)
        instrument = self.Instrument[symbol]
        if "fundingRate" in values:
            instrument.fundingRate = values["fundingRate"] * 100
        if "volume24h" in values:
            instrument.volume24h = values["volume24h"]
        if "state" in values:
            instrument.state = values["state"]

    def __update_account(self, settlCurrency: tuple, values: dict):
        account = self.Account[settlCurrency]
        if "maintMargin" in values:
            account.positionMagrin = (
                values["maintMargin"] / self.currency_divisor[settlCurrency[0]]
            )
        if "initMargin" in values:
            account.orderMargin = (
                values["initMargin"] / self.currency_divisor[settlCurrency[0]]
            )
        if "unrealisedPnl" in values:
            account.unrealisedPnl = (
                values["unrealisedPnl"] / self.currency_divisor[settlCurrency[0]]
            )
        if "walletBalance" in values:
            account.walletBalance = (
                values["walletBalance"] / self.currency_divisor[settlCurrency[0]]
            )
        if "marginBalance" in values:
            account.marginBalance = (
                values["marginBalance"] / self.currency_divisor[settlCurrency[0]]
            )
        if "availableMargin" in values:
            account.availableMargin = (
                values["availableMargin"] / self.currency_divisor[settlCurrency[0]]
            )

    def exit(self):
        """
        Closes websocket
        """
        try:
            self.ws.close()
        except Exception:
            pass
        self.logNumFatal = "SETUP"

    def transaction(self, **kwargs):
        """
        This method is replaced by transaction() from functions.py after the
        application is launched.
        """
        pass

    def ping_pong(self):
        if self.pinging == "pong":
            self.pinging = "ping"
            try:
                self.ws.send("ping")
            except Exception:
                self.logger.error("Bitmex websocket ping error. Reboot")
                self.logNumFatal = "SETUP"
                return False
            return True

        return False
