import json
import os
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
from services import exceptions_manager


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
        self.symbol_category = dict()
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
            self.orderbook_depth = 50
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
            if self.logNumFatal < 1004:
                self.logNumFatal = 1004
        time_out, slp = 3, 0.05
        while not self.access_token:
            time_out -= slp
            if time_out <= 0:
                self.logger.error("Access_token not received. Reboot.")
                self.logNumFatal = -1
                return
            time.sleep(slp)
        self.logger.info("access_token received")
        print("______________________ access_token received", self.access_token)

    def __subscribe(self):
        channels = list()
        self.subscriptions = set()

        # Orderbook

        if self.depth == "orderBook":
            depth = 10
        else:
            depth = 1
        for symbol in self.symbol_list:
            channel = f"book.{symbol[0]}.none.{depth}.100ms"
            self.logger.info("ws subscription - Orderbook - channel - " + str(channel))
            channels.append(channel)
        self.subscriptions.add(str(channels))
        self.__subscribe_channels(
            type="public",
            channels=channels,
            id="subscription",
            callback=self.__update_orderbook,
        )

        # Ticker

        channels = list()
        for symbol in self.symbol_list:
            channel = f"ticker.{symbol[0]}.100ms"
            self.logger.info("ws subscription - Ticker - channel - " + str(channel))
            channels.append(channel)
        self.subscriptions.add(str(channels))
        self.__subscribe_channels(
            type="public",
            channels=channels,
            id="subscription",
            callback=self.__update_ticker,
        )

        # Portfolio

        channels = ["user.portfolio.any"]
        self.logger.info("ws subscription - Portfolio - channel - " + str(channels[0]))
        self.subscriptions.add(str(channels))
        self.__subscribe_channels(
            type="private",
            channels=channels,
            id="subscription",
            callback=self.__update_portfolio,
        )

        # Orders

        channels = ["user.orders.any.any.raw"]
        self.logger.info("ws subscription - Orders - channel - " + str(channels[0]))
        self.subscriptions.add(str(channels))
        self.__subscribe_channels(
            type="private",
            channels=channels,
            id="subscription",
            callback=self.__handle_order,
        )

        # User changes (trades, positions, orders)

        channels = ["user.changes.any.any.raw"]
        self.logger.info(
            "ws subscription - User changes - channel - " + str(channels[0])
        )
        self.subscriptions.add(str(channels))
        self.__subscribe_channels(
            type="private",
            channels=channels,
            id="subscription",
            callback=self.__update_user_changes,
        )

    def __on_message(self, ws, message):
        message = json.loads(message)
        #print("_________________________________________________________________________________message", message)
        if "result" in message:
            id = message["id"]
            if "access_token" in message["result"]:
                self.access_token = message["result"]["access_token"]
                self.refresh_token = message["result"]["refresh_token"]
            elif id == "subscription":
                self.subscriptions.remove(str(message["result"]))
            elif id == "establish_heartbeat":
                if message["result"] == "ok":
                    self.logger.info("Heartbeat established.")
            elif id == "heartbeat_response":
                self.pinging = service.time_converter(
                    time=message["usOut"] / 1000000, usec=True
                )
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

    def __on_error(self, ws, error):
        """
        We are here if websocket has fatal errors.
        """
        self.logger.error(type(error).__name__ + " " + str(error))
        if self.logNumFatal < 1010:
            self.logNumFatal = 1010

    def __on_close(self, *args):
        self.logger.info("Websocke closed.")
        self.logNumFatal = -1

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

    def __confirm_subscription(self):
        """
        Checks that all subscriptions are successful.
        """
        timeout, slp = 3, 0.05
        while self.subscriptions:
            timeout -= slp
            if timeout <= 0:
                for sub in self.subscriptions:
                    self.logger.error("Failed to subscribe " + str(sub))
                self.logNumFatal = -1
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
        print("_____________heart")
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
        self.logNumFatal = -1

    def ping_pong(self):
        if datetime.now(tz=timezone.utc) - self.pinging > timedelta(
            seconds=self.heartbeat_interval + 3
        ):
            self.logger.error("Deribit websocket heartbeat error. Reboot")
            return False
        return True

    def __update_orderbook(self, values: dict) -> None:
        category = self.symbol_category[values["instrument_name"]]
        symbol = (values["instrument_name"], category, self.name)
        instrument = self.Instrument[symbol]
        instrument.asks = values["asks"]
        instrument.bids = values["bids"]
        # print("_________________________update orderbook", values)

    def __update_ticker(self, values: dict) -> None:
        category = self.symbol_category[values["instrument_name"]]
        symbol = (values["instrument_name"], category, self.name)
        instrument = self.Instrument[symbol]
        instrument.volume24h = values["stats"]["volume"]
        if "funding_8h" in values:
            instrument.fundingRate = values["funding_8h"] * 100
        # print("______________ user ticker", values)

    def __update_portfolio(self, values: dict) -> None:
        account = self.Account[values["currency"]]
        account.orderMargin = values["initial_margin"]
        account.positionMagrin = values["maintenance_margin"]
        account.availableMargin = values["available_withdrawal_funds"]
        account.marginBalance = values["available_funds"]
        account.walletBalance = values["balance"]
        account.unrealisedPnl = (
            values["futures_session_upl"] + values["options_session_upl"]
        )
        """print(values["currency"])
        print(
            "_________________________maintenance_margin", values["maintenance_margin"]
        )
        print("_________________________initial_margin", values["initial_margin"])
        print(
            "_________________________projected_maintenance_margin",
            values["projected_maintenance_margin"],
        )
        print(
            "_________________________projected_initial_margin",
            values["projected_initial_margin"],
        )
        print("_________________________margin_balance", values["margin_balance"])"""

    def __handle_order(self, values: dict) -> None:
        print("_________________________handle order", values)

    def __update_user_changes(self, values: dict) -> None:
        print("______________ user changes", values)
        for key, value in values.items():
            print("_________________", key)
            print(value)
