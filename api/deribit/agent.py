import json
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Union

import services as service
from api.errors import Error
from api.http import Send
from common.variables import Variables as var
from display.messages import ErrorMessage

from .error import DeribitWsRequestError
from .path import Listing, Matching_engine
from .ws import Deribit


class Agent(Deribit):
    def get_active_instruments(self) -> str:
        """
        Retrieves available trading instruments. This method can be used to
        see which instruments are available for trading, or which
        instruments have recently expired.

        Returns
        -------
        str
            On success, "" is returned, otherwise "error".
        """
        path = self.api_version + Listing.GET_ACTIVE_INSTRUMENTS
        data = Send.request(self, path=path, verb="GET")
        if isinstance(data, dict):
            if "result" in data:
                if isinstance(data["result"], list):
                    for values in data["result"]:
                        Agent.fill_instrument(
                            self,
                            values=values,
                        )
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
                else:
                    error = "A list was expected when loading instruments, but was not received."
            else:
                error = "When loading instruments, 'result' was not received."
        else:
            error = "Invalid data was received when loading instruments. " + str(data)
        self.logger.error(error)

        return service.unexpected_error(self)

    def get_instrument(self, ticker: str, category=None) -> str:
        """
        Gets a specific instrument by symbol. Fills the
        self.Instrument[<symbol>] array with data.

        Returns
        -------
        str
            On success, "" is returned.
        """
        path = Listing.GET_INSTRUMENT_DATA
        params = {"instrument_name": ticker}
        self.sequence += 1
        id = f"{path}_{ticker}_{self.sequence}"
        text = " - symbol - " + ticker
        res = Agent.ws_request(self, path=path, id=id, params=params, text=text)
        if isinstance(res, dict):
            Agent.fill_instrument(self, values=res)

            return ""

        else:
            return res  # error type

    count = 0

    def fill_instrument(self, values: dict) -> str:
        """
        Filling the instruments data.

        The data is stored in the Instrument class using MetaInstrument class.
        The data fields of different exchanges are unified through the
        Instrument class. See detailed description of the fields there.
        """
        category = values["kind"] + "_" + values["instrument_type"]
        category = self.define_category[category]
        if "spot" in category:
            symb = values["base_currency"] + "/" + values["quote_currency"]
        else:
            symb = values["instrument_name"]
        symbol = (symb, self.name)
        self.ticker[values["instrument_name"]] = symb
        instrument = self.Instrument.add(symbol)
        instrument.market = self.name
        instrument.symbol = symb
        instrument.ticker = values["instrument_name"]
        instrument.category = category
        instrument.baseCoin = values["base_currency"]
        instrument.quoteCoin = values["quote_currency"]
        if "settlement_currency" in values:
            instrument.settlCurrency = (values["settlement_currency"], self.name)
        else:
            instrument.settlCurrency = (
                var.DASH,
                self.name,
            )
        instrument.expire = service.time_converter(
            values["expiration_timestamp"] / 1000
        )
        if instrument.expire.year == 3000:
            instrument.expire = "Perpetual"
        instrument.tickSize = values["tick_size"]
        instrument.price_precision = service.precision(number=instrument.tickSize)
        instrument.minOrderQty = values["min_trade_amount"]
        instrument.qtyStep = instrument.minOrderQty
        instrument.precision = service.precision(number=instrument.qtyStep)
        if values["is_active"]:
            instrument.state = "Open"
        else:
            instrument.state = "Inactive"
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
        instrument.makerFee = values["maker_commission"]
        instrument.takerFee = values["taker_commission"]
        if values["instrument_type"] == "reversed":
            instrument.isInverse = True
        else:
            instrument.isInverse = False
        if instrument.state == "Open":
            self.instrument_index = service.fill_instrument_index(
                index=self.instrument_index, instrument=instrument, ws=self
            )

    def open_orders(self) -> str:
        """
        Retrieves list of user's open orders across many currencies.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": 1953,
            "method": "private/get_open_orders",
            "params": {},
        }
        path = self.api_version + Listing.OPEN_ORDERS
        res = Send.request(self, path=path, verb="POST", postData=msg)
        if isinstance(res, str):
            return res  # error
        if isinstance(res, dict):
            if "result" in res:
                if isinstance(res["result"], list):
                    for order in res["result"]:
                        symbol = (self.ticker[order["instrument_name"]], self.name)
                        instrument = self.Instrument[symbol]
                        order["symbol"] = symbol
                        order["orderID"] = order["order_id"]
                        if "label" in order and order["label"]:
                            order["clOrdID"] = order["label"]
                        order["orderQty"] = order["amount"]
                        order["settlCurrency"] = instrument.settlCurrency
                        order["ordStatus"] = order["order_state"]
                        order["leavesQty"] = order["amount"] - order["filled_amount"]
                        order["transactTime"] = service.time_converter(
                            time=int(order["last_update_timestamp"]) / 1000, usec=True
                        )
                        if order["direction"] == "buy":
                            order["side"] = "Buy"
                        else:
                            order["side"] = "Sell"
                        if symbol not in self.symbol_list:
                            self.symbol_list.append(symbol)
                    self.setup_orders = res["result"]
                    return ""
                else:
                    error = "The list was expected when the orders were loaded, but was not received."
            else:
                error = "When loading open orders 'result' was not received."
        else:
            error = "Invalid data was received when loading open orders. " + str(res)
        self.logger.error(error)

        return service.unexpected_error(self)

    def get_user(self) -> str:
        """
        Returns the user ID and other useful information about the user and
        places it in self.user.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type.
        """
        path = self.api_version + Listing.GET_ACCOUNT_INFO
        msg = {
            "jsonrpc": "2.0",
            "id": 2515,
            "method": "private/get_account_summaries",
            "params": {"extended": True},
        }
        res = Send.request(self, path=path, verb="POST", postData=msg)
        if isinstance(res, dict):
            if "id" in res["result"]:
                self.user = res
                self.user_id = res["result"]["id"]
                for values in res["result"]["summaries"]:
                    currency = (values["currency"], self.name)
                    account = self.Account[currency]
                    account.account = res["result"]["id"]
                    account.settlCurrency = values["currency"]
                    account.limits = values["limits"]
                    account.limits["private/get_transaction_log"] = {
                        "burst": 10,
                        "rate": 2,
                    }
                return ""

            else:
                self.logger.error(ErrorMessage.USER_ID_NOT_FOUND)
                return "FATAL"
        elif not isinstance(res, str):
            res = "FATAL"
        self.logger.error(ErrorMessage.USER_ID_NOT_RECEIVED)

        return res

    def get_wallet_balance(self) -> None:
        """
        Receives data on currency accounts through the websocket channel
        user.portfolio.any in the api/deribit/ws.py
        """

        return ""

    def get_position_info(self):
        """
        Gets current positions.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type.
        """
        path = self.api_version + Listing.GET_POSITION_INFO
        data = Send.request(self, path=path, verb="GET")
        if isinstance(data, dict):
            for values in data["result"]:
                symbol = (self.ticker[values["instrument_name"]], self.name)
                instrument = self.Instrument[symbol]
                if "spot" in instrument.category:
                    instrument.currentQty = var.DASH
                else:
                    if instrument.category == "future_linear":
                        instrument.currentQty = values["size_currency"]
                    else:
                        instrument.currentQty = values["size"]
                instrument.avgEntryPrice = service.set_avgEntryPrice(
                    instrument=instrument, price=values["average_price"]
                )
                instrument.unrealisedPnl = values["total_profit_loss"]
                """if "estimated_liquidation_price" in values:
                    instrument.marginCallPrice = values["estimated_liquidation_price"]
                else:
                    instrument.marginCallPrice = var.DASH"""
        else:
            self.logger.error(
                "The dict was expected when the positions were loaded, but "
                + "it was not received."
            )
            return "FATAL"

        return ""

    def trading_history(
        self, histCount: int, start_time: datetime = None, funding: bool = False
    ) -> Union[dict, str]:
        """
        Downloading trading and funding history from the endpoints:
            private/get_user_trades_by_currency_and_time
            history from private/get_transaction_log

        Provided data
        -------------
        endpoint                                        trades  funding period
        private/get_user_trades_by_currency_and_time    yes     no      last 5 days
        private/get_transaction_log                     yes     yes     full

        Deribit only provides trading history from
        'private/get_user_trades_by_currency_and_time' endpoint for last 5
        days, so we use 'private/get_transaction_log' endpoint to get
        trades made earlier than 5 days ago.

        label (clOrdID)
        ---------------
        endpoint                                        supported
        private/get_user_trades_by_currency_and_time    yes
        private/get_transaction_log                     no

        Trades made more than 5 days ago will be downloaded without the
        clOrdID field.

        Parameters
        ----------
        histCount: int
            The function returns data by chunks in the amount of histCount.
        start_time: datetime
            Date when a new chunk of data will be downloaded.
        funding: bool
            Cancels the "private/get_user_trades_by_currency_and_time"
            endpoint request if only funding and delivery are requested once
            a day at 8:00.

        Returns
        -------
        list | str
            On success, list is returned, otherwise error type.

        Notes
        -----
        1.
        The function gets the same trades from two different endpoints. So
        there will be trades with the same execID. It is preferable to save
        trades to the database from the
        ``private/get_user_trades_by_currency_and_time`` becuase it contains
        the label (clOrdID) field. As far Tmatic saves trades with the same
        execID only once and ignores repeating trades, this function
        corrects the timestamp of the trades from the endpoint mentioned
        above for 1ms ahead. Thus after sorting, the trades from the
        ``private/get_user_trades_by_currency_and_time`` are always first.
        2.
        Deribit limits non_matching_engine requests using a special scheme
        described at https://www.deribit.com/kb/deribit-rate-limits
        However, they have introduced a special limit for
        ``private/get_transaction_log`` to only 2 requests per second.
        3.
        In the transaction log, Deribit splits a trade into two transactions
        when a position passes through 0, so two trades with the same trade_id
        are merged.
        """
        trade_history = []
        startTime = service.time_converter(start_time)
        limit = 500
        step = 8640000000  # +100 days

        def get_in_thread(path, currency, start, end, limit, data_type, success, num):
            nonlocal trade_history
            cursor = limit
            continuation = None
            id = f"{path}_{currency}"
            while cursor >= limit:
                params = {
                    "currency": currency,
                    "start_timestamp": start,
                    "end_timestamp": end,
                    "count": limit,
                }
                if data_type == "trades":
                    params["sorting"] = "desc"
                if continuation:
                    params["continuation"] = continuation
                text = (
                    " - "
                    + currency
                    + " - period - "
                    + str(service.time_converter(start / 1000))
                    + " - "
                    + str(service.time_converter(end / 1000))
                )
                self.logger.info(
                    "Requesting trading history - currency - "
                    + currency
                    + " - startTime - "
                    + str(service.time_converter(start / 1000))
                )
                data = Agent.ws_request(
                    self, path=path, id=id, params=params, text=text, currency=currency
                )
                if data:
                    res = data[data_type]
                    if data_type == "logs":
                        res = list(
                            filter(
                                lambda x: x["type"]
                                in ["settlement", "trade", "delivery"],
                                res,
                            )
                        )
                        continuation = data["continuation"]
                    if isinstance(res, list):
                        for row in res:
                            if not row["instrument_name"] in self.ticker:
                                self.logger.info(
                                    self.name
                                    + " - Requesting instrument - ticker="
                                    + row["instrument_name"]
                                )
                                Agent.get_instrument(
                                    self, ticker=row["instrument_name"]
                                )
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
                            if data_type == "logs":
                                if row["type"] == "settlement":
                                    row["execType"] = "Funding"
                                    row["execID"] = (
                                        str(row["user_seq"])
                                        + "_"
                                        + row["settlCurrency"][0]
                                    )
                                    row["leavesQty"] = row["position"]
                                    row["execFee"] = row["total_interest_pl"]
                                elif row["type"] == "trade":
                                    row["execType"] = "Trade"
                                    row["execID"] = (
                                        str(row["trade_id"])
                                        + "_"
                                        + row["settlCurrency"][0]
                                    )
                                    row["orderID"] = (
                                        row["order_id"] + "_" + row["settlCurrency"][0]
                                    )
                                    row[
                                        "leavesQty"
                                    ] = 9999999999999  # leavesQty is not supported by Deribit
                                    row["execFee"] = row["commission"]
                                elif row["type"] == "delivery":
                                    row["execType"] = "Delivery"
                                    row["execID"] = (
                                        str(row["user_seq"])
                                        + "_"
                                        + row["settlCurrency"][0]
                                    )
                                    row[
                                        "leavesQty"
                                    ] = 9999999999999  # leavesQty is not supported by Deribit
                                    row["execFee"] = row["commission"]
                                if row["side"] != None:
                                    if "buy" in row["side"] or row["side"] == "long":
                                        row["side"] = "Buy"
                                    elif (
                                        "sell" in row["side"] or row["side"] == "short"
                                    ):
                                        row["side"] = "Sell"
                            else:
                                row["execType"] = "Trade"
                                row["execID"] = (
                                    str(row["trade_id"]) + "_" + row["settlCurrency"][0]
                                )
                                row["orderID"] = row["order_id"]
                                row[
                                    "leavesQty"
                                ] = 9999999999999  # leavesQty is not supported by Deribit
                                row["execFee"] = row["fee"]
                                if row["direction"] == "sell":
                                    row["side"] = "Sell"
                                else:
                                    row["side"] = "Buy"
                                row["timestamp"] -= 1  # Puts the trades
                                # from data_type="trades" in front of the
                                # same trades from data_type="logs"
                            if "label" in row:
                                row["clOrdID"] = row["label"]
                            row["category"] = instrument.category
                            if row["execType"] == "Delivery":
                                row["lastPx"] = row["mark_price"]
                            else:
                                row["lastPx"] = row["price"]
                            row["transactTime"] = service.time_converter(
                                time=row["timestamp"] / 1000, usec=True
                            )
                            row["lastQty"] = row["amount"]
                            row["market"] = self.name
                            """if row["execType"] == "Funding":
                                if row["side"] == "Sell":
                                    row["lastQty"] = -row["lastQty"]"""
                            row["commission"] = "Not supported"
                            # row["price"] = "Not supported"
                        if res and data_type == "logs":
                            # Exclude entries containing "execType" = "Funding"
                            # from non-perpetual and spot instruments.
                            for number in range(len(res) - 1, -1, -1):
                                if res[number]["execType"] == "Funding":
                                    instrument = self.Instrument[res[number]["symbol"]]
                                    if (
                                        instrument.expire != "Perpetual"
                                        or "spot" in instrument.category
                                    ):
                                        res.pop(number)
                            # Deribit splits trades when the position crosses
                            # the zero point.

                            # Example: Current position is -1. You buy 2 in
                            # one trade. You get two entries in the trading
                            # history: one trade closes the current position,
                            # then the other opens a new buy.

                            # However, in such cases, Tmatic only stores one
                            # trade.

                            # Merging transactions with the same trade_id:
                            transaction = OrderedDict()
                            for row in res:
                                if row["type"] == "trade":
                                    if row["trade_id"] in transaction:
                                        transaction[row["trade_id"]]["amount"] += row[
                                            "amount"
                                        ]
                                        transaction[row["trade_id"]]["execFee"] += row[
                                            "execFee"
                                        ]
                                        transaction[row["trade_id"]]["lastQty"] += row[
                                            "lastQty"
                                        ]
                                    else:
                                        transaction[row["trade_id"]] = row
                                else:
                                    transaction[row["execID"]] = row
                            trade_history += list(transaction.values())
                        else:
                            trade_history += res
                    else:
                        self.logger.error(
                            "The list was expected when the trading history were loaded, but for the currency "
                            + currency
                            + " it was not received. Reboot."
                        )
                        cursor = -1
                        break
                    cursor = len(res)
                    if cursor:
                        end = res[-1]["timestamp"]
                else:
                    cursor = -1
                    break
                if data_type == "logs" and continuation is None:
                    break
            if cursor > -1:
                success[num] = ""

        while startTime < service.time_converter(datetime.now(tz=timezone.utc)):
            endTime = startTime + step
            if endTime < 1577826000000:  # Dec 31 2019 21:00:00 GMT+0000
                endTime = 1577826000000
            get_last_trades = False
            if endTime >= service.time_converter(datetime.now(tz=timezone.utc)):
                if not funding:
                    get_last_trades = True
            threads, success = [], []
            for currency in self.settleCoin_list:
                success.append("FATAL")
                path = Listing.TRADES_AND_FUNDING_TRANSACTION_LOG
                t = threading.Thread(
                    target=get_in_thread,
                    args=(
                        path,
                        currency,
                        startTime,
                        endTime,
                        limit,
                        "logs",
                        success,
                        len(success) - 1,
                    ),
                )
                threads.append(t)
                t.start()
                if get_last_trades:
                    success.append("FATAL")
                    path = Listing.TRADES_LAST_5_DAYS
                    t = threading.Thread(
                        target=get_in_thread,
                        args=(
                            path,
                            currency,
                            startTime,
                            endTime,
                            limit,
                            "trades",
                            success,
                            len(success) - 1,
                        ),
                    )
                    threads.append(t)
                    t.start()
            [thread.join() for thread in threads]
            for error in success:
                if error:
                    return error
            tmp = []
            for el in trade_history:
                if el not in tmp:
                    tmp.append(el)
            trade_history = tmp
            message = (
                "Trading history data, received: "
                + str(len(trade_history))
                + " records."
            )
            self.logger.info(message)
            if len(trade_history) > histCount:
                break
            startTime = endTime
        trade_history.sort(key=lambda x: x["transactTime"])
        """for row in trade_history:
            print(
                row["transactTime"],
                row["execType"],
                row["symbol"],
                row["side"],
                row["lastQty"],
                row["lastPx"],
                "___lastQty",
                row["lastQty"],
                row["execID"],
            )
        print("___________________________FINISH", len(trade_history))"""

        return {"data": trade_history, "length": len(trade_history)}

    def trade_bucketed(
        self, symbol: tuple, start_time: datetime, timeframe: Union[int, str]
    ) -> Union[list, str]:
        """
        Returns kline data in in 1000 rows. Available timeframes: 1, 3, 5, 10,
        15, 30, 60, 120, 180, 360, 720, 1D

        If None is returned, the request failed. Reboot.

        Parameters
        ----------
        symbol: tuple
            Instrument symbol.
        start_time: datetime
            Beginning of the period.
        timeframe: int | str
            Time frames are expressed in minutes or '1D' in case of daily
            period.

        Returns
        -------
        str | None
            On success, list is returned, otherwise error type.
        """
        path = Listing.TRADE_BUCKETED
        self.sequence += 1
        id = f"{path}_{symbol}_{timeframe}_seq{self.sequence}"
        start_timestamp = service.time_converter(time=start_time)
        if isinstance(timeframe, int):
            number = timeframe * 60 * 1000000
        else:
            number = 86400 * 1000000
        end_timestamp = start_timestamp + number
        resolution = self.timefrs[timeframe]
        params = {
            "instrument_name": self.Instrument[symbol].ticker,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "resolution": str(resolution),
        }
        text = " - symbol - " + str(symbol) + " - interval - " + str(timeframe)
        res = Agent.ws_request(self, path=path, id=id, params=params, text=text)
        if isinstance(res, dict):
            klines = []
            for step in range(len(res["ticks"])):
                klines.append(
                    {
                        "timestamp": service.time_converter(
                            time=res["ticks"][step] / 1000
                        ),
                        "open": res["open"][step],
                        "high": res["high"][step],
                        "low": res["low"][step],
                        "close": res["close"][step],
                        "symbol": symbol,
                    }
                )
            return klines
        elif isinstance(res, str):
            return res  # error
        else:
            self.logger.error(
                "A dict was expected when loading klines, but was not received."
            )
            return service.unexpected_error(self)

    def place_limit(
        self, quantity: float, price: float, clOrdID: str, symbol: tuple
    ) -> Union[dict, str]:
        """
        Places a limit order.

        Returns
        -------
        dict | str
            On success, dict is returned, otherwise an error type.
        """
        side = "buy" if quantity > 0 else "sell"
        path = Listing.PLACE_LIMIT.format(SIDE=side)
        id = f"{path}_{clOrdID}"
        text = (
            " - symbol - "
            + str(symbol)
            + " - price - "
            + str(price)
            + " - quantity - "
            + str(abs(quantity))
        )
        params = {
            "instrument_name": self.Instrument[symbol].ticker,
            "price": price,
            "amount": abs(quantity),
            "type": "limit",
            "label": clOrdID,
        }

        return Agent.ws_request(self, path=path, id=id, params=params, text=text)

    def replace_limit(
        self,
        leavesQty: float,
        price: float,
        orderID: str,
        symbol: tuple,
        orderQty: float,
    ) -> Union[dict, str]:
        path = Listing.REPLACE_LIMIT
        id = f"{path}_{orderID}"
        text = (
            " - symbol - "
            + str(symbol[0])
            + " - price - "
            + str(price)
            + " - quantity - "
            + str(abs(leavesQty))
        )
        """
        '
        '
        Deribit does not have a leavesQty field. When amout changes when
        raplace order, this parameter also changes as originally declared in
        order. Therefore, a conflict situation may arise when processing
        Tmatic orders. Example:
            1) New order for 30 contracts.
            2) Order executed for 10 contracts, Tmatic considers the
        remainder as 20 contracts.
            3) Timatic replaces order with a new price and passes amount = 20
        to params. In this case, Deribit will change the order from 30 to 20
        contracts. Thus, Deribit will believe that there are 10 unexecuted
        contracts left, while Tmatic still has 20 contracts.
            4) Another 10 contracts executed: Deribit deletes the order as
        fully executed, and Tmatic considers that there are still 10
        contracts left and does not delete the order from its register.
        """
        params = {"order_id": orderID, "amount": orderQty, "price": price}
        """
        '
        '
        """

        return Agent.ws_request(self, path=path, id=id, params=params, text=text)

    def remove_order(self, order: dict) -> Union[dict, str]:
        path = Listing.REMOVE_ORDER
        id = f"{path}_{order['orderID']}"
        text = " - symbol - " + str(order["symbol"][0])
        params = {"order_id": order["orderID"]}

        return Agent.ws_request(self, path=path, id=id, params=params, text=text)

    def ws_request(
        self, path: str, id: str, params: dict, text: str, currency="BTC"
    ) -> Union[str, list, dict]:
        """
        Requests data over websocket connection. Request limits are taken
        into account according to
        https://www.deribit.com/kb/deribit-rate-limits

        Parameters
        ----------
        path: str
            Endpoint address.
        id: str
            Response key.
        params: dict
            Request parameters.
        text: str
            Aadditional info saved to the log file.
        currency: str
            By default, limits apply globally for all currencies, but can be
            enabled for specific customers upon request.

        Errors
        ------
            WAIT    the request is non-fatal, wait and try again.
            FATAL   reboot.
            IGNORE  the error only appears on the screen and does not cause a
            reboot.
            CANCEL  loading cancels.
            BLOCK   trading should bo blocked.

        Returns
        -------
            Requested information. If failed - error type.
        """
        account = self.Account[(currency, self.name)]
        limit = account.limits
        if path in Matching_engine.PATHS:
            lim = limit["matching_engine"]
            limits = lim["trading"]["total"]
            if "spot" in lim:
                limits = lim["spot"]
            maximum_quotes = lim["maximum_quotes"]
            cancel_all = lim["cancel_all"]
            scheme = self.scheme["matching_engine"]
        else:
            if path == "private/get_transaction_log":
                limits = limit[path]
                scheme = self.scheme[path]
            else:
                limits = limit["non_matching_engine"]
                scheme = self.scheme["non_matching_engine"]
        count = 0
        scheme["lock"].acquire(True)
        for num in range(len(scheme["time"]) - 1, -1, -1):
            tm = time.time()
            if tm - scheme["time"][num] < 1:
                count += 1
            if tm - scheme["time"][num] > 5:  # Considering 5
                # seconds withot a single request to return the burst scheme.
                scheme["time"].pop(num)
        if scheme["scheme"] == "burst" and len(scheme["time"]) >= limits["burst"]:
            scheme["scheme"] = "rate"
        elif not len(scheme["time"]):
            scheme["scheme"] = "burst"
        if scheme["scheme"] == "rate":
            number = min(limits["rate"], count)
            slp = 1 - (time.time() - scheme["time"][-number])
            if slp < 0:
                slp = 0
            time.sleep(slp)  # Wait if the number of requests per second is exceeded.
        scheme["lock"].release()
        while True:
            self.response[id] = {
                "request_time": time.time() + self.ws_request_delay,
                "result": None,
            }
            scheme["time"].append(time.time())
            msg = {"method": path, "params": params, "jsonrpc": "2.0", "id": id}
            try:
                self.ws.send(json.dumps(msg))
            except Exception as ex:
                message = (
                    "Error sending request via websocket: " + str(ex) + " - Reboot."
                )
                self.logger.error(message)
                var.queue_info.put(
                    {
                        "market": self.name,
                        "message": message,
                        "time": datetime.now(tz=timezone.utc),
                        "warning": "error",
                    }
                )
            while time.time() < self.response[id]["request_time"]:
                res = self.response[id]["result"]
                if res:
                    if "error" in res:
                        error = Error.handler(
                            self,
                            exception=DeribitWsRequestError(response=res),
                            response=res,
                            verb="request via ws",
                            path=path,
                        )
                        if error == "RETRY":
                            time.sleep(0.5)
                            break
                        else:
                            del self.response[id]
                            return error
                    else:
                        del self.response[id]
                        return res
                time.sleep(0.05)
            else:
                message = (
                    "No response to websocket "
                    + path
                    + " request, id="
                    + str(id)
                    + " within "
                    + str(self.ws_request_delay)
                    + " seconds. Reboot"
                )
                self.logger.error(message)
                var.queue_info.put(
                    {
                        "market": self.name,
                        "message": message,
                        "time": datetime.now(tz=timezone.utc),
                        "warning": "error",
                    }
                )
                self.response[id]
                self.logNumFatal = "FATAL"

                return self.logNumFatal

    def activate_funding_thread(self):
        """
        Makes the funding_thread active.
        """
        self.funding_thread_active = True
        t = threading.Thread(target=Agent.funding_thread, args=(self,))
        t.start()

    def funding_thread(self) -> None:
        """
        There is no Deribit websocket stream to provide funding (settlement)
        and delivery. So this thread requests this information at the
        designated time after 08:00:00 UTC. It requests two times at 8:00:15
        and 8:01:15 to avoid an unsuccessful response in case there is a
        delay from Deribit.
        """
        while self.funding_thread_active:
            tm = datetime.now(tz=timezone.utc)
            if tm.hour == 8:
                if tm.minute < 2:
                    if tm.second == 15:
                        start_time = datetime(
                            year=tm.year,
                            month=tm.month,
                            day=tm.day,
                            hour=7,
                            minute=59,
                            second=0,
                            tzinfo=timezone.utc,
                        )
                        history = Agent.trading_history(
                            self, histCount=500, start_time=start_time, funding=True
                        )
                        his_data = history["data"]
                        if isinstance(his_data, list):
                            for row in his_data:
                                data = service.select_database(  # read_database
                                    "select EXECID from %s where EXECID='%s' and account=%s and market='%s'"
                                    % (
                                        var.database_table,
                                        row["execID"],
                                        self.user_id,
                                        self.name,
                                    ),
                                )
                                if not data:
                                    self.transaction(row=row)
                        else:
                            message = "Failed request for funding and delivery information that arrived at 8:00 AM"
                            self.logger.error(message)
                            var.queue_info.put(
                                {
                                    "market": self.name,
                                    "message": message,
                                    "time": datetime.now(tz=timezone.utc),
                                    "warning": "error",
                                }
                            )
            time.sleep(1 - time.time() % 1)
