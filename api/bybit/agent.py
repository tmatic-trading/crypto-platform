# from api.variables import Variables
import logging
from collections import OrderedDict
from datetime import datetime
from typing import Union

import services as service
from common.variables import Variables as var
from services import exceptions_manager

from .ws import Bybit


@exceptions_manager
class Agent(Bybit):
    logger = logging.getLogger(__name__)

    def get_active_instruments(self):
        for category in self.category_list:
            instrument_info = self.session.get_instruments_info(category=category)
            for instrument in instrument_info["result"]["list"]:
                Agent.fill_instrument(self, instrument=instrument, category=category)
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
        print("___get_user")
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
        print("___get_instrument_data")
        instrument_info = self.session.get_instruments_info(
            symbol=symbol[0], category=symbol[1]
        )
        Agent.fill_instrument(
            self, instrument=instrument_info["result"]["list"][0], category=symbol[1]
        )

    def get_position(self, symbol: tuple = False):
        print("___get_position")

    def trade_bucketed(self):
        print("___trade_bucketed")

    def trading_history(self, histCount: int, time: datetime) -> list:
        print("___trading_history")
        startTime = service.time_converter(time)
        limit = min(100, histCount)
        trade_history = []
        while startTime < service.time_converter(datetime.now()):
            for category in self.category_list:
                cursor = "no"
                while cursor:
                    result = self.session.get_executions(
                        category=category,
                        startTime=startTime,
                        limit=limit,
                        cursor=cursor,
                    )
                    cursor = result["result"]["nextPageCursor"]
                    result = result["result"]["list"]
                    for row in result:
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
                    trade_history += result
            print(
                "Bybit - loading trading history, startTime="
                + str(service.time_converter(startTime / 1000))
                + ", received: "
                + str(len(trade_history))
                + " records."
            )
            if len(trade_history) > histCount:
                break
            startTime += 604800000
        trade_history.sort(key=lambda x: x["transactTime"])

        return trade_history

    def open_orders(self) -> list:
        print("___open_orders")
        myOrders = list()
        for category in self.category_list:
            for settleCoin in self.currencies:
                if settleCoin in self.settlCurrency_list[category]:
                    cursor = "no"
                    while cursor:
                        result = self.session.get_open_orders(
                            category=category,
                            settleCoin=settleCoin,
                            openOnly=0,
                            limit=50,
                            cursor=cursor,
                        )
                        cursor = result["result"]["nextPageCursor"]
                        for order in result["result"]["list"]:
                            order["symbol"] = (order["symbol"], category, self.name)
                            order["orderID"] = order["orderId"]
                            if "orderLinkId" in order and order["orderLinkId"]:
                                order["clOrdID"] = order["orderLinkId"]
                            order["account"] = self.user_id
                            order["orderQty"] = float(order["qty"])
                            order["price"] = float(order["price"])
                            order["settlCurrency"] = (settleCoin, self.name)
                            order["ordType"] = order["orderType"]
                            order["ordStatus"] = order["orderStatus"]
                            order["leavesQty"] = float(order["leavesQty"])
                            order["transactTime"] = service.time_converter(
                                time=int(order["updatedTime"]) / 1000, usec=True
                            )
                        myOrders += result["result"]["list"]

        return myOrders

    def urgent_announcement(self):
        print("___urgent_announcement")
        self.exit()
        self.logNumFatal = 1001

    def place_limit(self, quantity: int, price: float, clOrdID: str, symbol: tuple):
        print("___place_limit")
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
        print("___replace_limit")
        return self.session.amend_order(
            category=symbol[1],
            symbol=symbol[0],
            orderId=orderID,
            qty=str(quantity),
            price=str(price),
        )

    def remove_order(self, order: dict):
        print("___remove_order")
        return self.session.cancel_order(
            category=order["SYMBOL"][1],
            symbol=order["SYMBOL"][0],
            orderId=order["orderID"],
        )

    def get_wallet_balance(self) -> None:
        print("___wallet_balance")
        result = self.session.get_wallet_balance(accountType="UNIFIED")
        for values in result["result"]["list"]:
            if values["accountType"] == "UNIFIED":
                for coin in values["coin"]:
                    settlCurrency = (coin["coin"], self.name)
                    self.Account[settlCurrency].account = self.user_id
                    self.Account[settlCurrency].availableMargin = float(
                        coin["availableToWithdraw"]
                    )
                    self.Account[settlCurrency].commission = 0
                    self.Account[settlCurrency].funding = 0
                    self.Account[settlCurrency].marginBalance = float(coin["equity"])
                    self.Account[settlCurrency].marginLeverage = 0
                    self.Account[settlCurrency].result = 0
                    self.Account[settlCurrency].settlCurrency = settlCurrency
                    self.Account[settlCurrency].sumreal = 0
                break
        else:
            print("UNIFIED account not found")

    def get_position_info(self):
        for category in self.category_list:
            for settlCurrency in self.settlCurrency_list[category]:
                if settlCurrency in self.currencies:
                    cursor = "no"
                    while cursor:
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
                            instrument.currentQty = float(values["size"])
                            instrument.avgEntryPrice = float(values["avgPrice"])
                            instrument.unrealisedPnl = values["unrealisedPnl"]
                            instrument.marginCallPrice = values["liqPrice"]
                            if not instrument.marginCallPrice:
                                instrument.marginCallPrice = "inf"
                            instrument.state = values["positionStatus"]

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
        self.Instrument[symbol].minOrderQty = float(
            instrument["lotSizeFilter"]["minOrderQty"]
        )
        qty = self.Instrument[symbol].minOrderQty
        if float(qty) - int(float(qty)) == 0:
            self.Instrument[symbol].precision = 0
        else:
            self.Instrument[symbol].precision = (
                len(str(float(qty) - int(float(qty))).replace(".", "")) - 1
            )
        self.Instrument[symbol].state = instrument["status"]
        self.Instrument[symbol].multiplier = 1
        self.Instrument[symbol].myMultiplier = 1
        self.Instrument[symbol].fundingRate = 0
        self.Instrument[symbol].volume24h = 0
        self.Instrument[symbol].avgEntryPrice = 0
        self.Instrument[symbol].marginCallPrice = 0
        self.Instrument[symbol].currentQty = 0
        self.Instrument[symbol].unrealisedPnl = 0
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
