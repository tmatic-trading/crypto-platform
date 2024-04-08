import logging
from collections import OrderedDict
from datetime import datetime
from time import sleep

import services as service
from api.init import Setup
from api.variables import Variables
from common.data import MetaAccount, MetaInstrument
from common.variables import Variables as var
from services import exceptions_manager

# from .agent import Agent
from .pybit.unified_trading import HTTP, WebSocket


@exceptions_manager
class Bybit(Variables):
    class Account(metaclass=MetaAccount):
        pass

    class Instrument(metaclass=MetaInstrument):
        pass

    def __init__(self):
        self.name = "Bybit"
        Setup.variables(self, self.name)
        self.session = HTTP(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.testnet,
        )
        self.categories = ["spot", "inverse", "option", "linear"]
        self.settlCurrency_list = {
            "spot": [],
            "inverse": [],
            "option": [],
            "linear": [],
        }
        self.settleCoin_list = list()
        self.ws = {
            "spot": WebSocket,
            "inverse": WebSocket,
            "option": WebSocket,
            "linear": WebSocket,
        }
        self.ws_private = WebSocket
        self.logger = logging.getLogger(__name__)
        if self.depth == "quote":
            self.orderbook_depth = 1
        else:
            self.orderbook_depth = 50
        self.currency_divisor = {"USDT": 1, "BTC": 1}
        print("!!!!!!!!!!!!! BYBIT !!!!!!!!!!!")

    def start(self):
        print("-----starting Bybit----")
        self.count = 0
        self.__connect()

    def __connect(self) -> None:
        """
        Connecting to websocket.
        """
        self.logger.info("Connecting to websocket")
        for category in self.category_list:
            self.ws[category] = WebSocket(testnet=self.testnet, channel_type=category)
            for symbol in self.symbol_list:
                self.ws[category].orderbook_stream(
                    depth=self.orderbook_depth,
                    symbol=symbol[0],
                    callback=lambda x: self.__update_orderbook(
                        values=x["data"], symbol=symbol
                    ),
                )
                self.ws[category].ticker_stream(
                    symbol=symbol[0],
                    callback=lambda x: self.__update_ticker(
                        values=x["data"], category=category
                    ),
                )
        self.ws_private = WebSocket(
            testnet=self.testnet,
            channel_type="private",
            api_key=self.api_key,
            api_secret=self.api_secret,
        )
        self.ws_private.wallet_stream(callback=self.__update_account)
        self.ws_private.position_stream(callback=self.__update_position)
        self.ws_private.order_stream(callback=self.__handle_order)

    def __update_orderbook(self, values: dict, symbol: tuple) -> None:
        if self.depth == "quote":
            self.Instrument[symbol].asks[0] = values["a"]
            self.Instrument[symbol].bids[0] = values["b"]
        else:
            asks = values["a"]
            bids = values["b"]
            asks = list(map(lambda x: [float(x[0]), float(x[1])], asks))
            bids = list(map(lambda x: [float(x[0]), float(x[1])], bids))
            asks.sort(key=lambda x: x[0])
            bids.sort(key=lambda x: x[0], reverse=True)
            self.Instrument[symbol].asks = asks
            self.Instrument[symbol].bids = bids

    def __update_ticker(self, values: dict, category: str) -> None:
        self.message_counter += 1
        instrument = self.Instrument[(values["symbol"], category, self.name)]
        instrument.volume24h = float(values["volume24h"])
        instrument.fundingRate = float(values["fundingRate"])

    def __update_account(self, values: dict) -> None:
        for value in values["data"]:
            if value["accountType"] == "UNIFIED":
                for coin in value["coin"]:
                    if coin["coin"] in self.currencies:
                        settlCurrency = (coin["coin"], self.name)
                        self.Account[settlCurrency].availableMargin = float(
                            coin["availableToWithdraw"]
                        )
                        self.Account[settlCurrency].marginBalance = float(
                            coin["equity"]
                        )
                        print("---------", self.currencies)

    def __update_position(self, values: dict) -> None:
        print("________________update position")
        for value in values["data"]:
            symbol = (value["symbol"], value["category"], self.name)
            if symbol in self.symbol_list:
                instrument = self.Instrument[symbol]
                if value["side"] == "Sell":
                    instrument.currentQty = -float(value["size"])
                else:
                    instrument.currentQty = float(value["size"])
                instrument.avgEntryPrice = float(value["entryPrice"])
                instrument.marginCallPrice = value["liqPrice"]
                instrument.unrealisedPnl = float(value["unrealisedPnl"])

    def __handle_order(self, values):
        print("________________handle order")
        for value in values["data"]:
            if value["orderStatus"] == "Cancelled":
                orderStatus = "Canceled"
            elif value["orderStatus"] == "New":
                for order in var.orders.values():
                    if value["orderId"] == order["orderID"]:
                        orderStatus = "Replaced"
                        break
                else:
                    orderStatus = "New"
            elif value["orderStatus"] == "Rejected":
                self.logger.info(
                    "Rejected order "
                    + value["symbol"]
                    + " "
                    + value["category"]
                    + " orderId "
                    + value["orderId"]
                )
            else:
                orderStatus = ""
            if orderStatus:
                symbol = (value["symbol"], value["category"], self.name)
                val = {
                    "leavesQty": float(value["leavesQty"]),
                    "price": float(value["price"]),
                    "symbol": symbol,
                    "transactTime": service.time_converter(
                        int(value["updatedTime"]) / 1000
                    ),
                    "side": value["side"],
                    "orderID": value["orderId"],
                    "execType": orderStatus,
                    "settlCurrency": (self.Instrument[symbol].settlCurrency, self.name),
                    "orderQty": float(value["qty"]),
                    "cumQty": float(value["cumExecQty"]),
                }
                if value["orderLinkId"]:
                    val["clOrdID"] = value["orderLinkId"]
            self.transaction(row=val)

    def exit(self):
        """
        Closes websocket
        """
        for category in self.category_list:
            try:
                self.ws[category].exit()
            except Exception:
                pass
        try:
            self.ws_private.exit()
        except Exception:
            pass
        self.logger.info("Websocket closed")

    def transaction(self, **kwargs):
        """
        This method is replaced by transaction() from functions.py after the
        application is launched.
        """
        pass
