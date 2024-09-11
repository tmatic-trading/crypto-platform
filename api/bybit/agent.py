import sys
import threading
from datetime import datetime, timedelta, timezone
from typing import Union

import services as service
from api.bybit.erruni import Unify
from api.errors import Error
from display.messages import ErrorMessage

from .ws import Bybit


class Agent(Bybit):
    def get_active_instruments(self) -> str:
        """
        Instruments are requested in threads according to categories.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type.
        """

        def get_in_thread(category, success, num):
            cursor = "no"
            while cursor:
                cursor = ""
                try:
                    result = self.session.get_instruments_info(
                        category=category,
                        limit=1000,
                        cursor=cursor,
                    )
                except Exception as exception:
                    error = Unify.error_handler(
                        self,
                        exception=exception,
                        verb="GET",
                        path="get_instruments_info",
                    )
                    success[num] = error
                    return

                if "nextPageCursor" in result["result"]:
                    cursor = result["result"]["nextPageCursor"]
                else:
                    cursor = ""
                for instrument in result["result"]["list"]:
                    Agent.fill_instrument(
                        self, instrument=instrument, category=category
                    )
                if isinstance(result["result"]["list"], list):
                    success[num] = ""  # success

        threads, success = [], []
        for num, category in enumerate(self.categories):
            success.append("FATAL")
            t = threading.Thread(target=get_in_thread, args=(category, success, num))
            threads.append(t)
            t.start()
        [thread.join() for thread in threads]
        for error in success:
            if error:
                if error == "FATAL":
                    self.logger.error(
                        "The list was expected when the instruments were loaded, "
                        + "but for some categories it was not received. Reboot."
                    )
                return error

        self.symbol_list = service.check_symbol_list(
            symbols=self.Instrument.get_keys(),
            market=self.name,
            symbol_list=self.symbol_list,
        )

        return ""

    def get_user(self) -> str:
        """
        Returns the user ID and other useful information about the user and
        places it in self.user.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type.
        """
        try:
            res = self.session.get_uid_wallet_type()
            if isinstance(res, dict):
                id = find_value_by_key(data=res, key="uid")
                if id:
                    self.user_id = id
                    self.user = res
                    return ""
                else:
                    self.logger.error(ErrorMessage.USER_ID_NOT_FOUND)
                    return "FATAL"
            elif not isinstance(res, str):
                res = "FATAL"
            self.logger.error(ErrorMessage.USER_ID_NOT_RECEIVED)

            return res

        except Exception as exception:
            Unify.error_handler(
                self,
                exception=exception,
                verb="GET",
                path="get_uid_wallet_type",
            )
            self.logger.error(ErrorMessage.USER_ID_NOT_RECEIVED)

            if self.logNumFatal:
                return self.logNumFatal
            else:
                return "FATAL"

    def get_instrument(self, ticker: str, category: str) -> None:
        try:
            instrument = self.session.get_instruments_info(
                symbol=ticker, category=category
            )
        except Exception as exception:
            Unify.error_handler(
                self,
                exception=exception,
                verb="GET",
                path="get_instruments_info",
            )
            return

        if isinstance(instrument["result"]["list"], list):
            Agent.fill_instrument(
                self, instrument=instrument["result"]["list"][0], category=category
            )
        else:
            self.logger.error(
                "The list was expected when the instrument "
                + ticker
                + " is loaded, but was not received. Reboot."
            )
            self.logNumFatal = "FATAL"

    def get_position(self, symbol: tuple = False):
        print("___get_position", symbol)

    def trade_bucketed(
        self, symbol: tuple, start_time: datetime, timeframe: str
    ) -> Union[list, None]:
        instrument = self.Instrument[symbol]
        try:
            kline = self.session.get_kline(
                category=instrument.category,
                symbol=instrument.ticker,
                interval=str(timeframe),
                start=service.time_converter(time=start_time),
                limit=1000,
            )
        except Exception as exception:
            Unify.error_handler(
                self,
                exception=exception,
                verb="GET",
                path="get_kline",
            )
            return

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
                    "Bybit only allows you to query trading history for the last 2 years."
                )
                start_time = utc - timedelta(days=729)
                self.logger.info("Time changed to " + str(start_time))
            startTime = service.time_converter(start_time)
            limit = min(100, histCount)

            def get_in_thread(category, startTime, limit, success, num):
                nonlocal trade_history
                cursor = "no"
                while cursor:
                    try:
                        data = self.session.get_executions(
                            category=category,
                            startTime=startTime,
                            limit=limit,
                            cursor=cursor,
                        )
                    except Exception as exception:
                        error = Unify.error_handler(
                            self,
                            exception=exception,
                            verb="GET",
                            path="get_executions",
                        )
                        success[num] = error
                        return

                    cursor = data["result"]["nextPageCursor"]
                    res = data["result"]["list"]
                    if isinstance(data["result"]["list"], list):
                        for row in res:
                            if (row["symbol"], category) not in self.ticker:
                                self.logger.info(
                                    self.name
                                    + " - Requesting instrument - ticker="
                                    + row["symbol"]
                                    + ", category="
                                    + category
                                )
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
                        success[num] = ""  # success

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
                success.append("FATAL")
                t = threading.Thread(
                    target=get_in_thread,
                    args=(category, startTime, limit, success, len(success) - 1),
                )
                threads.append(t)
                t.start()
            [thread.join() for thread in threads]
            for error in success:
                if error:
                    self.logNumFatal = error
                    return
            if len(trade_history) > histCount:
                break
            startTime += 604800000  # +7 days
        trade_history.sort(key=lambda x: x["transactTime"])

        return trade_history

    def open_orders(self) -> int:
        """
        Open orders are requested in threads according to categories.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type.
        """
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
                try:
                    res = self.session.get_open_orders(**parameters)
                except Exception as exception:
                    error = Unify.error_handler(
                        self, exception=exception, verb="GET", path="get_open_orders"
                    )
                    success[num] = error
                    return

                cursor = res["result"]["nextPageCursor"]
                parameters["cursor"] = res["result"]["nextPageCursor"]
                for order in res["result"]["list"]:
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
                    if order["symbol"] not in self.symbol_list:
                        self.symbol_list.append(order["symbol"])
                myOrders += res["result"]["list"]
                if isinstance(res["result"]["list"], list):
                    success[num] = ""  # success

        def get_in_thread(**parameters):
            request_open_orders(parameters)

        threads, success = [], []
        for category in self.categories:
            if category == "spot":
                success.append("FATAL")
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
                        success.append("FATAL")
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
        for error in success:
            if error:
                if error == "FATAL":
                    self.logger.error(
                        "The list was expected when the orders were loaded, "
                        + "but for some categories it was not received."
                    )
                return error
        self.setup_orders = myOrders

        return ""

    def place_limit(
        self, quantity: float, price: float, clOrdID: str, symbol: tuple
    ) -> Union[str, None]:
        side = "Buy" if quantity > 0 else "Sell"
        instrument = self.Instrument[symbol]
        try:
            return self.session.place_order(
                category=instrument.category,
                symbol=instrument.ticker,
                side=side,
                orderType="Limit",
                qty=str(abs(quantity)),
                price=str(price),
                orderLinkId=clOrdID,
            )
        except Exception as exception:
            error = Unify.error_handler(
                self, exception=exception, verb="POST", path="place_order"
            )

            return error

    def replace_limit(
        self, quantity: float, price: float, orderID: str, symbol: tuple
    ) -> Union[str, None]:
        instrument = self.Instrument[symbol]
        try:
            return self.session.amend_order(
                category=instrument.category,
                symbol=instrument.ticker,
                orderId=orderID,
                qty=str(quantity),
                price=str(price),
            )
        except Exception as exception:
            error = Unify.error_handler(
                self, exception=exception, verb="PUT", path="amend_order"
            )

            return error

    def remove_order(self, order: dict):
        try:
            return self.session.cancel_order(
                category=self.Instrument[order["symbol"]].category,
                symbol=order["symbol"][0],
                orderId=order["orderID"],
            )
        except Exception as exception:
            error = Unify.error_handler(
                self, exception=exception, verb="POST", path="cancel_order"
            )

            return error

    def get_wallet_balance(self) -> None:
        """
        Requests wallet balance usually for two types of accounts: UNIFIED,
        CONTRACT.
        """
        for account_type in self.account_types:
            try:
                data = self.session.get_wallet_balance(accountType=account_type)
            except Exception as exception:
                Unify.error_handler(
                    self, exception=exception, verb="GET", path="get_wallet_balance"
                )
                return

            # Bybit bug patch 20/08/2024 on request accountType = "CONTRACT"
            if "list" in data["result"]:
                data = data["result"]["list"]
            else:
                data = data["result"]["result"]["list"]
            for values in data:
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
                try:
                    res = self.session.get_positions(
                        category=category,
                        settleCoin=settlCurrency,
                        limit=200,
                        cursor=cursor,
                    )
                except Exception as exception:
                    Unify.error_handler(
                        self, exception=exception, verb="GET", path="get_positions"
                    )
                    return

                cursor = res["result"]["nextPageCursor"]
                for values in res["result"]["list"]:
                    symbol = (self.ticker[(values["symbol"], category)], self.name)
                    instrument = self.Instrument[symbol]
                    instrument.currentQty = float(values["size"])
                    if values["side"] == "Sell":
                        instrument.currentQty = -instrument.currentQty
                    instrument.avgEntryPrice = float(values["avgPrice"])
                    instrument.unrealisedPnl = values["unrealisedPnl"]
                    instrument.marginCallPrice = values["liqPrice"]
                    if not instrument.marginCallPrice:
                        instrument.marginCallPrice = "inf"
                if isinstance(res["result"]["list"], list):
                    success[num] = ""  # success

        threads, success = [], []
        for category in self.categories:
            for settlCurrency in self.settlCurrency_list[category]:
                if settlCurrency in self.currencies:
                    success.append("FATAL")
                    t = threading.Thread(
                        target=get_in_thread,
                        args=(category, settlCurrency, success, len(success) - 1),
                    )
                    threads.append(t)
                    t.start()
        [thread.join() for thread in threads]
        for error in success:
            if error:
                if error == "FATAL":
                    self.logger.error(
                        "The list was expected when the positions were loaded, "
                        + "but for some categories and settlCurrency it was not "
                        + "received. Reboot"
                    )

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
        self.Instrument[symbol].market = self.name
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
        if instrument["status"] == "Trading":
            self.Instrument[symbol].state = "Open"
        else:
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

    def activate_funding_thread(self):
        """
        Not used for Bybit.
        """
        pass


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
