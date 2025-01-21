import json
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Callable

import requests
import websocket

import services as service
from api.deribit.error import ErrorStatus
from api.errors import Error
from api.init import Setup
from api.variables import Variables
from common.data import MetaAccount, MetaInstrument, MetaResult
from common.variables import Variables as var
from display.messages import Message
from services import display_exception

from .api_auth import API_auth
from .error import DeribitWsRequestError


class Deribit(Variables):
    class Account(metaclass=MetaAccount):
        pass

    class Instrument(metaclass=MetaInstrument):
        pass

    class Result(metaclass=MetaResult):
        pass

    def __init__(self):
        self.object = Deribit
        self.name = "Deribit"
        self.api_version = "/api/v2/"
        Setup.variables(self)
        self.session = requests.Session()
        self.define_category = {
            "future_linear": "future_linear",
            "future_reversed": "future_reversed",
            "future_combo_reversed": "future_combo_rev",
            "spot_linear": "spot_linear",
            "option_linear": "option_linear",
            "option_reversed": "option_reversed",
            "option_combo_reversed": "option_combo_rev",
        }
        self.timefrs = OrderedDict(
            [
                (1, 1),
                (3, 3),
                (5, 5),
                (10, 10),
                (15, 15),
                (30, 30),
                (60, 60),
                (120, 120),
                (180, 180),
                (360, 360),
                (720, 720),
                (1440, "1D"),
            ]
        )
        self.ws = websocket
        self.logger = var.logger
        self.klines = dict()
        self.setup_orders = list()
        self.account_disp = ""
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
        self.funding_thread_active = True
        self.instrument_index = OrderedDict()
        self.subscriptions = list()
        self.sequence = 0
        self.api_auth = API_auth
        self.get_error = ErrorStatus

    def setup_session(self):
        """
        Not used in Deribit.
        """
        pass

    def start_ws(self):
        self.logger.info("Connecting to websocket")
        time_out, slp = 5, 0.1
        websocket.setdefaulttimeout(time_out)
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

        # Waits for connection established.

        while (not self.ws.sock or not self.ws.sock.connected) and time_out >= 0:
            time.sleep(slp)
            time_out -= slp
        if time_out <= 0:
            self.logger.error("Couldn't connect to websocket!")
            return service.unexpected_error(self)

        self.logger.info("Connected to websocket.")
        time_out, slp = 3, 0.05
        while not self.access_token:
            time_out -= slp
            if time_out <= 0 or self.logNumFatal == "CANCEL":
                self.logger.error("Access_token not received. Reboot.")
                return service.unexpected_error(self)
            time.sleep(slp)
        self.logger.info("access_token received")

        return ""

    def setup_streams(self) -> str:
        if var.order_book_depth == "quote":
            self.orderbook_depth = 1
        else:
            self.orderbook_depth = 10
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
        if not self.logNumFatal:
            self.__establish_heartbeat()
            self.__subscribe()
            res = self._confirm_subscription()
            if not res:
                self.logger.info("All subscriptions are successful. Continuing.")
        else:
            return self.logNumFatal

        return ""

    def __subscribe(self):
        self.subscriptions = list()

        # Orderbook and Ticker

        self._subscribe_symbols(symbol_list=self.symbol_list)

        # Portfolio

        channels = ["user.portfolio.any"]
        self.logger.info("ws subscription - Portfolio - channel - " + str(channels[0]))
        self.__subscribe_channels(
            type="private",
            channels=channels,
            id="subscription",
            callback=self.__update_portfolio,
        )

        """# Orders

        channels = ["user.orders.any.any.raw"]
        self.logger.info("ws subscription - Orders - channel - " + str(channels[0]))
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
        self.__subscribe_channels(
            type="private",
            channels=channels,
            id="subscription",
            callback=self.__update_user_changes,
        )

    def _subscribe_symbols(self, symbol_list: list) -> None:
        """
        Orderbook and ticker subscription. Called at boot or reboot time or
        via the Instruments menu, the options series subscribes to all
        available put and call strikes.
        """
        channels = list()
        for symbol in symbol_list:
            instrument = self.Instrument[symbol]
            ticker = instrument.ticker
            if ticker != "option!":
                channel = f"book.{ticker}.none.{self.orderbook_depth}.100ms"
                channels.append(channel)
            else:
                lst = service.select_option_strikes(
                    index=self.instrument_index, instrument=instrument
                )
                for option in lst:
                    channel = f"book.{option}.none.{self.orderbook_depth}.100ms"
                    channels.append(channel)
        message = Message.WEBSOCKET_SUBSCRIPTION.format(
            NAME="Orderbook", CHANNEL=str(channels)
        )
        self._put_message(message=message)
        self.__subscribe_channels(
            type="public",
            channels=channels,
            id="subscription",
            callback=self.__update_orderbook,
        )

        # Ticker

        channels = list()
        for symbol in symbol_list:
            instrument = self.Instrument[symbol]
            ticker = instrument.ticker
            if ticker != "option!":
                channel = f"ticker.{ticker}.100ms"
                channels.append(channel)
            else:
                lst = service.select_option_strikes(
                    index=self.instrument_index, instrument=instrument
                )
                for option in lst:
                    channel = f"ticker.{option}.100ms"
                    channels.append(channel)
        message = Message.WEBSOCKET_SUBSCRIPTION.format(
            NAME="Ticker", CHANNEL=str(channels)
        )
        self._put_message(message=message)
        self.__subscribe_channels(
            type="public",
            channels=channels,
            id="subscription",
            callback=self.__update_ticker,
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
                res = {"error": message["error"]}
                if "id" in message:
                    if message["id"] in self.response:
                        self.response[message["id"]]["result"] = res
                    else:
                        Error.handler(
                            self,
                            exception=DeribitWsRequestError(response=res),
                            response=res,
                            verb="request via ws",
                            path="",
                        )
                else:
                    Error.handler(
                        self,
                        exception=DeribitWsRequestError(response=res),
                        response=res,
                        verb="request via ws",
                        path="",
                    )
            self.pinging = datetime.now(tz=timezone.utc)
        except Exception as exception:
            display_exception(exception)
            service.unexpected_error(self)

    def __on_error(self, ws, error):
        """
        We are here if websocket has fatal errors.
        """
        self.logger.error(type(error).__name__ + " " + str(error))
        service.unexpected_error(self)

    def __on_close(self, *args):
        self.logger.info("Websocket closed.")
        service.unexpected_error(self)

    def __ws_auth(self) -> None:
        """
        Requests DBT's `public/auth` to
        authenticate the WebSocket Connection.
        """
        sig = API_auth.generate_headers(
            api_key=self.api_key,
            api_secret=self.api_secret,
            method="",
            url="",
            path="_ws_signature",
        )
        msg = {
            "jsonrpc": "2.0",
            "id": 9929,
            "method": "public/auth",
            "params": {
                "grant_type": "client_signature",
                "client_id": sig["id"],
                "timestamp": sig["ts"],
                "nonce": sig["nonce"],
                "data": "",
                "signature": sig["signature"],
            },
        }
        self.ws.send(json.dumps(msg))

    def __on_open(self, ws):
        self.__ws_auth()

    def _confirm_subscription(self, action="subscribe"):
        """
        Checks that all subscriptions are successful.
        """
        timeout, slp = var.timeout, 0.05
        while self.subscriptions:
            timeout -= slp
            if timeout <= 0:  # or not self.api_is_active:
                for sub in self.subscriptions:
                    self.logger.error("Failed to " + action + " " + str(sub))
                return "timeout"
            time.sleep(slp)

        return ""

    def __subscribe_channels(
        self, type: str, channels: list, id: str, callback: Callable
    ) -> None:
        """
        Subscription in parts when the number of channels exceeds 250
        """
        length, step = len(channels), 250
        for num in range(0, length, step):
            part = channels[num : num + step]
            self.subscriptions.append(part)
            msg = {
                "jsonrpc": "2.0",
                "method": type + "/subscribe",
                "id": id,
                "params": {"channels": part},
            }
            for channel in part:
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
        self.api_is_active = False
        self.funding_thread_active = False

    def __update_orderbook(self, values: dict) -> None:
        symbol = (self.ticker[values["instrument_name"]], self.name)
        instrument = self.Instrument[symbol]
        instrument.asks = values["asks"]
        instrument.bids = values["bids"]
        if symbol in self.klines:
            service.kline_hi_lo_values(self, symbol=symbol, instrument=instrument)

    def __update_ticker(self, values: dict) -> None:
        symbol = (self.ticker[values["instrument_name"]], self.name)
        instrument = self.Instrument[symbol]
        instrument.volume24h = values["stats"]["volume"]
        if "funding_8h" in values:
            instrument.fundingRate = values["funding_8h"] * 100
        if "open_interest" in values:
            instrument.openInterest = values["open_interest"]
        if "option" in instrument.category:
            instrument.delta = values["greeks"]["delta"]
            instrument.vega = values["greeks"]["vega"]
            instrument.theta = values["greeks"]["theta"]
            instrument.gamma = values["greeks"]["gamma"]
            instrument.rho = values["greeks"]["rho"]
            instrument.bidIv = values["bid_iv"]
            instrument.askIv = values["ask_iv"]
        instrument.bidPrice = values["best_bid_price"]
        instrument.askPrice = values["best_ask_price"]
        instrument.bidSize = values["best_bid_amount"]
        instrument.askSize = values["best_ask_amount"]
        instrument.markPrice = values["mark_price"]
        instrument.state = values["state"]
        if values["state"] == "open":
            instrument.state = "Open"

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
        if "orders" in values:
            for value in values["orders"]:
                symbol = (self.ticker[value["instrument_name"]], self.name)
                side = "Sell" if value["direction"] == "sell" else "Buy"
                order_state = ""
                instrument = self.Instrument[symbol]
                response_id = ""
                if value["order_state"] == "open":
                    order_state = "New"
                    response_id = "private/" + value["direction"] + "_" + value["label"]
                elif value["order_state"] == "cancelled":
                    order_state = "Canceled"
                    response_id = "private/cancel_" + value["order_id"]
                elif value["order_state"] == "filled":
                    if value["replaced"]:
                        order_state = "Replaced"
                        response_id = "private/edit_" + value["order_id"]
                    else:
                        order_state = "New"
                        response_id = (
                            "private/" + value["direction"] + "_" + value["label"]
                        )
                        # value["filled_amount"] = 0
                if order_state == "New" and value["replaced"]:
                    order_state = "Replaced"
                    response_id = "private/edit_" + value["order_id"]
                if response_id in self.response:
                    self.response[response_id]["result"] = value
                if order_state:
                    """
                    '
                    '
                    Deribit does not have a leavesQty field, so in the case of replace
                    this field is ignored. The ability to change volume is not provided
                    by Tmatic. When processing the application in the orders_processing
                    function, leavesQty = None is taken into account.
                    """
                    if order_state == "Replaced":
                        leavesQty = None
                    else:
                        leavesQty = value["amount"]
                    """
                    '
                    '
                    """
                    row = {
                        "ticker": value["instrument_name"],
                        "category": instrument.category,
                        "leavesQty": leavesQty,  # value["amount"] - value["filled_amount"],
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
        if "trades" in values:
            for row in values["trades"]:
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
                row["orderID"] = row["order_id"]
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
        if "positions" in values:
            for value in values["positions"]:
                symbol = (
                    self.ticker[value["instrument_name"]],
                    self.name,
                )
                instrument = self.Instrument[symbol]
                if instrument.category == "future_linear":
                    instrument.currentQty = value["size_currency"]
                else:
                    instrument.currentQty = value["size"]
                instrument.avgEntryPrice = service.set_number(
                    instrument=instrument, number=value["average_price"]
                )
                instrument.unrealisedPnl = service.set_number(
                    instrument=instrument, number=value["total_profit_loss"]
                )
                # instrument.marginCallPrice is not provided

    def ping_pong(self):
        if datetime.now(tz=timezone.utc) - self.pinging > timedelta(
            seconds=self.heartbeat_interval + 2
        ):
            self.logger.error("Deribit websocket heartbeat error. Reboot")
            return False
        return True

    def subscribe_symbol(self, symbol: tuple, timeout=None) -> None:
        """
        Called when using the Instruments menu or while initial loading if an
        instrument is not subscribed, but unclosed positions are found for it.
        """
        self._subscribe_symbols(symbol_list=[symbol])

        return self._confirm_subscription()

    def unsubscribe_symbol(self, symbol: tuple) -> None:
        msg = {
            "jsonrpc": "2.0",
            "id": "subscription",
            "method": "public/unsubscribe",
            "params": {"channels": None},
        }
        channels = list()
        instrument = self.Instrument[symbol]
        ticker = instrument.ticker
        if ticker != "option!":
            channel = f"book.{ticker}.none.{self.orderbook_depth}.100ms"
            channels.append(channel)
            channel = f"ticker.{ticker}.100ms"
            channels.append(channel)
        else:
            lst = service.select_option_strikes(
                index=self.instrument_index, instrument=instrument
            )
            for option in lst:
                channel = f"book.{option}.none.{self.orderbook_depth}.100ms"
                channels.append(channel)
                channel = f"ticker.{option}.100ms"
                channels.append(channel)
        msg["params"]["channels"] = channels
        self.subscriptions.append(channels)
        message = Message.WEBSOCKET_UNSUBSCRIBE.format(
            NAME="Orderbook, Ticker", CHANNEL=channels
        )
        self._put_message(message=message)
        self.ws.send(json.dumps(msg))
        res = self._confirm_subscription(action="unsubscribe")
        if not res:
            for channel in channels:
                if channel in self.callback_directory:
                    del self.callback_directory[channel]
                else:
                    print("____channel not found", ticker, channel)

        return res

    def transaction(self, **kwargs):
        """
        This method is replaced by transaction() from functions.py after the
        application is launched.
        """
        pass

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
            var.logger.info(self.name + " - " + message)
        elif warning == "warning":
            var.logger.warning(self.name + " - " + message)
        else:
            var.logger.error(self.name + " - " + message)
