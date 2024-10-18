from collections import OrderedDict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Union

import services as service
from api.http import Send
from common.variables import Variables as var
from display.messages import ErrorMessage

from .path import Listing
from .ws import Bitmex


class Agent(Bitmex):
    def get_active_instruments(self) -> int:
        data = Send.request(self, path=Listing.GET_ACTIVE_INSTRUMENTS, verb="GET")
        if not isinstance(data, list):
            self.logger.error(
                "A list was expected when loading instruments, but was not received."
            )
            return service.unexpected_error(self)
        for values in data:
            Agent.fill_instrument(
                self,
                values=values,
            )
        self.symbol_list = service.check_symbol_list(
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
        Requests the user ID and other useful information about the user and
        places it in self.user.

        Returns
        -------
        str
            On success, "" is returned.
        """
        res = Send.request(self, path=Listing.GET_ACCOUNT_INFO, verb="GET")
        if isinstance(res, dict):
            if "id" in res:
                self.user_id = res["id"]
                self.user = res
                return ""
            else:
                self.logger.error(ErrorMessage.USER_ID_NOT_FOUND)
                return "FATAL"
        elif not isinstance(res, str):
            res = "FATAL"
        self.logger.error(ErrorMessage.USER_ID_NOT_RECEIVED)

        return res

    def get_instrument(self, ticker: str, category=None) -> str:
        """
        Gets a specific instrument by symbol. Fills the
        self.Instrument[<symbol>] array with data.

        Returns
        -------
        str
            On success, "" is returned.
        """
        path = Listing.GET_INSTRUMENT_DATA.format(SYMBOL=ticker)
        res = Send.request(self, path=path, verb="GET")
        if self.logNumFatal == "":
            if res:
                values = res[0]
                Agent.fill_instrument(self, values=values)

                return ""

            elif isinstance(res, str):  # error
                return res
            else:
                message = ErrorMessage.INSTRUMENT_NOT_FOUND.format(
                    PATH=path, TICKER=ticker, CATEGORY=category
                )
                self.logger.warning(message)

                return message

    def fill_instrument(self, values: dict) -> Union[str, None]:
        """
        Filling the instruments data.

        The data is stored in the Instrument class using MetaInstrument class.
        The data fields of different exchanges are unified through the
        Instrument class. See detailed description of the fields there.
        """
        """
        Check:
            P_KAMALAX24
            P_TRUMPX24
            P_SBFPARDONF25
            P_POWELLK26
            P_GENSLERM26
            P_FTXZ26
        """
        if "settlCurrency" in values:
            try:
                self.currency_divisor[values["settlCurrency"]]
            except KeyError:
                message = ErrorMessage.NO_CURRENCY.format(
                    TICKER=values["symbol"], CURRENCY=values["settlCurrency"]
                )
                var.logger.warning(message)
                var.queue_info.put(
                    {
                        "market": "Bitmex",
                        "message": message,
                        "time": datetime.now(tz=timezone.utc),
                        "warning": "error",
                    }
                )
                return
        # myMultiplier

        if values["isInverse"]:  # Inverse
            valueOfOneContract = Decimal(values["multiplier"]) / Decimal(
                values["underlyingToSettleMultiplier"]
            )
            minimumTradeAmount = valueOfOneContract * Decimal(values["lotSize"])
            category = "inverse"
        elif values["isQuanto"]:  # Quanto
            valueOfOneContract = Decimal(values["multiplier"]) / Decimal(
                self.currency_divisor[values["settlCurrency"]]
            )
            minimumTradeAmount = values["lotSize"]
            category = "quanto"
        else:  # Linear / "Spot"
            if "underlyingToPositionMultiplier" in values:
                valueOfOneContract = Decimal(1) / Decimal(
                    values["underlyingToPositionMultiplier"]
                )
            elif values["underlyingToSettleMultiplier"]:
                valueOfOneContract = Decimal(values["multiplier"]) / Decimal(
                    values["underlyingToSettleMultiplier"]
                )
            minimumTradeAmount = valueOfOneContract * Decimal(values["lotSize"])
            if "settlCurrency" not in values:
                category = "spot"
            else:
                category = "linear"
        myMultiplier = Decimal(values["lotSize"]) / minimumTradeAmount
        if category == "spot":
            symb = values["underlying"] + "/" + values["quoteCurrency"]
        else:
            symb = values["symbol"]
        valueOfOneContract = float(valueOfOneContract)
        minimumTradeAmount = float(minimumTradeAmount)
        myMultiplier = int(myMultiplier)
        symbol = (symb, self.name)
        self.ticker[values["symbol"]] = symb
        instrument = self.Instrument.add(symbol)
        instrument.market = self.name
        instrument.category = category
        instrument.symbol = symb
        instrument.ticker = values["symbol"]
        instrument.myMultiplier = myMultiplier
        instrument.multiplier = values["multiplier"]
        if category == "spot":
            instrument.fundingRate = "-"
            instrument.avgEntryPrice = "-"
            instrument.marginCallPrice = "-"
            instrument.currentQty = "-"
            instrument.unrealisedPnl = "-"
        if "settlCurrency" in values:
            instrument.settlCurrency = (
                values["settlCurrency"],
                self.name,
            )
        else:
            instrument.settlCurrency = (
                "-",
                self.name,
            )
        instrument.tickSize = values["tickSize"]
        instrument.price_precision = service.precision(
            number=values["tickSize"]
        )
        instrument.minOrderQty = minimumTradeAmount
        instrument.qtyStep = minimumTradeAmount
        instrument.precision = service.precision(minimumTradeAmount)
        instrument.state = values["state"]
        instrument.volume24h = values["volume24h"]
        if "expiry" in values:
            if values["expiry"]:
                instrument.expire = service.time_converter(
                    time=values["expiry"]
                )
            else:
                instrument.expire = "Perpetual"
        else:
            instrument.expire = "Perpetual"
        if "fundingRate" in values:
            instrument.fundingRate = values["fundingRate"] * 100
        instrument.asks = [[0, 0]]
        instrument.bids = [[0, 0]]
        instrument.baseCoin = values["underlying"]
        instrument.quoteCoin = values["quoteCurrency"]
        instrument.valueOfOneContract = valueOfOneContract
        if values["state"] == "Open":
            if category != "spot":
                self.instrument_index = service.fill_instrument_index(
                    index=self.instrument_index,
                    instrument=self.Instrument[symbol],
                    ws=self,
                )
        instrument.makerFee = values["makerFee"]
        instrument.takerFee = values["takerFee"]

        return category

    def get_position(self, symbol: tuple) -> OrderedDict:
        """
        Gets instrument position when instrument is not in the symbol_list
        """
        instrument = self.Instrument[symbol]
        ticker = instrument.ticker
        path = Listing.GET_POSITION.format(SYMBOL=ticker)
        data = Send.request(self, path=path, verb="GET")
        if isinstance(data, list):
            if data:
                instrument.currentQty = (
                    # data[0]["currentQty"] * instrument.valueOfOneContract
                    data[0]["currentQty"]
                    / instrument.myMultiplier
                )
            self.logger.info(
                str(symbol)
                + " has been added to the positions dictionary for "
                + self.name
            )
        else:
            self.logger.info(str(symbol) + " not found in get_position()")

    def trade_bucketed(
        self, symbol: tuple, start_time: datetime, timeframe: int
    ) -> Union[list, str]:
        """
        Gets timeframe data. Available time intervals: 1m,5m,1h,1d.

        Returns
        -------
        str | None
            On success, list is returned, otherwise error type.
        """
        path = Listing.TRADE_BUCKETED.format(
            TIMEFRAME=self.timefrs[timeframe],
            SYMBOL=self.Instrument[symbol].ticker,
            TIME=str(start_time)[:19],
        )
        res = Send.request(self, path=path, verb="GET")
        if isinstance(res, list):
            if res:
                filtered = []
                count = 0
                last_time = ""
                for values in res:
                    values["symbol"] = symbol
                    values["timestamp"] = service.time_converter(
                        time=values["timestamp"]
                    )
                    if "open" and "high" and "low" and "close" in values:
                        filtered.append(values)
                    else:
                        count += 1
                        last_time = values["timestamp"]
                if count:
                    if count == 1:
                        t = ("s", "This row is")
                    else:
                        t = ("", "These rows are")
                    message = (
                        "Kline's data obtained from the Bitmex API is not complete for "
                        + str(symbol)
                        + " at the "
                        + self.timefrs[timeframe]
                        + " time interval. "
                        + str(count)
                        + " row"
                        + t[0]
                        + " do not contain: open, high, low or closed. "
                        + t[1]
                        + " skipped. The time of the last row is "
                        + str(last_time)
                    )
                    self.logger.warning(message)
                    var.queue_info.put(
                        {
                            "market": self.name,
                            "message": message,
                            "time": datetime.now(tz=timezone.utc),
                            "warning": "warning",
                        }
                    )
                return filtered
            else:
                message = ErrorMessage.REQUEST_EMPTY.format(PATH=path)
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
        else:
            return res  # error

    def trading_history(self, histCount: int, start_time: datetime) -> Union[dict, str]:
        """
        Gets trades, funding and delivery from the exchange for the period starting
        from start_time.

        Returns
        -------
        list | str
            On success, list is returned, otherwise error type.
        """
        path = Listing.TRADING_HISTORY.format(
            HISTCOUNT=histCount, TIME=str(start_time)[:19]
        )
        res = Send.request(
            self,
            path=path,
            verb="GET",
        )
        if isinstance(res, list):
            spot_not_included = list()
            for row in res:
                row["ticker"] = row["symbol"]
                if row["symbol"] not in self.ticker:
                    self.logger.info(
                        self.name + " - Requesting instrument - ticker=" + row["symbol"]
                    )
                    Agent.get_instrument(
                        self,
                        ticker=row["symbol"],
                    )

                row["market"] = self.name
                row["symbol"] = (
                    self.ticker[row["symbol"]],
                    self.name,
                )
                instrument = self.Instrument[row["symbol"]]
                row["category"] = instrument.category
                row["transactTime"] = service.time_converter(
                    time=row["transactTime"], usec=True
                )
                if instrument.category == "spot":
                    if row["side"] == "Buy":
                        row["settlCurrency"] = (instrument.quoteCoin, self.name)
                    else:
                        row["settlCurrency"] = (instrument.baseCoin, self.name)
                else:
                    row["settlCurrency"] = instrument.settlCurrency
                if "lastQty" in row:
                    # row["lastQty"] *= instrument.valueOfOneContract
                    row["lastQty"] /= instrument.myMultiplier
                if "leavesQty" in row:
                    # row["leavesQty"] *= instrument.valueOfOneContract
                    row["leavesQty"] /= instrument.myMultiplier
                if row["execType"] == "Funding":
                    if row["foreignNotional"] > 0:
                        row["lastQty"] = -row["lastQty"]
                        row["commission"] = -row["commission"]
                elif row["execType"] == "Settlement":
                    row["execType"] = "Delivery"
                row["execFee"] = None
                if instrument.category != "spot":
                    spot_not_included.append(row)
                else:
                    self.logger.warning(
                        "Tmatic does not support spot trading on Bitmex. The trading history entry with execID "
                        + row["execID"]
                        + " was ignored."
                    )
            return {"data": spot_not_included, "length": len(res)}
        else:
            res  # error type

    def open_orders(self) -> str:
        path = Listing.OPEN_ORDERS
        res = Send.request(
            self,
            path=path,
            verb="GET",
        )
        if isinstance(res, list):
            for order in res:
                order["symbol"] = (
                    self.ticker[order["symbol"]],
                    self.name,
                )
                instrument = self.Instrument[order["symbol"]]
                order["orderQty"] /= instrument.myMultiplier
                order["leavesQty"] /= instrument.myMultiplier
                order["cumQty"] /= instrument.myMultiplier
                order["transactTime"] = service.time_converter(
                    time=order["transactTime"], usec=True
                )
                if order["symbol"] not in self.symbol_list:
                    self.symbol_list.append(order["symbol"])
        else:
            self.logger.error(
                "The list was expected when the orders were loaded, but it was not received."
            )
            return service.unexpected_error(self)
        self.setup_orders = res

        return ""

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
        if self.Instrument[symbol].category == "spot":
            message = (
                "Tmatic does not support spot trading on Bitmex. The order clOrdID "
                + clOrdID
                + " was ignored."
            )
            self.logger.warning(message)
            queue_message = {
                "market": self.name,
                "message": message,
                "time": datetime.now(tz=timezone.utc),
                "warning": "warning",
            }
            var.queue_info.put(queue_message)
            return
        path = Listing.ORDER_ACTIONS
        instrument = self.Instrument[symbol]
        postData = {
            "symbol": instrument.ticker,
            "orderQty": round(quantity * instrument.myMultiplier),
            "price": price,
            "clOrdID": clOrdID,
            "ordType": "Limit",
        }

        return Send.request(self, path=path, postData=postData, verb="POST")

    def replace_limit(
        self, quantity: float, price: float, orderID: str, symbol: tuple
    ) -> Union[dict, str]:
        """
        Moves a limit order
        """

        path = Listing.ORDER_ACTIONS
        instrument = self.Instrument[symbol]
        postData = {
            "symbol": instrument.ticker,
            "price": price,
            "orderID": orderID,
            "leavesQty": round(abs(quantity * instrument.myMultiplier)),
            "ordType": "Limit",
        }

        return Send.request(self, path=path, postData=postData, verb="PUT")

    def remove_order(self, order: dict) -> Union[dict, str]:
        """
        Deletes an order.
        """
        path = Listing.ORDER_ACTIONS
        postData = {"orderID": order["orderID"]}

        return Send.request(self, path=path, postData=postData, verb="DELETE")

    def get_wallet_balance(self):
        """
        Bitmex sends this information via websocket, "margin" subscription.
        """

        return ""

    def get_position_info(self) -> str:
        """
        Gets current positions.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type, such as
            FATAL, CANCEL.
        """
        path = Listing.GET_POSITION_INFO
        data = Send.request(self, path=path, verb="GET")
        if isinstance(data, list):
            for values in data:
                if values["symbol"] in self.ticker:
                    symbol = (
                        self.ticker[values["symbol"]],
                        self.name,
                    )
                    instrument = self.Instrument[symbol]
                    if "currentQty" in values:
                        instrument.currentQty = (
                            values["currentQty"] / instrument.myMultiplier
                        )
                    if instrument.currentQty != 0:
                        if "avgEntryPrice" in values:
                            instrument.avgEntryPrice = values["avgEntryPrice"]
                        if "marginCallPrice" in values:
                            if values["marginCallPrice"] == 100000000:
                                instrument.marginCallPrice = "inf"
                            else:
                                instrument.marginCallPrice = values["marginCallPrice"]
                        if "unrealisedPnl" in values:
                            instrument.unrealisedPnl = values["unrealisedPnl"]
        else:
            self.logger.error(ErrorMessage.POSITIONS_NOT_RECEIVED)
            return "FATAL"

        return ""

    def activate_funding_thread(self):
        """
        Not used for Bitmex.
        """
        pass
