import json
import threading
import time
import traceback
from collections import OrderedDict
from datetime import datetime, timezone
from time import sleep

import requests
import websocket

import services as service
from api.errors import Error
from api.init import Setup
from api.variables import Variables
from common.data import MetaAccount, MetaInstrument, MetaResult
from common.variables import Variables as var
from services import display_exception

from .api_auth import API_auth
from .error import ErrorStatus


class Bitmex(Variables):
    class Account(metaclass=MetaAccount):
        pass

    class Instrument(metaclass=MetaInstrument):
        pass

    class Result(metaclass=MetaResult):
        pass

    def __init__(self):
        self.object = Bitmex
        self.name = "Bitmex"
        self.data = dict()
        self.Api_auth = API_auth
        Setup.variables(self)
        self.session = requests.Session()
        self.session.headers.update({"user-agent": "Tmatic"})
        self.session.headers.update({"content-type": "application/json"})
        self.session.headers.update({"accept": "application/json"})
        self.currency_divisor = {
            "XBt": 100000000,
            "USDt": 1000000,
            "BMEx": 1000000,
            "MATIc": 1000000,
            "BBx": 1000000,
        }  # MATIc, BBx are probably incorrect
        self.timefrs = OrderedDict([(1, "1m"), (5, "5m"), (60, "1h")])
        self.logger = var.logger
        self.klines = dict()
        self.setup_orders = list()
        self.account_disp = ""
        self.pinging = "pong"
        self.ticker = dict()
        self.instrument_index = OrderedDict()
        self.unsubscribe = dict()
        self.api_auth = API_auth
        self.get_error = ErrorStatus

    def setup_session(self):
        """
        Not used in Bitmex.
        """
        pass

    def start_ws(self) -> str:
        if var.order_book_depth != "quote":
            self.depth = "orderBook10"
        else:
            self.depth = "quote"
        self.table_subscription = {
            "margin",
            "execution",
            "instrument",
            "position",
            self.depth,
            # "order",
            # "trade",
        }
        if not self.logNumFatal:
            self.__reset()
            time_out = 5
            websocket.setdefaulttimeout(time_out)
            self.ws = websocket.WebSocketApp(
                self.__get_url(),
                on_open=self.__on_open,
                on_close=self.__on_close,
                header=self.__get_auth(),
                on_message=self.__on_message,
                on_error=self.__on_error,
            )
            newth = threading.Thread(target=lambda: self.ws.run_forever())
            newth.daemon = True
            newth.start()
            # Waits for connection established
            while (
                (not self.ws.sock or not self.ws.sock.connected)
                and time_out >= 0
                and not self.logNumFatal
            ):
                sleep(0.1)
                time_out -= 0.1
            if time_out <= 0:
                self.logger.error("Couldn't connect to websocket!")
                return service.unexpected_error(self)
            self.logger.info("Connected to websocket.")

            return ""

    def setup_streams(self) -> str:
        for symbol in self.symbol_list:
            instrument = self.Instrument[symbol]
            if instrument.settlCurrency:
                self.Result[(instrument.settlCurrency[0], self.name)]
        try:
            if not self.logNumFatal:
                # Subscribes symbol by symbol to all tables given
                for symbol in self.symbol_list:
                    subscriptions = []
                    for sub in self.table_subscription:
                        subscriptions += [sub + ":" + self.Instrument[symbol].ticker]
                    self.logger.info("ws subscribe - " + str(subscriptions))
                    self.ws.send(json.dumps({"op": "subscribe", "args": subscriptions}))
        except Exception as exception:
            display_exception(exception)
            message = "Exception while connecting to websocket."
            if not self.logNumFatal:
                message += " Reboot."
                service.unexpected_error(self)
            self.logger.error(message)
            return self.logNumFatal
        if not self.logNumFatal:
            self.__wait_for_tables(self.symbol_list)
            if not self.logNumFatal:
                self.logger.info("Data received. Continuing.")
                self.pinging = "pong"

        return ""

    def subscribe_symbol(self, symbol: tuple, timeout=None) -> None:
        subscriptions = []
        for sub in self.table_subscription:
            subscriptions += [sub + ":" + self.Instrument[symbol].ticker]
        self.logger.info("ws subscribe - " + str(subscriptions))
        self.ws.send(json.dumps({"op": "subscribe", "args": subscriptions}))
        symbol_list = self.symbol_list.copy()
        symbol_list.append(symbol)
        res = self.__wait_for_tables(symbol_list)  # subscription confirmation

        return res

    def unsubscribe_symbol(self, symbol: tuple) -> None:
        subscriptions = []
        symb = self.Instrument[symbol].symbol
        for sub in self.table_subscription:
            subscriptions += [sub + ":" + self.Instrument[symbol].ticker]
        self.unsubscribe[symb] = subscriptions
        self.logger.info("ws unsubscribe - " + str(subscriptions))
        self.ws.send(json.dumps({"op": "unsubscribe", "args": subscriptions}))
        tm, sl = 0, 0.1
        while self.unsubscribe[symb]:
            if tm > var.timeout:
                return "timeout"
            tm += sl
            sleep(sl)
        del self.unsubscribe[symb]
        if symbol in self.data["instrument"]:
            del self.data["instrument"][symbol]
        if symbol in self.data[self.depth]:
            del self.data[self.depth][symbol]
        if (self.user_id, symb, self.name) in self.data["position"]:
            del self.data["position"][(self.user_id, symb, self.name)]

        return ""

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
            service.unexpected_error(self)
            return []

    def __wait_for_tables(self, symbol_list) -> None:
        """
        Waiting for data to be loaded from the websocket. If not all data is
        received after the timeout expires, the websocket is rebooted.
        """
        count = 0
        if not self.logNumFatal:
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
                    return service.unexpected_error(self)
                sleep(0.1)
            count = 0
        while True:
            count += 1
            if count > 30:  # fails after 3 seconds
                instr_lack = symbol_list.copy()
                for instrument in self.data["instrument"].values():
                    symb = (instrument["symbol"], self.name)
                    if symb in symbol_list:
                        instr_lack.remove(symb)
                self.logger.info(
                    "Timeout expired. Not all instruments has been loaded. "
                    + str(instr_lack)
                    + " - missing in the instrument table."
                )
                return "error"
            num = 0
            for symbol in symbol_list:
                if symbol in self.data["instrument"].keys():
                    num += 1
            if num == len(symbol_list):
                return ""
            sleep(0.1)

    def _generate_key(self, keys: list, val: dict) -> tuple:
        val["market"] = self.name
        return tuple((val[key]) for key in keys)

    def __on_message(self, ws, message) -> None:
        """
        Parses websocket messages.
        """
        if message == "pong":
            self.pinging = "pong"
            return

        message = json.loads(message)
        action = message["action"] if "action" in message else None
        table = message["table"] if "table" in message else None
        try:
            if action:
                # table_name = "orderBook" if table == "orderBook10" else table
                table_name = table
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
                            key = self._generate_key(self.keys[table], val)
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
                        key = self._generate_key(self.keys[table], val=val)
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
                                # val["lastQty"] *= instrument.valueOfOneContract
                                val["lastQty"] /= instrument.myMultiplier
                            if "leavesQty" in val:
                                # val["leavesQty"] *= instrument.valueOfOneContract
                                val["leavesQty"] /= instrument.myMultiplier
                            if "orderQty" in val:
                                val["orderQty"] /= instrument.myMultiplier
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
                        key = self._generate_key(self.keys[table], val=val)
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
                        key = self._generate_key(self.keys[table], val)
                        self.data[table_name].pop(key)
            elif "unsubscribe" in message:
                symb = message["unsubscribe"].split(":")[1]
                if symb in self.unsubscribe:
                    self.unsubscribe[symb].remove(message["unsubscribe"])
        except Exception:
            self.logger.error(
                traceback.format_exc()
            )  # Error in api.py. Take a look in logfile.log. Restarting...
            service.unexpected_error(self)

    def __on_error(self, ws, error) -> None:
        """
        We are here if websocket has fatal errors.
        """
        Error.handler(self, exception=error, verb="WebSocket")
        # self.logger.error("Error: %s" % error)

    def __on_open(self, ws) -> None:
        self.logger.debug("Websocket opened")

    def __on_close(self, *args) -> None:
        self.logger.info("Websocket closed.")
        # service.unexpected_error(self)

    def __reset(self) -> None:
        """
        Resets internal data.
        """
        self.data = {}
        self.keys = {}

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
                        values["askSize"] / instrument.myMultiplier,
                    ]
                ]
            if "bidPrice" in values:
                instrument.bids = [
                    [
                        values["bidPrice"],
                        values["bidSize"] / instrument.myMultiplier,
                    ]
                ]
        else:
            if "asks" in values:
                for ask in values["asks"]:
                    ask[1] /= instrument.myMultiplier
                instrument.asks = values["asks"]
            if "bids" in values:
                for bid in values["bids"]:
                    bid[1] /= instrument.myMultiplier
                instrument.bids = values["bids"]
        if symbol in self.klines:
            service.kline_hi_lo_values(self, symbol=symbol, instrument=instrument)

    def __update_position(self, key, values: dict) -> None:
        """
        There is only one Instrument array for the "instrument", "position",
        "quote", "orderBook10" websocket streams.
        """
        symbol = (self.ticker[values["symbol"]], self.name)
        instrument = self.Instrument[symbol]
        if "currentQty" in values:
            if values["currentQty"] or values["currentQty"] == 0:
                instrument.currentQty = values["currentQty"] / instrument.myMultiplier
        if instrument.currentQty == 0:
            instrument.avgEntryPrice = var.DASH
            instrument.marginCallPrice = var.DASH
            instrument.unrealisedPnl = var.DASH
        else:
            if "avgEntryPrice" in values:
                if values["avgEntryPrice"] is None:
                    values["avgEntryPrice"] == var.DASH
                else:
                    instrument.avgEntryPrice = service.set_number(
                        instrument=instrument, number=values["avgEntryPrice"]
                    )
            if "unrealisedPnl" in values:
                instrument.unrealisedPnl = (
                    values["unrealisedPnl"]
                    / self.currency_divisor[instrument.settlCurrency[0]]
                )
            if "liquidationPrice" in values:
                instrument.marginCallPrice = values["liquidationPrice"]

    def __update_instrument(self, symbol: tuple, values: dict):
        symbol = (self.ticker[values["symbol"]], self.name)
        instrument = self.Instrument[symbol]
        if "fundingRate" in values:
            instrument.fundingRate = values["fundingRate"] * 100
        if "volume24h" in values:
            instrument.volume24h = values["volume24h"]
        if "state" in values:
            instrument.state = values["state"]
        if "markPrice" in values:
            instrument.markPrice = values["markPrice"]

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
        self.api_is_active = False

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
                service.unexpected_error(self)
                return False
            return True

        return False

    def _put_message(self, message: str, warning=None) -> None:
        """
        Places an information message into the queue and the logger.
        """
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
