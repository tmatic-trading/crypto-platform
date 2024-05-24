import logging
import threading
from collections import OrderedDict

import services as service
from api.init import Setup
from api.variables import Variables
from common.data import MetaAccount, MetaInstrument, MetaResult
from common.variables import Variables as var
from services import exceptions_manager

from .pybit.unified_trading import HTTP, WebSocket


@exceptions_manager
class Bybit(Variables):
    class Account(metaclass=MetaAccount):
        pass

    class Instrument(metaclass=MetaInstrument):
        pass

    class Result(metaclass=MetaResult):
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
        self.account_types = ["UNIFIED", "CONTRACT"]
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
        self.setup_orders = list()
        self.setup_frames = None
        self.account_disp = ""
        self.orders = dict()

    def start(self):
        for symbol in self.symbol_list:
            instrument = self.Instrument[symbol]
            if instrument.category == "linear":
                self.Result[(instrument.quoteCoin, self.name)]
            elif instrument.category == "inverse":
                self.Result[(instrument.baseCoin, self.name)]
            elif instrument.category == "spot":
                self.Result[(instrument.baseCoin, self.name)]
                self.Result[(instrument.quoteCoin, self.name)]
        self.__connect()

    def __connect(self) -> None:
        """
        Connecting to websocket.
        """
        self.logger.info("Connecting to websocket")

        def subscribe_in_thread(category):
            lst = list(filter(lambda x: x[1] == category, self.symbol_list))
            if lst:
                self.ws[category] = WebSocket(
                    testnet=self.testnet, channel_type=category
                )
            for symbol in lst:
                if category == "linear":
                    self.logger.info(
                        "ws subscription - orderbook_stream - category - "
                        + category
                        + " - symbol - "
                        + str(symbol)
                    )
                    self.ws[category].orderbook_stream(
                        depth=self.orderbook_depth,
                        symbol=symbol[0],
                        callback=lambda x: self.__update_orderbook(
                            values=x["data"], category="linear"
                        ),
                    )
                    self.logger.info(
                        "ws subscription - ticker_stream - category - "
                        + category
                        + " - symbol - "
                        + str(symbol)
                    )
                    self.ws[category].ticker_stream(
                        symbol=symbol[0],
                        callback=lambda x: self.__update_ticker(
                            values=x["data"], category="linear"
                        ),
                    )
                elif category == "inverse":
                    self.logger.info(
                        "ws subscription - orderbook_stream - category - "
                        + category
                        + " - symbol - "
                        + str(symbol)
                    )
                    self.ws[category].orderbook_stream(
                        depth=self.orderbook_depth,
                        symbol=symbol[0],
                        callback=lambda x: self.__update_orderbook(
                            values=x["data"], category="inverse"
                        ),
                    )
                    self.logger.info(
                        "ws subscription - ticker_stream - category - "
                        + category
                        + " - symbol - "
                        + str(symbol)
                    )
                    self.ws[category].ticker_stream(
                        symbol=symbol[0],
                        callback=lambda x: self.__update_ticker(
                            values=x["data"], category="inverse"
                        ),
                    )
                elif category == "spot":
                    self.logger.info(
                        "ws subscription - orderbook_stream - category - "
                        + category
                        + " - symbol - "
                        + str(symbol)
                    )
                    self.ws[category].orderbook_stream(
                        depth=self.orderbook_depth,
                        symbol=symbol[0],
                        callback=lambda x: self.__update_orderbook(
                            values=x["data"], category="spot"
                        ),
                    )
                    self.logger.info(
                        "ws subscription - ticker_stream - category - "
                        + category
                        + " - symbol - "
                        + str(symbol)
                    )
                    self.ws[category].ticker_stream(
                        symbol=symbol[0],
                        callback=lambda x: self.__update_ticker(
                            values=x["data"], category="spot"
                        ),
                    )
                elif category == "option":
                    self.logger.info(
                        "ws subscription - orderbook_stream - category - "
                        + category
                        + " - symbol - "
                        + str(symbol)
                    )
                    self.ws[category].orderbook_stream(
                        depth=self.orderbook_depth,
                        symbol=symbol[0],
                        callback=lambda x: self.__update_orderbook(
                            values=x["data"], category="option"
                        ),
                    )
                    self.logger.info(
                        "ws subscription - ticker_stream - category -"
                        + category
                        + " - symbol - "
                        + str(symbol)
                    )
                    self.ws[category].ticker_stream(
                        symbol=symbol[0],
                        callback=lambda x: self.__update_ticker(
                            values=x["data"], category="option"
                        ),
                    )

        def private_in_thread():
            self.ws_private = WebSocket(
                testnet=self.testnet,
                channel_type="private",
                api_key=self.api_key,
                api_secret=self.api_secret,
            )

        threads = []
        for category in self.categories:
            t = threading.Thread(target=subscribe_in_thread, args=(category,))
            threads.append(t)
            t.start()
        t = threading.Thread(target=private_in_thread)
        threads.append(t)
        t.start()
        [thread.join() for thread in threads]
        self.ws_private.wallet_stream(callback=self.__update_account)
        self.ws_private.position_stream(callback=self.__update_position)
        self.ws_private.order_stream(callback=self.__handle_order)
        self.ws_private.execution_stream(callback=self.__handle_execution)

    def __update_orderbook(self, values: dict, category: tuple) -> None:
        symbol = (values["s"], category, self.name)
        instrument = self.Instrument[symbol]
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
            instrument.fundingRate = float(values["fundingRate"]) * 100

    def __update_account(self, values: dict) -> None:
        for value in values["data"]:
            for coin in value["coin"]:
                if coin["coin"] in self.currencies:
                    currency = (coin["coin"] + "." + value["accountType"], self.name)
                    account = self.Account[currency]
                    total = 0
                    check = 0
                    if "locked" in coin:
                        if coin["locked"] != "":
                            total += float(coin["locked"])
                            check += 1
                    if "totalOrderIM" in coin:
                        total += float(coin["totalOrderIM"])
                        check += 1
                    if check:
                        account.orderMargin = total
                    if "totalPositionIM" in coin:
                        account.positionMagrin = float(coin["totalPositionIM"])
                    if "availableToWithdraw" in coin:
                        account.availableMargin = float(coin["availableToWithdraw"])
                    if "equity" in coin:
                        account.marginBalance = float(coin["equity"])
                    if "walletBalance" in coin:
                        account.walletBalance = float(coin["walletBalance"])
                    if "unrealisedPnl" in coin:
                        account.unrealisedPnl = float(coin["unrealisedPnl"])

    def __update_position(self, values: dict) -> None:
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
                if value["liqPrice"] == "":
                    if instrument.currentQty == 0:
                        instrument.marginCallPrice = 0
                    else:
                        instrument.marginCallPrice = "inf"
                else:
                    instrument.marginCallPrice = value["liqPrice"]
                instrument.unrealisedPnl = value["unrealisedPnl"]

    def __handle_order(self, values):
        for value in values["data"]:
            if value["orderStatus"] == "Cancelled":
                orderStatus = "Canceled"
            elif value["orderStatus"] == "New":
                for order in self.orders.values():
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
        for row in values["data"]:
            row["symbol"] = (row["symbol"], row["category"], self.name)
            instrument = self.Instrument[row["symbol"]]
            row["execID"] = row["execId"]
            row["orderID"] = row["orderId"]
            row["lastPx"] = float(row["execPrice"])
            row["leavesQty"] = float(row["leavesQty"])
            row["transactTime"] = service.time_converter(
                time=int(row["execTime"]) / 1000, usec=True
            )
            row["commission"] = float(row["feeRate"])
            if row["orderLinkId"]:
                row["clOrdID"] = row["orderLinkId"]
            row["price"] = float(row["orderPrice"])
            row["market"] = self.name
            row["lastQty"] = float(row["execQty"])
            if row["execType"] == "Funding":
                if row["side"] == "Sell":
                    row["lastQty"] = -row["lastQty"]
            row["execFee"] = float(row["execFee"])
            if row["category"] == "spot":
                if row["commission"] > 0:
                    if row["side"] == "Buy":
                        row["feeCurrency"] = instrument.baseCoin
                    elif row["side"] == "Sell":
                        row["feeCurrency"] = instrument.quoteCoin
                else:
                    if row["IsMaker"]:
                        if row["side"] == "Buy":
                            row["feeCurrency"] = instrument.quoteCoin
                        elif row["side"] == "Sell":
                            row["feeCurrency"] = instrument.baseCoin
                    elif not row["IsMaker"]:
                        if row["side"] == "Buy":
                            row["feeCurrency"] = instrument.baseCoin
                        elif row["side"] == "Sell":
                            row["feeCurrency"] = instrument.quoteCoin
                row["settlCurrency"] = (row["feeCurrency"], self.name)
            else:
                row["settlCurrency"] = instrument.settlCurrency
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
        self.logger.info(self.name + " - Websocket closed")

    def transaction(self, **kwargs):
        """
        This method is replaced by transaction() from functions.py after the
        application is launched.
        """
        pass


    def ping_pong(self):
        pass
