import json
import logging
import threading
import time
import traceback
from collections import OrderedDict
from time import sleep

import websocket

from api.variables import Variables
from display.functions import info_display

from .api_auth import generate_signature
import requests
from api.init import Setup
from common.data import MetaPosition, MetaInstrument


class Bitmex(Variables):
    class Position(metaclass=MetaPosition): pass
    class Instrument(metaclass=MetaInstrument): pass
    def __init__(self):
        self.name = "Bitmex"
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
            "order",
            "position",
            "trade",
            depth,
        }
        self.currency_divisor = {"XBt": 100000000, "USDt": 1000000, "BMEx": 1000000}
        self.symbol_category = dict()
        self.logger = logging.getLogger(__name__)
        print("!!!!!!!!!!!!! BITMEX !!!!!!!!!!!")

    def start(self):
        if not self.logNumFatal:
            self.__reset()
            self.__connect(self.__get_url())
            if self.logNumFatal == 0:
                self.logger.info("Connected to websocket.")
                info_display(self.name, "Connected to websocket.")
                self.__wait_for_tables()
                if self.logNumFatal == 0:
                    self.logger.info("Data received. Continuing.")

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
            while (not self.ws.sock or not self.ws.sock.connected) and time_out:
                sleep(1)
                time_out -= 1
            if not time_out:
                self.logger.error("Couldn't connect to websocket!")
                if self.logNumFatal < 1004:
                    self.logNumFatal = 1004
            else:
                # Subscribes symbol by symbol to all tables given
                for symbolName in map(lambda x: x[0], self.symbol_list):
                    subscriptions = []
                    for sub in self.table_subscription:
                        subscriptions += [sub + ":" + symbolName]
                    self.ws.send(json.dumps({"op": "subscribe", "args": subscriptions}))
        except Exception:
            self.logger.error("Exception while connecting to websocket. Restarting...")
            if self.logNumFatal < 1005:
                self.logNumFatal = 1005

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
                    + generate_signature(
                        self.api_secret, "GET", "/realtime", nonce, ""
                    ),
                    "api-key:" + self.api_key,
                ]
            else:
                self.logger.info("No authentication with API key.")
                return []
        except Exception:
            self.logger.error("Exception while authenticating. Restarting...")
            if self.logNumFatal < 1006:
                self.logNumFatal = 1006
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
                if self.logNumFatal < 1007:
                    self.logNumFatal = 1007
                break
            sleep(0.1)
        count2 = 0
        while (count <= 30) and (len(self.data["instrument"]) != len(self.symbol_list)):
            count2 += 1
            if count2 > 30:  # fails after 3 seconds
                instr_lack = self.symbol_list.copy()
                for instrument in self.data["instrument"].values():
                    if instrument["symbol"] in self.symbol_list:
                        instr_lack.remove(instrument["symbol"])
                self.logger.info(
                    "Timeout expired. Not all instruments has been loaded. "
                    + str(instr_lack)
                    + " - missing in the instrument table."
                )
                if self.logNumFatal < 1008:
                    self.logNumFatal = 1008
                break
            sleep(0.1)

    def __on_message(self, ws, message) -> None:
        """
        Parses websocket messages.
        """

        def generate_key(keys: list, val: dict, table: str) -> tuple:
            if table in ["instrument", "position", "quote", "orderBook10"]:
                val["category"] = self.symbol_category[val["symbol"]]
                val["market"] = self.name
            return tuple((val[key]) for key in keys)

        message = json.loads(message)
        action = message["action"] if "action" in message else None
        table = message["table"] if "table" in message else None
        self.message_counter = self.message_counter + 1
        try:
            if action:
                table_name = "orderBook" if table == "orderBook10" else table
                if table_name not in self.data:
                    self.data[table_name] = OrderedDict()
                if action == "partial":  # table snapshot
                    self.logger.debug("%s: partial" % table)
                    self.keys[table] = message["keys"]
                    if table == "quote":
                        self.keys[table] = ["symbol", "category", self.name]
                    elif table == "trade":
                        self.keys[table] = ["trdMatchID"]
                    elif table == "execution":
                        self.keys[table] = ["execID"]
                    elif table in ["instrument", "orderBook10", "position"]:
                        self.keys[table].append("category")
                        self.keys[table].append("market")
                    for val in message["data"]:
                        for key in self.keys[table]:
                            if key not in ["category", "market"]:
                                if key not in val:
                                    break
                        else:
                            key = generate_key(self.keys[table], val, table)
                            self.data[table_name][key] = val
                elif action == "insert":
                    for val in message["data"]:
                        key = generate_key(self.keys[table], val, table)
                        if table == "quote":
                            val["category"] = self.symbol_category[val["symbol"]]
                            if "bidPrice" in val:
                                self.data[table_name][key]["bidPrice"] = val["bidPrice"]
                                self.data[table_name][key]["bidSize"] = val["bidSize"]
                            if "askPrice" in val:
                                self.data[table_name][key]["askPrice"] = val["askPrice"]
                                self.data[table][key]["askSize"] = val["askSize"]
                            self.frames_hi_lo_values(data=self.data[table_name][key])
                        elif table == "execution":
                            val["symbol"] = (
                                val["symbol"],
                                self.symbol_category[val["symbol"]],
                                self.name
                            )
                            val["market"] = self.name
                            self.transaction(row=val)
                        else:
                            self.data[table_name][key] = val
                elif action == "update":
                    for val in message["data"]:
                        key = generate_key(self.keys[table], val, table)
                        if key not in self.data[table_name]:
                            return  # No key to update
                        self.data[table_name][key].update(val)
                        if table == "orderBook10":
                            self.frames_hi_lo_values(data=self.data[table_name][key])
                        elif table == "instrument":
                            self.instrument_update(symbol=key, instrument=val)
                        elif table == "position":
                            self.position_update(position=val)
                        # Removes cancelled or filled orders
                        elif (
                            table == "order" and self.data[table_name][key]["leavesQty"] <= 0
                        ):
                            self.data[table_name].pop(key)
                elif action == "delete":
                    for val in message["data"]:
                        key = generate_key(self.keys[table], val, table)
                        self.data[table_name].pop(key)
        except Exception:
            self.logger.error(
                traceback.format_exc()
            )  # Error in api.py. Take a look in logfile.log. Restarting...
            if self.logNumFatal < 1009:
                self.logNumFatal = 1009

    def __on_error(self, ws, error) -> None:
        """
        We are here if websocket has fatal errors.
        """
        self.logger.error("Error: %s" % error)
        if self.logNumFatal < 1010:
            self.logNumFatal = 1010

    def __on_open(self, ws) -> None:
        self.logger.debug("Websocket opened")

    def __on_close(self, *args) -> None:
        self.logger.info("Websocket closed")
        if self.logNumFatal < 1011:
            self.logNumFatal = 1011

    def __reset(self) -> None:
        """
        Resets internal data.
        """
        self.data = {}
        self.keys = {}

    def frames_hi_lo_values(self, data: dict) -> None:
        if data["symbol"] in self.frames:
            for timeframe in self.frames[data["symbol"]].values():
                if timeframe["data"]:
                    if self.depth == "orderBook":
                        if data["asks"]:
                            if data["asks"][0][0] > timeframe["data"][-1]["hi"]:
                                timeframe["data"][-1]["hi"] = data["asks"][0][0]
                        if data["bids"]:
                            if data["bids"][0][0] < timeframe["data"][-1]["lo"]:
                                timeframe["data"][-1]["lo"] = data["bids"][0][0]
                    else:
                        if "askPrice" in data:
                            if data["askPrice"] > timeframe["data"][-1]["hi"]:
                                timeframe["data"][-1]["hi"] = data["askPrice"]
                        if "bidPrice" in data:
                            if data["bidPrice"] < timeframe["data"][-1]["lo"]:
                                timeframe["data"][-1]["lo"] = data["bidPrice"]

    def position_update(self, position: dict) -> None:
        """
        Updates the positions variable for subscribed instruments each time
        information from "position" table is received from the websocket.
        """
        symbol = (position["symbol"], position["category"], self.name)
        self.positions[symbol]["POS"] = position["currentQty"]
        if "avgEntryPrice" in position:
            self.positions[symbol]["ENTRY"] = position["avgEntryPrice"]
        else:
            self.positions[symbol]["ENTRY"] = 0
        if "marginCallPrice" in position:
            self.positions[symbol]["MCALL"] = position["marginCallPrice"]
        else:
            self.positions[symbol]["MCALL"] = 0
        if "unrealisedPnl" in position:
            self.positions[symbol]["PNL"] = position["unrealisedPnl"]
        else:
            self.positions[symbol]["PNL"] = 0

    def instrument_update(self, symbol: tuple, instrument: dict):
        if "fundingRate" in instrument:
            self.Instrument[symbol].fundingRate = instrument["fundingRate"]
        if "volume24h" in instrument:
            self.Instrument[symbol].volume24h = instrument["volume24h"]
        if "state" in instrument:
            self.Instrument[symbol].state = instrument["state"]

    def exit(self):
        """
        Closes websocket
        """
        try:
            self.ws.close()
        except Exception:
            pass

    def transaction(self, **kwargs):
        """
        This method is replaced by transaction() from functions.py after the
        application is launched.
        """
        pass
