import json
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Callable

import requests
import websocket

import services as service
from api.init import Setup
from api.variables import Variables
from common.data import MetaAccount, MetaInstrument, MetaResult
from common.variables import Variables as var
from services import display_exception


class Deribit(Variables):
    class Account(metaclass=MetaAccount):
        pass

    class Instrument(metaclass=MetaInstrument):
        pass

    class Result(metaclass=MetaResult):
        pass

    def __init__(self):
        self.name = "Deribit"
        self.api_version = "/api/v2/"
        Setup.variables(self, self.name)
        self.session = requests.Session()
        self.define_category = {
            "future linear": "future L",
            "future reversed": "future R",
            "future_combo reversed": "future CR",
            "spot linear": "spot L",
            "option linear": "option L",
            "option reversed": "option R",
            "option_combo reversed": "option CR",
        }
        self.settleCoin_list = list()
        self.ws = websocket
        self.logger = var.logger
        if self.depth == "quote":
            self.orderbook_depth = 1
        else:
            self.orderbook_depth = 10
        self.robots = OrderedDict()
        self.frames = dict()
        self.robot_status = dict()
        self.setup_orders = list()
        self.account_disp = ""
        self.orders = dict()
        self.access_token = ""
        self.pinging = datetime.now(tz=timezone.utc)
        self.heartbeat_interval = 10
        self.callback_directory = dict()
        self.response = dict()
        self.settleCoin_list = ["BTC", "ETH", "USDC", "USDT", "EURR"]
        self.ws_request_delay = 5
        self.scheme = {
            "matching_engine": {
                "lock": threading.Lock(),
                "scheme": "burst",
                "time": [],
            },
            "non_matching_engine": {
                "lock": threading.Lock(),
                "scheme": "burst",
                "time": [],
            },
            "private/get_transaction_log": {
                "lock": threading.Lock(),
                "scheme": "burst",
                "time": [],
            },
        }
        self.ticker = dict()

    def start(self):
        for symbol in self.symbol_list:
            instrument = self.Instrument[symbol]
            if "linear" in instrument.category:
                self.Result[(instrument.quoteCoin, self.name)]
            elif "reversed" in instrument.category:
                self.Result[(instrument.baseCoin, self.name)]
            elif "spot" in instrument.category:
                self.Result[(instrument.baseCoin, self.name)]
                self.Result[(instrument.quoteCoin, self.name)]
            elif "option" in instrument.category:
                self.Result[(instrument.baseCoin, self.name)]
        self.__connect()
        if not self.logNumFatal:
            self.logger.info("Connected to websocket.")
            self.__establish_heartbeat()
            self.__subscribe()
            self.__confirm_subscription()

    def __connect(self) -> None:
        """
        Connecting to websocket.
        """
        self.logger.info("Connecting to websocket")
        self.ws = websocket.WebSocketApp(
            self.ws_url + self.api_version,
            on_message=self.__on_message,
            on_error=self.__on_error,
            on_close=self.__on_close,
            on_open=self.__on_open,
        )
        newth = threading.Thread(target=lambda: self.ws.run_forever())
        newth.daemon = True
        newth.start()
        # Waits for connection established
        time_out, slp = 5, 0.1
        while (not self.ws.sock or not self.ws.sock.connected) and time_out >= 0:
            time.sleep(slp)
            time_out -= slp
        if time_out <= 0:
            self.logger.error("Couldn't connect to websocket!")
            self.logNumFatal = "SETUP"
        time_out, slp = 3, 0.05
        while not self.access_token:
            time_out -= slp
            if time_out <= 0:
                self.logger.error("Access_token not received. Reboot.")
                self.logNumFatal = "SETUP"
                return
            time.sleep(slp)
        self.logger.info("access_token received")

    def __subscribe(self):
        channels = list()
        self.subscriptions = list()

        # Orderbook

        for symbol in self.symbol_list:
            ticker = self.Instrument[symbol].ticker
            channel = f"book.{ticker}.none.{self.orderbook_depth}.100ms"
            self.logger.info("ws subscription - Orderbook - channel - " + str(channel))
            channels.append(channel)
        self.subscriptions.append(channels)
        self.__subscribe_channels(
            type="public",
            channels=channels,
            id="subscription",
            callback=self.__update_orderbook,
        )

        # Ticker

        channels = list()
        for symbol in self.symbol_list:
            ticker = self.Instrument[symbol].ticker
            channel = f"ticker.{ticker}.100ms"
            self.logger.info("ws subscription - Ticker - channel - " + str(channel))
            channels.append(channel)
        self.subscriptions.append(channels)
        self.__subscribe_channels(
            type="public",
            channels=channels,
            id="subscription",
            callback=self.__update_ticker,
        )

        # Portfolio

        channels = ["user.portfolio.any"]
        self.logger.info("ws subscription - Portfolio - channel - " + str(channels[0]))
        self.subscriptions.append(channels)
        self.__subscribe_channels(
            type="private",
            channels=channels,
            id="subscription",
            callback=self.__update_portfolio,
        )

        """# Orders

        channels = ["user.orders.any.any.raw"]
        self.logger.info("ws subscription - Orders - channel - " + str(channels[0]))
        self.subscriptions.append(channels)
        self.__subscribe_channels(
            type="private",
            channels=channels,
            id="subscription",
            callback=self.__handle_order,
        )"""

        # User changes (trades, positions, orders)

        channels = ["user.changes.any.any.raw"]
        self.logger.info(
            "ws subscription - User changes - channel - " + str(channels[0])
        )
        self.subscriptions.append(channels)
        self.__subscribe_channels(
            type="private",
            channels=channels,
            id="subscription",
            callback=self.__update_user_changes,
        )

    def __on_message(self, ws, message):
        try:
            message = json.loads(message)
            if "result" in message:
                id = message["id"]
                if "access_token" in message["result"]:
                    self.access_token = message["result"]["access_token"]
                    self.refresh_token = message["result"]["refresh_token"]
                elif id == "subscription":
                    for subscription in self.subscriptions:
                        if set(subscription) <= set(message["result"]):
                            self.subscriptions.remove(subscription)
                elif id == "establish_heartbeat":
                    if message["result"] == "ok":
                        self.logger.info("Heartbeat established.")
                else:
                    if id in self.response:
                        self.response[id]["result"] = message["result"]
            elif "params" in message:
                if message["method"] == "subscription":
                    self.callback_directory[message["params"]["channel"]](
                        values=message["params"]["data"]
                    )
                elif "type" in message["params"]:
                    if message["params"]["type"] == "test_request":
                        self.__heartbeat_response()
            elif "error" in message:
                id = message["id"]
                if id in self.response:
                    self.response[id]["result"] = {"error": message["error"]}
            self.pinging = datetime.now(tz=timezone.utc)
        except Exception as exception:
            display_exception(exception)
            self.logNumFatal = "SETUP"

    def __on_error(self, ws, error):
        """
        We are here if websocket has fatal errors.
        """
        self.logger.error(type(error).__name__ + " " + str(error))
        self.logNumFatal = "SETUP"

    def __on_close(self, *args):
        self.logger.info("Websocke closed.")
        self.logNumFatal = "SETUP"

    def __ws_auth(self) -> None:
        """
        Requests DBT's `public/auth` to
        authenticate the WebSocket Connection.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": 9929,
            "method": "public/auth",
            "params": {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
            },
        }
        self.ws.send(json.dumps(msg))

    def __on_open(self, ws):
        self.__ws_auth()

    def __confirm_subscription(self, action="subscribe"):
        """
        Checks that all subscriptions are successful.
        """
        timeout, slp = 3, 0.05
        while self.subscriptions:
            timeout -= slp
            if timeout <= 0:
                for sub in self.subscriptions:
                    self.logger.error("Failed to " + action + " " + str(sub))
                self.logNumFatal = "SETUP"
                return
            time.sleep(slp)
        self.logger.info("All subscriptions are successful. Continuing.")

    def __subscribe_channels(
        self, type: str, channels: list, id: str, callback: Callable
    ):
        msg = {
            "jsonrpc": "2.0",
            "method": type + "/subscribe",
            "id": id,
            "params": {"channels": channels},
        }
        for channel in channels:
            self.callback_directory[channel] = callback
        self.ws.send(json.dumps(msg))

    def __establish_heartbeat(self) -> None:
        """
        Requests DBT's `public/set_heartbeat` to
        establish a heartbeat connection.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": "establish_heartbeat",
            "method": "public/set_heartbeat",
            "params": {"interval": 10},
        }
        self.ws.send(json.dumps(msg))

    def __heartbeat_response(self) -> None:
        """
        Sends the required WebSocket response to
        the Deribit API Heartbeat message.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": "heartbeat_response",
            "method": "public/test",
            "params": {"interval": self.heartbeat_interval},
        }
        self.ws.send(json.dumps(msg))

    def exit(self):
        """
        Closes websocket
        """
        try:
            self.ws.close()
        except Exception:
            pass
        self.logNumFatal = "SETUP"

    def ping_pong(self):
        if datetime.now(tz=timezone.utc) - self.pinging > timedelta(
            seconds=self.heartbeat_interval + 2
        ):
            self.logger.error("Deribit websocket heartbeat error. Reboot")
            return False
        return True

    def __update_orderbook(self, values: dict) -> None:
        symbol = (self.ticker[values["instrument_name"]], self.name)
        instrument = self.Instrument[symbol]
        instrument.asks = values["asks"]
        instrument.bids = values["bids"]

    def __update_ticker(self, values: dict) -> None:
        symbol = (self.ticker[values["instrument_name"]], self.name)
        instrument = self.Instrument[symbol]
        instrument.volume24h = values["stats"]["volume"]
        if "funding_8h" in values:
            instrument.fundingRate = values["funding_8h"] * 100

    def __update_portfolio(self, values: dict) -> None:
        currency = (values["currency"], self.name)
        account = self.Account[currency]
        account.orderMargin = values["initial_margin"]
        account.positionMagrin = values["maintenance_margin"]
        account.availableMargin = values["available_withdrawal_funds"]
        account.marginBalance = values["available_funds"]
        account.walletBalance = values["balance"]
        account.unrealisedPnl = (
            values["futures_session_upl"] + values["options_session_upl"]
        )

    def __handle_order(self, values: dict) -> None:
        print("_________________________handle order", values)

    def __update_user_changes(self, values: dict) -> None:
        for key, data in values.items():
            if key == "orders":
                for value in data:
                    symbol = (self.ticker[value["instrument_name"]], self.name)
                    side = "Sell" if value["direction"] == "sell" else "Buy"
                    order_state = ""
                    instrument = self.Instrument[symbol]
                    if value["order_state"] == "open":
                        order_state = "New"
                    elif value["order_state"] == "cancelled":
                        order_state = "Canceled"
                    if order_state == "New" and value["replaced"]:
                        order_state = "Replaced"
                    if order_state:
                        row = {
                            "ticker": value["instrument_name"],
                            "category": instrument.category,
                            "leavesQty": value["amount"] - value["filled_amount"],
                            "price": float(value["price"]),
                            "symbol": symbol,
                            "transactTime": service.time_converter(
                                int(value["last_update_timestamp"]) / 1000, usec=True
                            ),
                            "side": side,
                            "orderID": value["order_id"],
                            "execType": order_state,
                            "settlCurrency": instrument.settlCurrency,
                            "orderQty": float(value["amount"]),
                            "cumQty": float(value["filled_amount"]),
                        }
                        if value["label"]:
                            row["clOrdID"] = value["label"]
                        self.transaction(row=row)
            elif key == "positions":
                for value in data:
                    symbol = (
                        self.ticker[value["instrument_name"]],
                        self.name,
                    )
                    instrument = self.Instrument[symbol]
                    if symbol in self.symbol_list:
                        instrument.currentQty = value["size"]
                        instrument.avgEntryPrice = value["average_price"]
                        instrument.unrealisedPnl = value["total_profit_loss"]
                        # instrument.marginCallPrice is not provided
            elif key == "trades":
                for row in data:
                    row["execType"] = "Trade"
                    row["ticker"] = row["instrument_name"]
                    row["symbol"] = (
                        self.ticker[row["instrument_name"]],
                        self.name,
                    )
                    instrument = self.Instrument[row["symbol"]]
                    if instrument.category == "spot":
                        row["settlCurrency"] = (
                            row["fee_currency"],
                            self.name,
                        )
                    else:
                        row["settlCurrency"] = instrument.settlCurrency
                    row["execID"] = str(row["trade_id"]) + "_" + row["settlCurrency"][0]
                    row["orderID"] = row["order_id"] + "_" + row["settlCurrency"][0]
                    row[
                        "leavesQty"
                    ] = 9999999999999  # leavesQty is not supported by Deribit
                    row["execFee"] = row["fee"]
                    if row["direction"] == "sell":
                        row["side"] = "Sell"
                    else:
                        row["side"] = "Buy"
                    if "label" in row:
                        row["clOrdID"] = row["label"]
                    row["category"] = instrument.category
                    row["lastPx"] = row["price"]
                    row["transactTime"] = service.time_converter(
                        time=row["timestamp"] / 1000, usec=True
                    )
                    row["lastQty"] = row["amount"]
                    row["market"] = self.name
                    row["commission"] = "Not supported"
                    self.transaction(row=row)

    def subscribe_symbol(self, symbol: tuple) -> None:
        ticker = self.Instrument[symbol].ticker
        channel = [f"book.{ticker}.none.{self.orderbook_depth}.100ms"]
        self.logger.info("ws subscription - Orderbook - channel - " + str(channel))
        self.subscriptions.append(channel)
        self.__subscribe_channels(
            type="public",
            channels=channel,
            id="subscription",
            callback=self.__update_orderbook,
        )
        channel = [f"ticker.{symbol[0]}.100ms"]
        self.logger.info("ws subscription - Ticker - channel - " + str(channel))
        self.subscriptions.append(channel)
        self.__subscribe_channels(
            type="public",
            channels=channel,
            id="subscription",
            callback=self.__update_ticker,
        )
        self.__confirm_subscription()

    def unsubscribe_symbol(self, symbol: str) -> None:
        msg = {
            "jsonrpc": "2.0",
            "id": "subscription",
            "method": "public/unsubscribe",
            "params": {"channels": None},
        }
        channel = [f"book.{symbol}.none.{self.orderbook_depth}.100ms"]
        self.logger.info("ws unsubscribe - Orderbook - channel - " + str(channel))
        self.subscriptions.append(channel)
        msg["params"]["channels"] = channel
        self.ws.send(json.dumps(msg))
        channel = [f"ticker.{symbol}.100ms"]
        self.logger.info("ws unsubscribe - Ticker - channel - " + str(channel))
        self.subscriptions.append(channel)
        msg["params"]["channels"] = channel
        self.ws.send(json.dumps(msg))
        self.__confirm_subscription(action="unsubscribe")

    def transaction(self, **kwargs):
        """
        This method is replaced by transaction() from functions.py after the
        application is launched.
        """
        pass
