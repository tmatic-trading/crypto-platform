# from api.variables import Variables
import logging
from datetime import datetime, timedelta, timezone
from typing import Union
import threading

import services as service
from services import exceptions_manager

from .ws import Bybit


@exceptions_manager
class Agent(Bybit):
    logger = logging.getLogger(__name__)
    def get_active_instruments(self):
        def get_in_thread(category):
            cursor = "no"
            while cursor:
                cursor = ""
                Agent.logger.info(
                    "In get_active_instruments - sending get_instruments_info() "
                    + "- category - "
                    + category
                )
                result = self.session.get_instruments_info(
                    category=category, limit=1000,
                    cursor=cursor,
                )
                if "nextPageCursor" in result["result"]:                    
                    cursor = result["result"]["nextPageCursor"]
                else:
                    cursor = ""
                for instrument in result["result"]["list"]:
                    Agent.fill_instrument(self, instrument=instrument, category=category)
        threads = []
        for category in self.categories:
            t = threading.Thread(target=get_in_thread, args=(category,))
            threads.append(t)
            t.start()
        [thread.join() for thread in threads]
        for symbol in self.symbol_list:
            if symbol not in self.symbols:
                Agent.logger.error(
                    "Unknown symbol: "
                    + str(symbol)
                    + ". Check the SYMBOLS in the .env.Bitmex file. Perhaps "
                    + "such symbol does not exist"
                )
                Bybit.exit(self)
                exit(1)

    def get_user(self) -> Union[dict, None]:
        Agent.logger.info("In get_user - sending get_uid_wallet_type()")
        result = self.session.get_uid_wallet_type()
        self.user = result
        id = find_value_by_key(data=result, key="uid")
        if id:
            self.user_id = id
        else:
            self.logNumFatal = 10001
            message = (
                "A user ID was requested from the exchange but was not " + "received."
            )
            Agent.logger.error(message)

    def get_instrument(self, symbol: tuple) -> None:
        Agent.logger.info(
            "In get_instrument - sending get_instruments_info() - symbol - "
            + str(symbol)
        )
        instrument_info = self.session.get_instruments_info(
            symbol=symbol[0], category=symbol[1]
        )
        Agent.fill_instrument(
            self, instrument=instrument_info["result"]["list"][0], category=symbol[1]
        )

    def get_position(self, symbol: tuple = False):
        print("___get_position", symbol)

    def trade_bucketed(
        self, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, None]:
        Agent.logger.info(
            "In trade_bucketed - sending get_kline() - symbol - "
            + str(symbol)
            + " - interval - "
            + str(timeframe)
        )
        kline = self.session.get_kline(
            category=symbol[1],
            symbol=symbol[0],
            interval=str(timeframe),
            start=service.time_converter(time=time),
            limit=1000,
        )
        if kline["result"]["list"]:
            result = []
            for row in kline["result"]["list"]:
                result.append(
                    {
                        "timestamp": service.time_converter(int(row[0]) / 1000),
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                    }
                )

            return result

    def trading_history(self, histCount: int, time: datetime) -> list:
        utc = datetime.now(timezone.utc)
        if utc - time > timedelta(days=729):
            self.logger.info(
                "Bybit only allows you to query trading history for the last "
                + "2 years. Check the History.ini file."
            )
            time = utc - timedelta(days=729)
            self.logger.info("Time changed to " + str(time))
        startTime = service.time_converter(time)
        limit = min(100, histCount)
        trade_history = []
        while startTime < service.time_converter(datetime.now(tz=timezone.utc)):
            for category in self.categories:
                cursor = "no"
                while cursor:
                    Agent.logger.info(
                        "In trading_history - sending get_executions() - category - "
                        + category
                        + " - startTime - "
                        + str(service.time_converter(startTime / 1000))
                    )
                    result = self.session.get_executions(
                        category=category,
                        startTime=startTime,
                        limit=limit,
                        cursor=cursor,
                    )
                    cursor = result["result"]["nextPageCursor"]
                    res = result["result"]["list"]
                    for row in res:
                        row["symbol"] = (row["symbol"], category, self.name)
                        row["execID"] = row["execId"]
                        row["orderID"] = row["orderId"]
                        row["category"] = category
                        row["lastPx"] = float(row["execPrice"])
                        row["leavesQty"] = float(row["leavesQty"])
                        row["transactTime"] = service.time_converter(
                            time=int(row["execTime"]) / 1000, usec=True
                        )
                        row["commission"] = float(row["feeRate"])
                        if row["orderLinkId"]:
                            row["clOrdID"] = row["orderLinkId"]
                        row["price"] = float(row["execPrice"])
                        row["lastQty"] = float(row["execQty"])
                        row["settlCurrency"] = self.Instrument[
                            row["symbol"]
                        ].settlCurrency
                        row["market"] = self.name
                        if row["execType"] == "Funding":
                            if row["side"] == "Sell":
                                row["lastQty"] = -row["lastQty"]
                    trade_history += res
            print(
                "Bybit - loading trading history, startTime="
                + str(service.time_converter(startTime / 1000))
                + ", received: "
                + str(len(trade_history))
                + " records."
            )
            if len(trade_history) > histCount:
                break
            startTime += 604800000  # +7 days
        trade_history.sort(key=lambda x: x["transactTime"])

        return trade_history

    def open_orders(self) -> list:
        myOrders = list()
        base = {"openOnly": 0, "limit": 50}

        def request_open_orders(myOrders: list, parameters: dict):
            cursor = "no"
            parameters["cursor"] = cursor
            while cursor:
                Agent.logger.info(
                    "In open_orders - sending open_orders() - parameters - "
                    + str(parameters)
                )
                result = self.session.get_open_orders(**parameters)
                cursor = result["result"]["nextPageCursor"]
                parameters["cursor"] = result["result"]["nextPageCursor"]
                for order in result["result"]["list"]:
                    order["symbol"] = (order["symbol"], category, self.name)
                    order["orderID"] = order["orderId"]
                    if "orderLinkId" in order and order["orderLinkId"]:
                        order["clOrdID"] = order["orderLinkId"]
                    order["account"] = self.user_id
                    order["orderQty"] = float(order["qty"])
                    order["price"] = float(order["price"])
                    if "settlCurrency" in parameters:
                        order["settlCurrency"] = (
                            parameters["settlCurrency"],
                            self.name,
                        )
                    order["ordType"] = order["orderType"]
                    order["ordStatus"] = order["orderStatus"]
                    order["leavesQty"] = float(order["leavesQty"])
                    order["transactTime"] = service.time_converter(
                        time=int(order["updatedTime"]) / 1000, usec=True
                    )
                myOrders += result["result"]["list"]

            return myOrders

        for category in self.categories:
            if category == "spot":
                parameters = base.copy()
                parameters["category"] = category
                myOrders = request_open_orders(myOrders=myOrders, parameters=parameters)
            else:
                for settleCoin in self.currencies:
                    if settleCoin in self.settlCurrency_list[category]:
                        parameters = base.copy()
                        parameters["category"] = category
                        parameters["settleCoin"] = settleCoin
                        myOrders = request_open_orders(
                            myOrders=myOrders, parameters=parameters
                        )

        return myOrders

    def urgent_announcement(self):
        print("___urgent_announcement")
        self.exit()
        self.logNumFatal = 1001

    def place_limit(self, quantity: int, price: float, clOrdID: str, symbol: tuple):
        side = "Buy" if quantity > 0 else "Sell"
        return self.session.place_order(
            category=symbol[1],
            symbol=symbol[0],
            side=side,
            orderType="Limit",
            qty=str(abs(quantity)),
            price=str(price),
            orderLinkId=clOrdID,
        )

    def replace_limit(self, quantity: int, price: float, orderID: str, symbol: tuple):
        return self.session.amend_order(
            category=symbol[1],
            symbol=symbol[0],
            orderId=orderID,
            qty=str(quantity),
            price=str(price),
        )

    def remove_order(self, order: dict):
        return self.session.cancel_order(
            category=order["SYMBOL"][1],
            symbol=order["SYMBOL"][0],
            orderId=order["orderID"],
        )

    def get_wallet_balance(self) -> None:
        for account_type in self.account_types:
            Agent.logger.info(
                "In get_wallet_balance - sending get_wallet_balance() - accountType - "
                + account_type
            )
            result = self.session.get_wallet_balance(accountType=account_type)
            for values in result["result"]["list"]:
                for coin in values["coin"]:
                    currency = (coin["coin"] + "." + values["accountType"], self.name)
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
                    account.account = self.user_id
                    self.Account[currency].commission = 0
                    self.Account[currency].funding = 0
                    self.Account[currency].result = 0
                    self.Account[currency].settlCurrency = currency
                    self.Account[currency].sumreal = 0
                break

    def get_position_info(self):
        def get_in_thread(category, settlCurrency):
            cursor = "no"
            while cursor:
                Agent.logger.info(
                    "In get_position_info - sending get_positions() - category - "
                    + category
                    + " - settlCurrency - "
                    + settlCurrency
                )
                result = self.session.get_positions(
                    category=category,
                    settleCoin=settlCurrency,
                    limit=200,
                    cursor=cursor,
                )
                cursor = result["result"]["nextPageCursor"]
                for values in result["result"]["list"]:
                    symbol = (values["symbol"], category, self.name)
                    instrument = self.Instrument[symbol]
                    if symbol in self.positions:
                        self.positions[symbol]["POS"] = float(values["size"])
                        if values["side"] == "Sell":
                            self.positions[symbol]["POS"] = -self.positions[
                                symbol
                            ]["POS"]
                    instrument.currentQty = float(values["size"])
                    if values["side"] == "Sell":
                        instrument.currentQty = -instrument.currentQty
                    instrument.avgEntryPrice = float(values["avgPrice"])
                    instrument.unrealisedPnl = values["unrealisedPnl"]
                    instrument.marginCallPrice = values["liqPrice"]
                    if not instrument.marginCallPrice:
                        instrument.marginCallPrice = "inf"
                    instrument.state = values["positionStatus"]

        threads = []            
        for category in self.category_list:
            for settlCurrency in self.settlCurrency_list[category]:
                if settlCurrency in self.currencies:
                    t = threading.Thread(target=get_in_thread, args=(category,settlCurrency))
                    threads.append(t)
                    t.start()
        [thread.join() for thread in threads]

    def fill_instrument(self, instrument: dict, category: str):
        symbol = (instrument["symbol"], category, self.name)
        self.symbols.add(symbol)
        self.Instrument[symbol].category = category
        self.Instrument[symbol].symbol = instrument["symbol"]
        if "settleCoin" in instrument:
            self.Instrument[symbol].settlCurrency = (
                instrument["settleCoin"],
                self.name,
            )
            if instrument["settleCoin"] not in self.settlCurrency_list[category]:
                self.settlCurrency_list[category].append(instrument["settleCoin"])
            if instrument["settleCoin"] not in self.settleCoin_list:
                self.settleCoin_list.append(instrument["settleCoin"])
        else:
            self.Instrument[symbol].settlCurrency = (
                "None",
                self.name,
            )
        if "deliveryTime" in instrument:
            if int(instrument["deliveryTime"]):
                self.Instrument[symbol].expire = service.time_converter(
                    int(instrument["deliveryTime"]) / 1000
                )
            else:
                self.Instrument[symbol].expire = "Perpetual"
        else:
            self.Instrument[symbol].expire = "None"
        self.Instrument[symbol].tickSize = float(instrument["priceFilter"]["tickSize"])
        self.Instrument[symbol].price_precision = service.precision(
            number=self.Instrument[symbol].tickSize
        )
        self.Instrument[symbol].minOrderQty = float(
            instrument["lotSizeFilter"]["minOrderQty"]
        )
        if category == "spot":
            self.Instrument[symbol].qtyStep = float(
                instrument["lotSizeFilter"]["basePrecision"]
            )
        else:
            self.Instrument[symbol].qtyStep = float(
                instrument["lotSizeFilter"]["qtyStep"]
            )
        self.Instrument[symbol].precision = service.precision(
            number=self.Instrument[symbol].qtyStep
        )
        self.Instrument[symbol].state = instrument["status"]
        self.Instrument[symbol].multiplier = 1
        self.Instrument[symbol].myMultiplier = 1
        if category == "spot":
            self.Instrument[symbol].fundingRate = "None"
            self.Instrument[symbol].avgEntryPrice = "None"
            self.Instrument[symbol].marginCallPrice = "None"
            self.Instrument[symbol].currentQty = "None"
            self.Instrument[symbol].unrealisedPnl = "None"
        if category == "option":
            self.Instrument[symbol].fundingRate = "None"
        self.Instrument[symbol].asks = [[0, 0]]
        self.Instrument[symbol].bids = [[0, 0]]


def find_value_by_key(data: dict, key: str) -> Union[str, None]:
    for k, val in data.items():
        if k == key:
            return val
        elif isinstance(val, dict):
            res = find_value_by_key(val, key)
            if res:
                return res
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    res = find_value_by_key(item, key)
                    if res:
                        return res
