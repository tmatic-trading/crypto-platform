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
        for instrument in data:
            Agent.fill_instrument(
                self,
                instrument=instrument,
            )
        self.symbol_list = service.check_symbol_list(
            symbols=self.Instrument.get_keys(),
            market=self.name,
            symbol_list=self.symbol_list,
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
        if res:
            instrument = res[0]
            Agent.fill_instrument(self, instrument=instrument)

            return ""

        elif isinstance(res, str):  # error
            return res
        else:
            message = ErrorMessage.INSTRUMENT_NOT_FOUND.format(
                PATH=path, TICKER=ticker, CATEGORY=category
            )
            self.logger.warning(message)

            return message

    def fill_instrument(self, instrument: dict) -> Union[str, None]:
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
        if "settlCurrency" in instrument:
            try:
                self.currency_divisor[instrument["settlCurrency"]]
            except KeyError:
                message = ErrorMessage.NO_CURRENCY.format(
                    TICKER=instrument["symbol"], CURRENCY=instrument["settlCurrency"]
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

        if instrument["isInverse"]:  # Inverse
            valueOfOneContract = Decimal(instrument["multiplier"]) / Decimal(
                instrument["underlyingToSettleMultiplier"]
            )
            minimumTradeAmount = valueOfOneContract * Decimal(instrument["lotSize"])
            category = "inverse"
        elif instrument["isQuanto"]:  # Quanto
            valueOfOneContract = Decimal(instrument["multiplier"]) / Decimal(
                self.currency_divisor[instrument["settlCurrency"]]
            )
            minimumTradeAmount = instrument["lotSize"]
            category = "quanto"
        else:  # Linear / "Spot"
            if "underlyingToPositionMultiplier" in instrument:
                valueOfOneContract = Decimal(1) / Decimal(
                    instrument["underlyingToPositionMultiplier"]
                )
            elif instrument["underlyingToSettleMultiplier"]:
                valueOfOneContract = Decimal(instrument["multiplier"]) / Decimal(
                    instrument["underlyingToSettleMultiplier"]
                )
            minimumTradeAmount = valueOfOneContract * Decimal(instrument["lotSize"])
            if "settlCurrency" not in instrument:
                category = "spot"
            else:
                category = "linear"
        myMultiplier = Decimal(instrument["lotSize"]) / minimumTradeAmount
        if category == "spot":
            symb = instrument["underlying"] + "/" + instrument["quoteCurrency"]
        else:
            symb = instrument["symbol"]
        valueOfOneContract = float(valueOfOneContract)
        minimumTradeAmount = float(minimumTradeAmount)
        myMultiplier = int(myMultiplier)
        symbol = (symb, self.name)
        self.ticker[instrument["symbol"]] = symb
        self.Instrument[symbol].market = self.name
        self.Instrument[symbol].category = category
        self.Instrument[symbol].symbol = symb
        self.Instrument[symbol].ticker = instrument["symbol"]
        self.Instrument[symbol].myMultiplier = myMultiplier
        self.Instrument[symbol].multiplier = instrument["multiplier"]
        if category == "spot":
            self.Instrument[symbol].fundingRate = "None"
            self.Instrument[symbol].avgEntryPrice = "None"
            self.Instrument[symbol].marginCallPrice = "None"
            self.Instrument[symbol].currentQty = "None"
            self.Instrument[symbol].unrealisedPnl = "None"
        if "settlCurrency" in instrument:
            self.Instrument[symbol].settlCurrency = (
                instrument["settlCurrency"],
                self.name,
            )
        else:
            self.Instrument[symbol].settlCurrency = (
                "None",
                self.name,
            )
        self.Instrument[symbol].tickSize = instrument["tickSize"]
        self.Instrument[symbol].price_precision = service.precision(
            number=instrument["tickSize"]
        )
        self.Instrument[symbol].minOrderQty = minimumTradeAmount
        self.Instrument[symbol].qtyStep = minimumTradeAmount
        self.Instrument[symbol].precision = service.precision(minimumTradeAmount)
        self.Instrument[symbol].state = instrument["state"]
        self.Instrument[symbol].volume24h = instrument["volume24h"]
        if "expiry" in instrument:
            if instrument["expiry"]:
                self.Instrument[symbol].expire = service.time_converter(
                    time=instrument["expiry"]
                )
            else:
                self.Instrument[symbol].expire = "Perpetual"
        else:
            self.Instrument[symbol].expire = "Perpetual"
        if "fundingRate" in instrument:
            self.Instrument[symbol].fundingRate = instrument["fundingRate"] * 100
        self.Instrument[symbol].asks = [[0, 0]]
        self.Instrument[symbol].bids = [[0, 0]]
        self.Instrument[symbol].baseCoin = instrument["underlying"]
        self.Instrument[symbol].quoteCoin = instrument["quoteCurrency"]
        self.Instrument[symbol].valueOfOneContract = valueOfOneContract

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
                # order["orderQty"] *= instrument.valueOfOneContract
                # order["leavesQty"] *= instrument.valueOfOneContract
                # order["cumQty"] *= instrument.valueOfOneContract
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
