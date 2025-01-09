import sys
import threading
from datetime import datetime, timedelta, timezone
from typing import Union

import services as service
from api.bybit.erruni import Unify
from api.errors import Error
from common.variables import Variables as var
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
                if cursor == "no":
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
                for values in result["result"]["list"]:
                    Agent.fill_instrument(self, values=values, category=category)
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
                self.logger.error(
                    "The list was expected when the instruments were loaded, "
                    + "but for some categories it was not received."
                )
                return error

        self.symbol_list = service.check_symbol_list(
            ws=self,
            symbols=self.Instrument.get_keys(),
            market=self.name,
            symbol_list=self.symbol_list,
        )
        self.instrument_index = service.sort_instrument_index(
            index=self.instrument_index
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
            error = Unify.error_handler(
                self,
                exception=exception,
                verb="GET",
                path="get_uid_wallet_type",
            )
            self.logger.error(ErrorMessage.USER_ID_NOT_RECEIVED)

            return error

    def get_instrument(self, ticker: str, category: str) -> str:
        """
        Gets a specific instrument by symbol. Fills the
        self.Instrument[<symbol>] array with data.

        Returns
        -------
        str
            On success, "" is returned.
        """
        try:
            instrument = self.session.get_instruments_info(
                symbol=ticker, category=category
            )
        except Exception as exception:
            error = Unify.error_handler(
                self,
                exception=exception,
                verb="GET",
                path="get_instruments_info",
            )
            return error

        if instrument["result"]["list"]:
            Agent.fill_instrument(
                self, values=instrument["result"]["list"][0], category=category
            )

            return ""

        else:
            message = ErrorMessage.INSTRUMENT_NOT_FOUND.format(
                PATH="get_instruments_info", TICKER=ticker, CATEGORY=category
            )
            self.logger.warning(message)

            return message

    def get_position(self, symbol: tuple = False):
        print("___get_position", symbol)

    def trade_bucketed(
        self, symbol: tuple, start_time: datetime, timeframe: str
    ) -> Union[list, str]:
        """
        Gets timeframe data. Available time intervals: 1, 3, 5, 15, 30, 60,
        120, 240, 360, 720, D, M, W.

        Returns
        -------
        str | None
            On success, list is returned, otherwise None.
        """
        instrument = self.Instrument[symbol]
        interval = self.timefrs[timeframe]
        try:
            kline = self.session.get_kline(
                category=instrument.category,
                symbol=instrument.ticker,
                interval=str(interval),
                start=service.time_converter(time=start_time),
                limit=1000,
            )
        except Exception as exception:
            error = Unify.error_handler(
                self,
                exception=exception,
                verb="GET",
                path="get_kline",
            )
            return error

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

        else:
            message = ErrorMessage.REQUEST_EMPTY.format(PATH="get_kline")
            self.logger.error(message)
            var.queue_info.put(
                {
                    "market": self.name,
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": "error",
                }
            )
            return service.unexpected_error(self)

    def trading_history(self, histCount: int, start_time: datetime) -> Union[dict, str]:
        """
        Gets trades, funding and delivery from the exchange for the period starting
        from start_time.

        Returns
        -------
        list | str
            On success, list is returned, otherwise error type.
        """
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
                self.logger.info(
                    "Requesting trading history - category - "
                    + category
                    + " - startTime - "
                    + str(service.time_converter(startTime / 1000))
                )
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
                        elif row["execType"] == "Settle":
                            row["execType"] = "Delivery"
                        row["execFee"] = float(row["execFee"])
                    trade_history += res
                    success[num] = ""  # success

                else:
                    self.logger.error(
                        "The list was expected when the trading history were loaded, but for the category "
                        + category
                        + " it was not received."
                    )
                    return service.unexpected_error(self)

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
                    return error
            self.logger.info(
                "Trading history data, received: "
                + str(len(trade_history))
                + " records."
            )
            if len(trade_history) > histCount:
                break
            startTime += 604800000  # +7 days
        trade_history.sort(key=lambda x: x["transactTime"])

        return {"data": trade_history, "length": len(trade_history)}

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
                    order["settlCurrency"] = self.Instrument[
                        order["symbol"]
                    ].settlCurrency
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
            if category == "linear":
                for settleCoin in self.settlCurrency_list[category]:
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
            else:
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
        [thread.join() for thread in threads]
        for error in success:
            if error:
                self.logger.error(
                    "The list was expected when the orders were loaded, "
                    + "but for some categories it was not received."
                )
                return error
        self.setup_orders = myOrders

        return ""

    def place_limit(
        self, quantity: float, price: float, clOrdID: str, symbol: tuple
    ) -> Union[dict, str]:
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
        self,
        leavesQty: float,
        price: float,
        orderID: str,
        symbol: tuple,
        orderQty: float,
    ) -> Union[dict, str]:
        instrument = self.Instrument[symbol]
        try:
            return self.session.amend_order(
                category=instrument.category,
                symbol=instrument.ticker,
                orderId=orderID,
                qty=str(leavesQty),
                price=str(price),
            )
        except Exception as exception:
            error = Unify.error_handler(
                self, exception=exception, verb="PUT", path="amend_order"
            )

            return error

    def remove_order(self, order: dict) -> Union[dict, str]:
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

    def get_wallet_balance(self) -> str:
        """
        Requests wallet balance usually for two types of accounts: UNIFIED,
        CONTRACT.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type.
        """
        for account_type in self.account_types:
            try:
                res = self.session.get_wallet_balance(accountType=account_type)
            except Exception as exception:
                error = Unify.error_handler(
                    self, exception=exception, verb="GET", path="get_wallet_balance"
                )
                return error

            # Bybit bug patch 20/08/2024 on request accountType = "CONTRACT"
            if "list" in res["result"]:
                res = res["result"]["list"]
            else:
                res = res["result"]["result"]["list"]

            for values in res:
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
                    if "availableToWithdraw" in coin and coin["availableToWithdraw"]:
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

        return ""

    def get_position_info(self):
        """
        Gets current positions in parallel threads, each category and
        currency in its own thread.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type.
        """

        def get_in_thread(category, settlCurrency, success, num):
            cursor = "no"
            while cursor:
                try:
                    parameters = {"category": category, "limit": 200, "cursor": cursor}
                    if category == "linear":
                        parameters["settleCoin"] = settlCurrency
                    res = self.session.get_positions(**parameters)
                except Exception as exception:
                    error = Unify.error_handler(
                        self, exception=exception, verb="GET", path="get_positions"
                    )
                    success[num] = error
                    return

                cursor = res["result"]["nextPageCursor"]
                for values in res["result"]["list"]:
                    symbol = (self.ticker[(values["symbol"], category)], self.name)
                    instrument = self.Instrument[symbol]
                    if instrument.category == "spot":
                        instrument.currentQty = var.DASH
                    else:
                        instrument.currentQty = float(values["size"])
                        if values["side"] == "Sell":
                            instrument.currentQty = -instrument.currentQty
                    instrument.avgEntryPrice = service.set_number(
                        instrument=instrument, number=float(values["avgPrice"])
                    )
                    instrument.unrealisedPnl = service.set_number(
                        instrument=instrument, number=float(values["unrealisedPnl"])
                    )
                    instrument.marginCallPrice = values["liqPrice"]
                    if not instrument.marginCallPrice:
                        instrument.marginCallPrice = var.DASH
                if isinstance(res["result"]["list"], list):
                    success[num] = ""  # success

        threads, success = [], []
        for category in self.categories:
            if category == "linear":
                for settlCurrency in self.settlCurrency_list[category]:
                    success.append("FATAL")
                    t = threading.Thread(
                        target=get_in_thread,
                        args=(category, settlCurrency, success, len(success) - 1),
                    )
                    threads.append(t)
                    t.start()
            elif category != "spot":
                success.append("FATAL")
                t = threading.Thread(
                    target=get_in_thread,
                    args=(category, None, success, len(success) - 1),
                )
                threads.append(t)
                t.start()
        [thread.join() for thread in threads]
        for error in success:
            if error:
                self.logger.error(
                    "The list was expected when the positions were loaded, "
                    + "but for some categories and settlCurrency it was not "
                    + "received"
                )
                return error

    def fill_instrument(self, values: dict, category: str):
        """
        Filling the instruments data.

        The data is stored in the Instrument class using MetaInstrument class.
        The data fields of different exchanges are unified through the
        Instrument class. See detailed description of the fields there.
        """
        if category == "spot":
            symb = values["baseCoin"] + "/" + values["quoteCoin"]
        else:
            symb = values["symbol"]
        symbol = (symb, self.name)
        self.ticker[(values["symbol"], category)] = symb
        instrument = self.Instrument.add(symbol)
        instrument.market = self.name
        instrument.category = category
        instrument.symbol = symb
        instrument.ticker = values["symbol"]
        instrument.baseCoin = values["baseCoin"]
        instrument.quoteCoin = values["quoteCoin"]
        if "settleCoin" in values:
            instrument.settlCurrency = (
                values["settleCoin"],
                self.name,
            )
            if values["settleCoin"] not in self.settlCurrency_list[category]:
                self.settlCurrency_list[category].append(values["settleCoin"])
            if values["settleCoin"] not in self.settleCoin_list:
                self.settleCoin_list.append(values["settleCoin"])
        else:
            instrument.settlCurrency = (
                var.DASH,
                self.name,
            )
        if "deliveryTime" in values:
            if int(values["deliveryTime"]):
                instrument.expire = service.time_converter(
                    int(values["deliveryTime"]) / 1000
                )
            else:
                instrument.expire = "Perpetual"
        else:
            instrument.expire = "Perpetual"
        instrument.tickSize = float(values["priceFilter"]["tickSize"])
        instrument.price_precision = service.precision(number=instrument.tickSize)
        instrument.minOrderQty = float(values["lotSizeFilter"]["minOrderQty"])
        if category == "spot":
            instrument.qtyStep = float(values["lotSizeFilter"]["basePrecision"])
        else:
            instrument.qtyStep = float(values["lotSizeFilter"]["qtyStep"])
        instrument.precision = service.precision(number=instrument.qtyStep)
        if values["status"] == "Trading":
            instrument.state = "Open"
        else:
            instrument.state = values["status"]
        instrument.multiplier = 1
        instrument.myMultiplier = 1
        if category == "spot":
            instrument.fundingRate = var.DASH
            instrument.avgEntryPrice = var.DASH
            instrument.marginCallPrice = var.DASH
            instrument.currentQty = var.DASH
            instrument.unrealisedPnl = var.DASH
        if category == "option":
            instrument.fundingRate = var.DASH
        instrument.valueOfOneContract = 1
        if category == "inverse":
            instrument.isInverse = True
        else:
            instrument.isInverse = False
        if instrument.state == "Open":
            self.instrument_index = service.fill_instrument_index(
                index=self.instrument_index,
                instrument=instrument,
                ws=self,
            )

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
