import json
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

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
            time.sleep(100)

            self.__subscribe()

            self.__confirm_subscription()
            time.sleep(10)
            os.abort()

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

        # Orderbook

        if self.depth == "orderBook":
            depth = 10
        else:
            depth = 1
        for symbol in self.symbol_list:
            self.logger.info("ws subscription - orderbook" + " - " + str(symbol))
            channel = f"book.{symbol[0]}.none.{depth}.100ms"
            channels.append(channel)
        self.__subscribe_public(channels=channels, id="subscription")
        self.subscriptions = set()
        self.subscriptions.add(str(channels))

    def __on_message(self, ws, message):
        message = json.loads(message)
        print("______message", message)
        if "result" in message:
            print(type(message["result"]))
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
        elif "params" in message:
            if message["params"]["type"] == "test_request":
                self.__heartbeat_response()

            print("______________params")

        """if "id" in message:
            self.response[message["id"]] = message["result"]"""

    def __on_error(self, ws, error):
        """
        We are here if websocket has fatal errors.
        """
        self.logger.error(type(error).__name__ + " " + str(error))
        if self.logNumFatal < 1010:
            self.logNumFatal = 1010

    def __on_close(self, ws):
        self.logger.info("Websocke closed.")
        self.logNumFatal = -1  # Reboot
        print("close")

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

    def __subscribe_public(self, channels: list, id: str):
        msg = {
            "jsonrpc": "2.0",
            "method": "public/subscribe",
            "id": id,
            "params": {"channels": channels},
        }
        self.ws.send(json.dumps(msg))

    def __subscribe_private(self) -> None:
        pass

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
