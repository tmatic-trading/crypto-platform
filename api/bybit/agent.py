import threading
from datetime import datetime, timedelta, timezone
from typing import Union

import services as service
from services import exceptions_manager

from .ws import Bybit


@exceptions_manager
class Agent(Bybit):
    def get_active_instruments(self):
        def get_in_thread(category, success, num):
            cursor = "no"
            while cursor:
                cursor = ""
                self.logger.info(
                    "Sending get_instruments_info() - category - " + category
                )
                result = self.session.get_instruments_info(
                    category=category,
                    limit=1000,
                    cursor=cursor,
                )
                if "nextPageCursor" in result["result"]:
                    cursor = result["result"]["nextPageCursor"]
                else:
                    cursor = ""
                for instrument in result["result"]["list"]:
                    Agent.fill_instrument(
                        self, instrument=instrument, category=category
                    )
                if isinstance(result["result"]["list"], list):
                    success[num] = 0

        threads, success = [], []
        for num, category in enumerate(self.categories):
            success.append(-1)
            t = threading.Thread(target=get_in_thread, args=(category, success, num))
            threads.append(t)
            t.start()
        [thread.join() for thread in threads]
        for number in success:
            if number != 0:
                self.logger.error(
                    "The list was expected when the instruments were loaded, but for some categories it was not received. Reboot."
                )
                return -1

        if self.Instrument.get_keys():
            for symbol in self.symbol_list:
                if symbol not in self.Instrument.get_keys():
                    self.logger.error(
                        "Unknown symbol: "
                        + str(symbol)
                        + ". Check the SYMBOLS in the .env.Bybit file. Perhaps the name of the symbol does not correspond to the category or such symbol does not exist. Reboot."
                    )
                    return -1
        else:
            self.logger.error("There are no entries in the Instrument class.")
            return -1

        return 0

    def get_user(self) -> None:
        """
        Returns the user ID and other useful information about the user and
        places it in self.user. If unsuccessful, logNumFatal is not ''.
        """
        self.logger.info("Sending get_uid_wallet_type()")
        data = self.session.get_uid_wallet_type()
        if isinstance(data, dict):
            self.user = data
            id = find_value_by_key(data=data, key="uid")
            if id:
                self.user_id = id
                return
        self.logNumFatal = "SETUP"
        message = (
            "A user ID was requested from the exchange but was not received. Reboot"
        )
        self.logger.error(message)

    def get_instrument(self, ticker: str, category: str) -> None:
        self.logger.info(
            "Sending get_instruments_info() - symbol - " + ticker + " " + category
        )
        instrument_info = self.session.get_instruments_info(
            symbol=ticker, category=category
        )
        Agent.fill_instrument(
            self, instrument=instrument_info["result"]["list"][0], category=category
        )

    def get_position(self, symbol: tuple = False):
        print("___get_position", symbol)

    def trade_bucketed(
        self, symbol: tuple, start_time: datetime, timeframe: str
    ) -> Union[list, None]:
        self.logger.info(
            "Sending get_kline() - symbol - "
            + str(symbol)
            + " - interval - "
            + str(timeframe)
        )
        instrument = self.Instrument[symbol]
        kline = self.session.get_kline(
            category=instrument.category,
            symbol=instrument.ticker,
            interval=str(timeframe),
            start=service.time_converter(time=start_time),
            limit=1000,
        )
        if kline["result"]["list"]:
            res = []
            for row in kline["result"]["list"]:
                res.append(
                    {
                        "timestamp": service.time_converter(int(row[0]) / 1000),
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                    }
                )
            res.sort(key=lambda x: x["timestamp"])

            return res

    def trading_history(self, histCount: int, start_time=None) -> list:
        if start_time:
            trade_history = []
            utc = datetime.now(timezone.utc)
            if utc - start_time > timedelta(days=729):
                self.logger.info(
                    "Bybit only allows you to query trading history for the last 2 years. Check the history.ini file."
                )
                start_time = utc - timedelta(days=729)
                self.logger.info("Time changed to " + str(start_time))
            startTime = service.time_converter(start_time)
            limit = min(100, histCount)

            def get_in_thread(category, startTime, limit, success, num):
                nonlocal trade_history
                cursor = "no"
                while cursor:
                    self.logger.info(
                        "Sending get_executions() - category - "
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
                    if isinstance(result["result"]["list"], list):
                        for row in res:
                            if (row["symbol"], category) not in self.ticker:
                                Agent.get_instrument(
                                    self,
                                    ticker=row["symbol"],
                                    category=category,
                                )
                            row["ticker"] = (row["symbol"],)
                            row["symbol"] = (
                                self.ticker[(row["symbol"], category)],
                                self.name,
                            )
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
                            row["price"] = float(row["orderPrice"])
                            if category == "spot":
                                row["settlCurrency"] = (row["feeCurrency"], self.name)
                            else:
                                row["settlCurrency"] = self.Instrument[
                                    row["symbol"]
                                ].settlCurrency
                            row["lastQty"] = float(row["execQty"])
                            row["market"] = self.name
                            if row["execType"] == "Funding":
                                if row["side"] == "Sell":
                                    row["lastQty"] = -row["lastQty"]
                            row["execFee"] = float(row["execFee"])
                        trade_history += res
                        success[num] = "success"

                    else:
                        self.logger.error(
                            "The list was expected when the trading history were loaded, but for the category "
                            + category
                            + " it was not received. Reboot."
                        )
                        return

        while startTime < service.time_converter(datetime.now(tz=timezone.utc)):
            threads, success = [], []
            for category in self.categories:
                success.append(None)
                t = threading.Thread(
                    target=get_in_thread,
                    args=(category, startTime, limit, success, len(success) - 1),
                )
                threads.append(t)
                t.start()
            [thread.join() for thread in threads]
            for s in success:
                if not s:
                    return
            message = (
                "Bybit - loading trading history, startTime="
                + str(service.time_converter(startTime / 1000))
                + ", received: "
                + str(len(trade_history))
                + " records."
            )
            self.logger.info(message)
            if len(trade_history) > histCount:
                break
            startTime += 604800000  # +7 days
        trade_history.sort(key=lambda x: x["transactTime"])

        return trade_history

    def open_orders(self) -> int:
        myOrders = list()
        base = {"openOnly": 0, "limit": 50}

        def request_open_orders(parameters: dict):
            nonlocal myOrders
            cursor = "no"
            parameters["cursor"] = cursor
            success = parameters["success"]
            num = parameters["num"]
            parameters.pop("success")
            parameters.pop("num")
            while cursor:
                self.logger.info(
                    "Sending open_orders() - parameters - " + str(parameters)
                )
                result = self.session.get_open_orders(**parameters)
                cursor = result["result"]["nextPageCursor"]
                parameters["cursor"] = result["result"]["nextPageCursor"]
                for order in result["result"]["list"]:
                    order["symbol"] = (
                        self.ticker[(order["symbol"], parameters["category"])],
                        self.name,
                    )
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
                if isinstance(result["result"]["list"], list):
                    success[num] = 0

        def get_in_thread(**parameters):
            request_open_orders(parameters)

        threads, success = [], []
        for category in self.categories:
            if category == "spot":
                success.append(-1)
                parameters = base.copy()
                parameters["category"] = category
                t = threading.Thread(
                    target=lambda par=parameters: get_in_thread(
                        **par, success=success, num=len(success) - 1
                    )
                )
                threads.append(t)
                t.start()
            else:
                for settleCoin in self.currencies:
                    if settleCoin in self.settlCurrency_list[category]:
                        success.append(-1)
                        parameters = base.copy()
                        parameters["category"] = category
                        parameters["settleCoin"] = settleCoin
                        t = threading.Thread(
                            target=lambda par=parameters: get_in_thread(
                                **par, success=success, num=len(success) - 1
                            )
                        )
                        threads.append(t)
                        t.start()
        [thread.join() for thread in threads]
        for number in success:
            if number != 0:
                self.logger.error(
                    "The list was expected when the orders were loaded, but for some categories it was not received. Reboot"
                )
                return -1
        self.setup_orders = myOrders

        return 0

    def place_limit(self, quantity: float, price: float, clOrdID: str, symbol: tuple):
        side = "Buy" if quantity > 0 else "Sell"
        instrument = self.Instrument[symbol]
        return self.session.place_order(
            category=instrument.category,
            symbol=instrument.ticker,
            side=side,
            orderType="Limit",
            qty=str(abs(quantity)),
            price=str(price),
            orderLinkId=clOrdID,
        )

    def replace_limit(self, quantity: float, price: float, orderID: str, symbol: tuple):
        instrument = self.Instrument[symbol]
        return self.session.amend_order(
            category=instrument.category,
            symbol=instrument.ticker,
            orderId=orderID,
            qty=str(quantity),
            price=str(price),
        )

    def remove_order(self, order: dict):
        return self.session.cancel_order(
            category=self.Instrument[order["SYMBOL"]].category,
            symbol=order["SYMBOL"][0],
            orderId=order["orderID"],
        )

    def get_wallet_balance(self) -> None:
        for account_type in self.account_types:
            self.logger.info(
                "Sending get_wallet_balance() - accountType - " + account_type
            )
            data = self.session.get_wallet_balance(accountType=account_type)
            for values in data["result"]["list"]:
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
                    # self.Account[currency].commission = 0
                    # self.Account[currency].funding = 0
                    # self.Account[currency].result = 0
                    account.settlCurrency = currency
                    # self.Account[currency].sumreal = 0
                break

    def get_position_info(self):
        def get_in_thread(category, settlCurrency, success, num):
            cursor = "no"
            while cursor:
                self.logger.info(
                    "Sending get_positions() - category - "
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
                    symbol = (self.ticker[(values["symbol"], category)], self.name)
                    instrument = self.Instrument[symbol]
                    if symbol in self.positions:
                        self.positions[symbol]["POS"] = float(values["size"])
                        if values["side"] == "Sell":
                            self.positions[symbol]["POS"] = -self.positions[symbol][
                                "POS"
                            ]
                    instrument.currentQty = float(values["size"])
                    if values["side"] == "Sell":
                        instrument.currentQty = -instrument.currentQty
                    instrument.avgEntryPrice = float(values["avgPrice"])
                    instrument.unrealisedPnl = values["unrealisedPnl"]
                    instrument.marginCallPrice = values["liqPrice"]
                    if not instrument.marginCallPrice:
                        instrument.marginCallPrice = "inf"
                    instrument.state = values["positionStatus"]
                if isinstance(result["result"]["list"], list):
                    success[num] = 0

        threads, success = [], []
        for category in self.categories:
            for settlCurrency in self.settlCurrency_list[category]:
                if settlCurrency in self.currencies:
                    success.append(-1)
                    t = threading.Thread(
                        target=get_in_thread,
                        args=(category, settlCurrency, success, len(success) - 1),
                    )
                    threads.append(t)
                    t.start()
        [thread.join() for thread in threads]
        for number in success:
            if number != 0:
                self.logger.error(
                    "The list was expected when the positions were loaded, but for some categories and settlCurrency it was not received. Reboot"
                )
                self.logNumFatal = "SETUP"

    def fill_instrument(self, instrument: dict, category: str):
        """
        Filling the instruments data.

        The data is stored in the Instrument class using MetaInstrument class.
        The data fields of different exchanges are unified through the
        Instrument class. See detailed description of the fields there.
        """
        if category == "spot":
            symb = instrument["baseCoin"] + "/" + instrument["quoteCoin"]
        else:
            symb = instrument["symbol"]
        symbol = (symb, self.name)
        self.ticker[(instrument["symbol"], category)] = symb
        self.Instrument[symbol].category = category
        self.Instrument[symbol].symbol = symb
        self.Instrument[symbol].ticker = instrument["symbol"]
        self.Instrument[symbol].baseCoin = instrument["baseCoin"]
        self.Instrument[symbol].quoteCoin = instrument["quoteCoin"]
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
        self.Instrument[symbol].valueOfOneContract = 1


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
