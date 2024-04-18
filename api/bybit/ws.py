import logging

import services as service
from api.init import Setup
from api.variables import Variables
from common.data import MetaAccount, MetaInstrument
from common.variables import Variables as var
from display.functions import info_display
from services import exceptions_manager
import time
from collections import OrderedDict

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
        self.currency_divisor = {
            "USDT": 1,
            "BTC": 1,
            "ETH": 1,
            "EOS": 1,
            "XRP": 1,
            "DOT": 1,
            "ADA": 1,
            "MANA": 1,
            "LTC": 1,
            "SOL": 1,
            "None": 1,
        }
        self.robots = OrderedDict()
        self.frames = dict()
        self.robot_status = dict()
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
            lst = list(filter(lambda x: x[1] == category, self.symbol_list))
            for symbol in lst:
                if category == "linear":
                    print(
                        "_________ws subscription: linear - orderbook_stream -", symbol
                    )
                    self.ws[category].orderbook_stream(
                        depth=self.orderbook_depth,
                        symbol=symbol[0],
                        callback=lambda x: self.__update_orderbook(
                            values=x["data"], category="linear"
                        ),
                    )
                    print("_________ws subscription: linear - ticker_stream -", symbol)
                    self.ws[category].ticker_stream(
                        symbol=symbol[0],
                        callback=lambda x: self.__update_ticker(
                            values=x["data"], category="linear"
                        ),
                    )
                elif category == "inverse":
                    print(
                        "_________ws subscription: inverse - orderbook_stream -", symbol
                    )
                    self.ws[category].orderbook_stream(
                        depth=self.orderbook_depth,
                        symbol=symbol[0],
                        callback=lambda x: self.__update_orderbook(
                            values=x["data"], category="inverse"
                        ),
                    )
                    print("_________ws subscription: inverse - ticker_stream -", symbol)
                    self.ws[category].ticker_stream(
                        symbol=symbol[0],
                        callback=lambda x: self.__update_ticker(
                            values=x["data"], category="inverse"
                        ),
                    )
                elif category == "spot":
                    print("_________ws subscription: spot - orderbook_stream -", symbol)
                    self.ws[category].orderbook_stream(
                        depth=self.orderbook_depth,
                        symbol=symbol[0],
                        callback=lambda x: self.__update_orderbook(
                            values=x["data"], category="spot"
                        ),
                    )
                    print("_________ws subscription: spot - ticker_stream -", symbol)
                    self.ws[category].ticker_stream(
                        symbol=symbol[0],
                        callback=lambda x: self.__update_ticker(
                            values=x["data"], category="spot"
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
        self.ws_private.execution_stream(callback=self.__handle_execution)
        info_display(self.name, "Connected to websocket.")

    def __update_orderbook(self, values: dict, category: tuple) -> None:
        symbol = (values["s"], category, self.name)
        instrument = self.Instrument[symbol]
        if self.depth == "quote":
            instrument.asks[0] = values["a"]
            instrument.bids[0] = values["b"]
        else:
            asks = values["a"]
            bids = values["b"]
            asks = list(map(lambda x: [float(x[0]), float(x[1])], asks))
            bids = list(map(lambda x: [float(x[0]), float(x[1])], bids))
            asks.sort(key=lambda x: x[0])
            bids.sort(key=lambda x: x[0], reverse=True)
            instrument.asks = asks
            instrument.bids = bids

    def __update_ticker(self, values: dict, category: str) -> None:
        self.message_counter += 1
        instrument = self.Instrument[(values["symbol"], category, self.name)]
        instrument.volume24h = float(values["volume24h"])
        if "fundingRate" in values:
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

    def __update_position(self, values: dict) -> None:
        print("_______update_position")
        for value in values["data"]:
            symbol = (value["symbol"], value["category"], self.name)
            if symbol in self.symbol_list:
                instrument = self.Instrument[symbol]
                if value["side"] == "Sell":
                    instrument.currentQty = -float(value["size"])
                else:
                    instrument.currentQty = float(value["size"])
                self.positions[symbol]["POS"] = instrument.currentQty
                instrument.avgEntryPrice = float(value["entryPrice"])
                instrument.marginCallPrice = value["liqPrice"]
                instrument.unrealisedPnl = float(value["unrealisedPnl"])

    def __handle_order(self, values):
        print("_______handle_order")
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
                return
            else:
                orderStatus = ""
            if orderStatus:
                symbol = (value["symbol"], value["category"], self.name)
                row = {
                    "leavesQty": float(value["leavesQty"]),
                    "price": float(value["price"]),
                    "symbol": symbol,
                    "transactTime": service.time_converter(
                        int(value["updatedTime"]) / 1000, usec=True
                    ),
                    "side": value["side"],
                    "orderID": value["orderId"],
                    "execType": orderStatus,
                    "settlCurrency": self.Instrument[symbol].settlCurrency,
                    "orderQty": float(value["qty"]),
                    "cumQty": float(value["cumExecQty"]),
                }
                if value["orderLinkId"]:
                    row["clOrdID"] = value["orderLinkId"]
                self.transaction(row=row)

    def __handle_execution(self, values):
        print("_______handle_execution")
        for row in values["data"]:
            row["symbol"] = (row["symbol"], row["category"], self.name)
            row["execID"] = row["execId"]
            row["orderID"] = row["orderId"]
            row["lastPx"] = float(row["execPrice"])
            row["leavesQty"] = float(row["leavesQty"])
            row["transactTime"] = service.time_converter(
                time=int(row["execTime"]) / 1000, usec=True
            )
            row["commission"] = float(row["execFee"])
            if row["orderLinkId"]:
                row["clOrdID"] = row["orderLinkId"]
            row["price"] = float(row["orderPrice"])
            row["lastQty"] = float(row["execQty"])
            row["settlCurrency"] = self.Instrument[row["symbol"]].settlCurrency
            row["market"] = self.name
            if row["execType"] == "Funding":
                if row["side"] == "Sell":
                    row["lastQty"] = -row["lastQty"]
            self.transaction(row=row)

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
        self.logNumFatal = -1
        self.logger.info("Websocket closed")   

    def transaction(self, **kwargs):
        """
        This method is replaced by transaction() from functions.py after the
        application is launched.
        """
        pass
