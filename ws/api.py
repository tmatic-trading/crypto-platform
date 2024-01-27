import json
import logging
import threading
import time
import traceback
from collections import OrderedDict
from datetime import datetime
from time import sleep
from typing import Union
from urllib.parse import urlparse, urlunparse

import requests
import websocket

from ws.api_auth import API_auth, generate_signature


class Connect_websocket:
    def __init__(
        self,
        endpoint=None,
        symbol=None,
        api_key=None,
        api_secret=None,
        info_display=None,
        order_book_depth=None,
        instruments=None,
        format_price=None
    ):
        """
        Initialize and connect to websocket.
        """
        self.instruments = instruments
        self.format_price = format_price
        self.depth = order_book_depth
        self.table_subscription = {
            "margin",
            "execution",
            "instrument",
            "order",
            "position",
            self.depth,
        }
        self.message_counter = 0
        self.api_key = api_key
        self.api_secret = api_secret
        self.endpoint = endpoint
        self.symbol_list = symbol
        self.info_display = info_display
        self.logger = logging.getLogger(__name__)
        self.__reset()
        self.logNumFatal = 0  # logNumFatal < 1000 means not fatal;
        # 1000 < logNumFatal < 2000 means reloading terminal;
        # logNumFatal > 2000 means fatal => stop all
        self.maxRetryRest = (
            3  # number of retry attempts for non-trading orders like POST, PUT, DELETE
        )
        self.myOrderID = ""
        self.timeoutOccurred = ""
        self.__connect(url=self.__get_url())

        # Prepare HTTPS session
        self.session = requests.Session()
        self.session.headers.update({"user-agent": "Tmatic"})
        self.session.headers.update({"content-type": "application/json"})
        self.session.headers.update({"accept": "application/json"})
        if self.logNumFatal == 0:
            self.logger.info("Connected to websocket.")
            self.info_display("Connected to websocket.")
            self.instruments = self.active_instruments(instruments=self.instruments)
            self.__wait_for_tables()
            if self.logNumFatal == 0:
                self.logger.info("Data received. Continuing.")

    def place_limit(
        self, quantity: int, price: float, clOrdID: str, symbol: str
    ) -> Union[dict, None]:
        """
        Places a limit order
        """
        postData = {
            "symbol": symbol,
            "orderQty": quantity,
            "price": price,
            "clOrdID": clOrdID,
            "ordType": "Limit",
        }

        return self.__request(path="order", postData=postData, verb="POST")

    def replace_limit(
        self, quantity: int, price: float, orderID: str, symbol: str
    ) -> Union[dict, None]:
        """
        Moves a limit order
        """
        postData = {
            "symbol": symbol,
            "price": price,
            "orderID": orderID,
            "leavesQty": abs(quantity),
            "ordType": "Limit",
        }

        return self.__request(path="order", postData=postData, verb="PUT")

    def remove_order(self, orderID: str) -> Union[list, None]:
        """
        Deletes an order
        """
        postData = {"orderID": orderID}

        return self.__request(path="order", postData=postData, verb="DELETE")

    def trading_history(
        self, histCount: int, start=None, time=None
    ) -> Union[list, None]:
        if start:
            return self.__request(
                path="execution/tradeHistory?count="
                + str(histCount)
                + "&start="
                + str(start)
                + "&reverse=false",
                verb="GET",
            )
        elif time:
            return self.__request(
                path="execution/tradeHistory?count="
                + str(histCount)
                + "&reverse=false&startTime="
                + str(time),
                verb="GET",
            )
        else:
            return "error"

    def urgent_announcement(self):
        return self.__request(path="/announcement/urgent", verb="GET")

    def trade_bucketed(
        self, symbol: str, time: datetime, timeframe: str
    ) -> Union[list, None]:
        """
        Gets timeframe data. Available time interval: 1m,5m,1h,1d.
        """
        path = (
            "trade/bucketed?binSize="
            + str(timeframe)
            + "&count=1000&reverse=false&partial=true&symbol="
            + str(symbol)
            + "&columns=open%2C%20high%2C%20low%2C%20close&startTime="
            + str(time)
        )

        return self.__request(path=path, verb="GET")

    def get_user(self) -> Union[dict, None]:
        """
        Gets account info
        """

        return self.__request(path="user", verb="GET")

    def get_ticker(self, ticker: OrderedDict) -> OrderedDict:
        """
        Returns a ticker entity.
        """
        for key, val in self.data[self.depth].items():
            symbol = key[0][1]
            if self.depth == "quote":
                if "bidPrice" in val:
                    ticker[symbol]["bid"] = val["bidPrice"]
                    ticker[symbol]["bidSize"] = val["bidSize"]
                if "askPrice" in val:
                    ticker[symbol]["ask"] = val["askPrice"]
                    ticker[symbol]["askSize"] = val["askSize"]
            else:
                if val["bids"]:
                    ticker[symbol]["bid"] = val["bids"][0][0]
                    ticker[symbol]["bidSize"] = val["bids"][0][1]
                if val["asks"]:
                    ticker[symbol]["ask"] = val["asks"][0][0]
                    ticker[symbol]["askSize"] = val["asks"][0][1]

        return ticker

    def get_position(self, positions: OrderedDict) -> OrderedDict:
        """
        Gets instrument's position for each symbol.
        """
        for symbol in self.symbol_list:
            positions[symbol]["SYMB"] = symbol
            for val in self.data["position"].values():
                if val["symbol"] == symbol:
                    positions[symbol]["POS"] = val["currentQty"]
                    if "avgEntryPrice" in val:
                        positions[symbol]["ENTRY"] = val["avgEntryPrice"]
                    else:
                        positions[symbol]["ENTRY"] = 0
                    if "marginCallPrice" in val:
                        positions[symbol]["MCALL"] = val["marginCallPrice"]
                    else:
                        positions[symbol]["MCALL"] = 0
                    positions[symbol]["PNL"] = val["unrealisedPnl"]
                    break

        return positions

    def get_additional_position_data(
        self, positions: OrderedDict, symbol: str
    ) -> OrderedDict:
        """
        Gets instrument position when instrument is not in the symbol_list
        """
        path = "position?filter=%7B%22symbol%22%3A%22" + symbol + "%22%7D"
        data = self.__request(path=path, verb="GET")
        if isinstance(data, list):
            if data:
                positions[symbol] = {"POS": data[0]["currentQty"]}
            else:
                positions[symbol] = {"POS": 0}
            self.logger.info(symbol + " has been added to the var.positions dictionary")
        else:
            self.logger.info(symbol + " not found in get_additional_position_data()")

        return positions

    def get_instrument(self, instruments: OrderedDict) -> OrderedDict:
        """
        Gets instrument's data for each symbol.
        """
        for symbol in self.symbol_list:
            for val in self.data["instrument"].values():
                if val["symbol"] == symbol:
                    instruments[symbol]["symbol"] = val["symbol"]
                    instruments[symbol]["state"] = val["state"]
                    if "fundingRate" in val:
                        instruments[symbol]["fundingRate"] = val["fundingRate"]
                    else:
                        instruments[symbol]["fundingRate"] = 0
                    instruments[symbol]["tickSize"] = val["tickSize"]
                    instruments[symbol]["volume24h"] = val["volume24h"]
                    instruments[symbol]["lotSize"] = val["lotSize"]
                    instruments[symbol]["settlCurrency"] = val["settlCurrency"]
                    instruments[symbol]["isInverse"] = val["isInverse"]
                    break

        return instruments

    def get_funds(self) -> list:
        """
        Cash in the account
        """

        return self.data["margin"].values()

    def get_exec(self) -> list:
        """
        Gets a raw execution list.
        """

        return self.data["execution"]

    def open_orders(self) -> list:
        """
        Gets open orders.
        """

        return self.data["order"].values()

    def market_depth10(self) -> list:
        """
        Gets market depth (orderbook), 10 lines deep.
        """

        return self.data["orderBook10"].values()

    def get_additional_instrument_data(
        self, symbol: list, instruments: OrderedDict
    ) -> OrderedDict:
        """
        Adds fields such as: isInverse, multiplier...
        """

        path = "instrument?symbol=" + symbol
        instrument = self.__request(path=path, verb="GET")[0]
        instruments = self.fill_instrument_data(
            instrument=instrument, instruments=instruments
        )

        return instruments

    def active_instruments(self, instruments: OrderedDict) -> OrderedDict:
        """
        Gets all active instruments
        """
        data = self.__request(path="instrument/active", verb="GET")
        for instrument in data:
            instruments = self.fill_instrument_data(
                instrument=instrument, instruments=instruments
            )
        for symbol in self.symbol_list:
            if not instruments[symbol]["symbol"]:
                self.logger.error(
                    "Unknown symbol: "
                    + symbol
                    + ". Check the SYMBOLS in the .env file."
                )
                exit(1)

        return instruments

    def fill_instrument_data(
        self, instrument: dict, instruments: OrderedDict
    ) -> OrderedDict:
        """
        Filling the instruments with data
        """
        symbol = instrument["symbol"]
        if symbol not in instruments:
            instruments[symbol] = dict()
        instruments[symbol]["symbol"] = instrument["symbol"]
        instruments[symbol]["multiplier"] = instrument["multiplier"]
        if "settlCurrency" in instrument:
            instruments[symbol]["settlCurrency"] = instrument["settlCurrency"]
        else:
            instruments[symbol]["settlCurrency"] = None
        instruments[symbol]["tickSize"] = instrument["tickSize"]
        instruments[symbol]["lotSize"] = instrument["lotSize"]
        if "bidPrice" in instrument:
            instruments[symbol]["bidPrice"] = instrument["bidPrice"]
        else:
            instruments[symbol]["bidPrice"] = None
        if "askPrice" in instrument:
            instruments[symbol]["askPrice"] = instrument["askPrice"]
        else:
            instruments[symbol]["askPrice"] = None
        instruments[symbol]["isInverse"] = instrument["isInverse"]
        if "underlyingToSettleMultiplier" not in instrument:
            instrument["underlyingToSettleMultiplier"] = None
        if "underlyingToPositionMultiplier" not in instrument:
            instrument["underlyingToPositionMultiplier"] = None
        if (
            instrument["underlyingToPositionMultiplier"] is None
            and instrument["underlyingToSettleMultiplier"] is None
        ):
            instruments[symbol]["myMultiplier"] = 1
        elif instrument["underlyingToSettleMultiplier"] is None:
            instruments[symbol]["myMultiplier"] = int(
                instrument["quoteToSettleMultiplier"] / instrument["multiplier"]
            )
            if instruments[symbol]["myMultiplier"] == 0:
                instruments[symbol]["myMultiplier"] = 1
        elif instrument["isInverse"]:
            instruments[symbol]["myMultiplier"] = int(
                instrument["underlyingToSettleMultiplier"] / instrument["multiplier"]
            )
        else:
            instruments[symbol]["myMultiplier"] = 1
        if "expiry" in instrument and instrument["expiry"]:
            instruments[symbol]["expiry"] = datetime.strptime(
                instrument["expiry"][:-1], "%Y-%m-%dT%H:%M:%S.%f"
            )
        else:
            instruments[symbol]["expiry"] = "Perpetual"

        return instruments

    def exit(self):
        """
        Closes websocket
        """
        try:
            self.ws.close()
        except Exception:
            pass

    def __request(
        self, path: str, verb: str, postData=None, timeout=7, teorPrice=None
    ) -> Union[dict, list, None]:
        """
        Sends a request to the exchange
        """

        def info_warn_err(whatNow, textNow, codeNow=0):
            if whatNow == "INFO":
                self.logger.info(textNow)
            elif whatNow == "WARN":
                self.logger.warning(textNow)
                if codeNow > self.logNumFatal:
                    self.logNumFatal = codeNow
            else:
                self.logger.error(textNow)
                if codeNow > self.logNumFatal:
                    self.logNumFatal = codeNow

        url = self.endpoint + path
        cur_retries = 1
        auth = API_auth(self.api_key, self.api_secret)
        while True:
            stop_retries = cur_retries
            # Makes the request
            response = None
            if isinstance(postData, dict):
                tmp = postData.copy()
                if "price" in tmp:
                    tmp["price"] = self.format_price(
                        number=tmp["price"], symbol=tmp["symbol"]
                    )
            else:
                tmp = postData
            try:
                if teorPrice is None:
                    info_warn_err(
                        "INFO",
                        "("
                        + url[0]
                        + url[1]
                        + url[2]
                        + url[3]
                        + url[4]
                        + ") sending %s to %s: %s"
                        % (verb, path, json.dumps(tmp or "")),
                    )
                else:
                    info_warn_err(
                        "INFO",
                        "("
                        + url[0]
                        + url[1]
                        + url[2]
                        + url[3]
                        + url[4]
                        + ") sending %s to %s: %s, theor: %s"
                        % (
                            verb,
                            path,
                            json.dumps(tmp or ""),
                            teorPrice,
                        ),
                    )
                req = requests.Request(verb, url, json=postData, auth=auth, params=None)
                prepped = self.session.prepare_request(req)
                response = self.session.send(prepped, timeout=timeout)
                # Make non-200s throw
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response is None:
                    raise e
                cur_retries += 1
                # 401 - Auth error. This is fatal.
                if response.status_code == 401:
                    info_warn_err(
                        "ERROR",
                        "API Key or Secret incorrect (401): " + response.text,
                        2001,
                    )  # stop all

                # 404 - can be thrown if order does not exist
                elif response.status_code == 404:
                    if verb == "DELETE" and postData:
                        info_warn_err(
                            "WARN",
                            "DELETE orderID=%s: not found (404)" % postData["orderID"],
                            response.status_code,
                        )
                    elif verb == "PUT" and postData:
                        info_warn_err(
                            "WARN",
                            "PUT orderID=%s: not found (404)" % postData["orderID"],
                            response.status_code,
                        )
                    else:
                        info_warn_err(
                            "ERROR",
                            "Unable to contact API (404). %s: %s"
                            % (url, json.dumps(postData or "")),
                            1001,
                        )

                # 429 - ratelimit. If orders are posted or put too often
                elif response.status_code == 429:
                    info_warn_err(
                        "WARN",
                        "Rate limit exceeded (429). %s: %s"
                        % (url, json.dumps(postData or "")),
                        response.status_code,
                    )
                    time.sleep(1)

                # 503 - The exchange temporary downtime. Try again
                elif response.status_code == 503:
                    error = response.json()["error"]
                    message = error["message"] if error else ""
                    info_warn_err(
                        "WARN",
                        message + " (503). %s: %s" % (url, json.dumps(postData or "")),
                        response.status_code,
                    )

                elif response.status_code == 400:
                    error = response.json()["error"]
                    message = error["message"].lower() if error else ""
                    if (
                        verb == "PUT" and "invalid ordstatus" in message
                    ):  # move order with origClOrdID does not exist. Probably already executed
                        info_warn_err(
                            "WARN",
                            error["message"]
                            + " (400). %s: %s" % (url, json.dumps(postData or "")),
                            response.status_code,
                        )
                    elif verb == "POST" and "duplicate clordid" in message:
                        info_warn_err(
                            "ERROR",
                            error["message"]
                            + " (400). %s: %s" % (url, json.dumps(postData or "")),
                            1,
                        )  # impossible situation => stop trading
                    elif "insufficient available balance" in message:
                        info_warn_err(
                            "ERROR",
                            error["message"]
                            + " (400). %s: %s" % (url, json.dumps(postData or "")),
                            2,
                        )
                    elif (
                        "request has expired" in message
                    ):  # This request has expired - `expires` is in the past
                        info_warn_err(
                            "WARN",
                            error["message"]
                            + " (400)."
                            + " Your computer's system time may be incorrect. %s: %s"
                            % (url, json.dumps(postData or "")),
                            998,
                        )
                    elif (
                        "too many open orders" in message
                    ):  # When limit of 200 orders reached
                        info_warn_err(
                            "WARN",
                            error["message"]
                            + " (400). %s: %s" % (url, json.dumps(postData or "")),
                            5,
                        )
                    else:  # Example: wrong parameters set (tickSize, lotSize, etc)
                        errCode = 3 if postData else 997
                        info_warn_err(
                            "ERROR",
                            error["message"]
                            + " (400 else). %s: %s" % (url, json.dumps(postData or "")),
                            errCode,
                        )
                else:  # Unknown error type
                    errCode = 4 if postData else 996
                    info_warn_err(
                        "ERROR",
                        "Unhandled %s: %s. %s: %s"
                        % (e, response.text, url, json.dumps(postData or "")),
                        errCode,
                    )
            except (
                requests.exceptions.Timeout
            ) as e:  # sometimes there is no answer during timeout period (currently = 7 sec).
                if postData:  # (POST, PUT or DELETE) => terminal reloads
                    self.timeoutOccurred = "Timed out on request"  # reloads terminal
                    errCode = 0
                else:
                    errCode = 999
                    cur_retries += 1
                info_warn_err(
                    "WARN",
                    "Timed out on request. %s: %s" % (url, json.dumps(postData or "")),
                    errCode,
                )
                self.info_display("Websocket. Timed out on request")

            except requests.exceptions.ConnectionError as e:
                info_warn_err(
                    "ERROR",
                    "Unable to contact API: %s. %s: %s"
                    % (e, url, json.dumps(postData or "")),
                    1002,
                )
                self.info_display("Websocket. Unable to contact API")
                cur_retries += 1
            if postData:  # trading orders (POST, PUT, DELETE)
                if cur_retries == stop_retries:  # means no errors
                    if self.timeoutOccurred == "":
                        pos_beg = response.text.find('"orderID":"') + 11
                        pos_end = response.text.find('"', pos_beg)
                        self.myOrderID = response.text[pos_beg:pos_end]
                    else:
                        self.myOrderID = self.timeoutOccurred
                    if self.logNumFatal < 1000:
                        self.logNumFatal = 0
                break
            else:
                if cur_retries > self.maxRetryRest:
                    info_warn_err("ERROR", "Max retries hit. Reboot", 1003)
                    self.info_display("ERROR, Max retries hit. Reboot")
                    break
                if cur_retries == stop_retries:  # means no errors
                    if self.logNumFatal < 1000:
                        self.logNumFatal = 0
                    break
            if path == "/announcement/urgent":
                break
            else:
                time.sleep(3)
        self.time_response = datetime.utcnow()
        if response:
            return response.json()
        else:
            return None

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
                for symbolName in self.symbol_list:
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
        urlDetails = list(urlparse(self.endpoint))
        urlDetails[0] = urlDetails[0].replace("http", "ws")
        urlDetails[1] = urlDetails[1].replace("www.bitmex.com", "ws.bitmex.com")
        urlDetails[2] = "/realtime?subscribe=margin"

        return urlunparse(urlDetails)

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
        while not self.table_subscription <= set(self.data):
            count += 1
            if count > 30:  # fails after 3 seconds
                table_lack = self.table_subscription.copy()
                for table in self.data.keys():
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

        def generate_key(keys, val) -> tuple:
            return tuple((key, val[key]) for key in keys)

        message = json.loads(message)
        action = message["action"] if "action" in message else None
        table = message["table"] if "table" in message else None
        self.message_counter = self.message_counter + 1
        try:
            if action:
                if table not in self.data:
                    self.data[table] = OrderedDict()
                if action == "partial":  # table snapshot
                    self.logger.debug("%s: partial" % table)
                    self.keys[table] = message["keys"]                    
                    if table == "quote":
                        self.keys[table] = ["symbol"]
                    elif table == "trade":
                        self.keys[table] = ["trdMatchID"]
                    elif table == "execution":
                        self.keys[table] = ["execID"]
                    for val in message["data"]:
                        for key in self.keys[table]:
                            if key not in val:
                                break
                        else:
                            key = generate_key(self.keys[table], val)
                            self.data[table][key] = val
                elif action == "insert":
                    if table == "quote":
                        for val in message["data"]:
                            key = generate_key(self.keys[table], val)
                            if "bidPrice" in val:
                                self.data[table][key]["bidPrice"] = val["bidPrice"]
                                self.data[table][key]["bidSize"] = val["bidSize"]
                            if "askPrice" in val:
                                self.data[table][key]["askPrice"] = val["askPrice"]
                                self.data[table][key]["askSize"] = val["askSize"]
                    else:
                        for val in message["data"]:
                            key = generate_key(self.keys[table], val)
                            self.data[table][key] = val
                elif action == "update":
                    for val in message["data"]:
                        key = generate_key(self.keys[table], val)
                        if key not in self.data[table]:
                            return  # No key to update
                        self.data[table][key].update(val)
                        # Removes cancelled or filled orders
                        if table == "order" and self.data[table][key]["leavesQty"] <= 0:
                            self.data[table].pop(key)
                elif action == "delete":
                    for val in message["data"]:
                        key = generate_key(self.keys[table], val)
                        self.data[table].pop(key)
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
