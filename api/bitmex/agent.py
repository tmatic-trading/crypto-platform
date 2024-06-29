from collections import OrderedDict
from datetime import datetime, timezone
from typing import Union

import services as service
from api.http import Send

from .path import Listing
from .ws import Bitmex

from common.variables import Variables as var


class Agent(Bitmex):
    def get_active_instruments(self) -> int:
        data = Send.request(self, path=Listing.GET_ACTIVE_INSTRUMENTS, verb="GET")
        if not isinstance(data, list):
            self.logger.error(
                "A list was expected when loading instruments, but was not received. Reboot"
            )
            return -1
        for instrument in data:
            category = Agent.fill_instrument(
                self,
                instrument=instrument,
            )
            self.symbol_category[instrument["symbol"]] = category
        if self.Instrument.get_keys():
            for symbol in self.symbol_list:
                if symbol not in self.Instrument.get_keys():
                    self.logger.error(
                        "Unknown symbol: "
                        + str(symbol)
                        + ". Check the SYMBOLS in the .env.Bitmex file. Perhaps the name of the symbol does not correspond to the category or such symbol does not exist. Reboot."
                    )
                    return -1
        else:
            self.logger.error("There are no entries in the Instrument class.")
            return -1

        return 0

    def get_user(self) -> Union[dict, None]:
        """
        Returns the user ID and other useful information about the user and
        places it in self.user. If unsuccessful, logNumFatal is not 0.
        """
        result = Send.request(self, path=Listing.GET_ACCOUNT_INFO, verb="GET")
        if result:
            self.user_id = result["id"]
            self.user = result

    def get_instrument(self, symbol: tuple):
        """
        Adds fields such as: isInverse, multiplier...
        """
        path = Listing.GET_INSTRUMENT_DATA.format(SYMBOL=symbol[0])
        res = Send.request(self, path=path, verb="GET")
        if res:
            instrument = res[0]
            category = Agent.fill_instrument(self, instrument=instrument)
            self.symbol_category[instrument["symbol"]] = category
        else:
            self.logger.info(str(symbol) + " not found in get_instrument()")

    def fill_instrument(self, instrument: dict) -> str:
        """
        Filling the instruments data.

        The data is stored in the Instrument class using MetaInstrument class.
        The data fields of different exchanges are unified through the
        Instrument class. See detailed description of the fields there.
        """
        # myMultiplier
        if instrument["isInverse"]:  # Inverse
            valueOfOneContract = (
                instrument["multiplier"] / instrument["underlyingToSettleMultiplier"]
            )
            minimumTradeAmount = valueOfOneContract * instrument["lotSize"]
            category = "inverse"
        elif instrument["isQuanto"]:  # Quanto
            valueOfOneContract = (
                instrument["multiplier"]
                / self.currency_divisor[instrument["settlCurrency"]]
            )
            minimumTradeAmount = instrument["lotSize"]
            category = "quanto"
        else:  # Linear / "Spot"
            if "underlyingToPositionMultiplier" in instrument:
                valueOfOneContract = 1 / instrument["underlyingToPositionMultiplier"]
            elif instrument["underlyingToSettleMultiplier"]:
                valueOfOneContract = (
                    instrument["multiplier"]
                    / instrument["underlyingToSettleMultiplier"]
                )
            minimumTradeAmount = valueOfOneContract * instrument["lotSize"]
            if "settlCurrency" not in instrument:
                category = "spot"
            else:
                category = "linear"
        myMultiplier = instrument["lotSize"] / minimumTradeAmount
        symbol = (instrument["symbol"], category, self.name)
        self.Instrument[symbol].category = category
        self.Instrument[symbol].symbol = instrument["symbol"]
        self.Instrument[symbol].myMultiplier = int(myMultiplier)
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
        self.Instrument[symbol].minOrderQty = instrument["lotSize"]
        self.Instrument[symbol].qtyStep = instrument["lotSize"]
        self.Instrument[symbol].precision = service.precision(
            number=self.Instrument[symbol].qtyStep / myMultiplier
        )
        self.Instrument[symbol].state = instrument["state"]
        self.Instrument[symbol].volume24h = instrument["volume24h"]
        if "expire" in instrument:
            if instrument["expire"]:
                self.Instrument[symbol].expire = service.time_converter(
                    time=instrument["expiry"]
                )
            else:
                self.Instrument[symbol].expire = "Perpetual"
        else:
            self.Instrument[symbol].expire = "None"
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
        path = Listing.GET_POSITION.format(SYMBOL=symbol[0])
        data = Send.request(self, path=path, verb="GET")
        if isinstance(data, list):
            if data:
                self.positions[symbol] = {"POS": data[0]["currentQty"]}
                self.Instrument[symbol].currentQty = data[0]["currentQty"]
            else:
                self.positions[symbol] = {"POS": 0}
            self.logger.info(
                str(symbol)
                + " has been added to the positions dictionary for "
                + self.name
            )
        else:
            self.logger.info(str(symbol) + " not found in get_position()")

    def trade_bucketed(
        self, symbol: tuple, time: datetime, timeframe: int
    ) -> Union[list, None]:
        """
        Gets timeframe data. Available time interval: 1m,5m,1h,1d.
        """
        path = Listing.TRADE_BUCKETED.format(
            TIMEFRAME=self.timefrs[timeframe], SYMBOL=symbol[0], TIME=str(time)[:19]
        )
        data = Send.request(self, path=path, verb="GET")
        if isinstance(data, list):
            filtered = []
            for values in data:
                values["symbol"] = symbol
                values["timestamp"] = service.time_converter(time=values["timestamp"])
                if "open" and "high" and "low" and "close" in values:
                    filtered.append(values)
                else:
                    message = (
                        "Klein's data of "
                        + str(symbol)
                        + " "
                        + str(values["timestamp"])
                        + " is not complete. Not received: 'open' or 'high' or 'low' or 'closed'. The line is skipped."
                    )
                    self.logger.warning(message)
                    var.queue_info.put(
                        {
                            "market": self.name,
                            "message": message,
                            "time": datetime.now(tz=timezone.utc),
                            "warning": True,
                        }
                    )
            return filtered
        else:
            return None

    def trading_history(self, histCount: int, start_time=None) -> Union[list, str]:
        if start_time:
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
                    if row["symbol"] not in self.symbol_category:
                        Agent.get_instrument(
                            self,
                            symbol=(row["symbol"], "category not defined", self.name),
                        )
                    row["market"] = self.name
                    row["category"] = self.symbol_category[row["symbol"]]
                    row["symbol"] = (
                        row["symbol"],
                        self.symbol_category[row["symbol"]],
                        self.name,
                    )
                    row["transactTime"] = service.time_converter(
                        time=row["transactTime"], usec=True
                    )
                    instrument = self.Instrument[row["symbol"]]
                    if row["symbol"][1] == "spot":
                        if row["side"] == "Buy":
                            row["settlCurrency"] = (instrument.quoteCoin, self.name)
                        else:
                            row["settlCurrency"] = (instrument.baseCoin, self.name)
                    else:
                        row["settlCurrency"] = (row["settlCurrency"], self.name)
                    if row["execType"] == "Funding":
                        if row["foreignNotional"] > 0:
                            row["lastQty"] = -row["lastQty"]
                            row["commission"] = -row["commission"]
                    row["execFee"] = None
                    if row["symbol"][1] != "spot":
                        spot_not_included.append(row)
                    else:
                        self.logger.warning(
                            "Tmatic does not support spot trading on Bitmex. The trading history entry with execID "
                            + row["execID"]
                            + " was ignored."
                        )
                return spot_not_included
            else:
                self.logNumFatal = 1001

    def open_orders(self) -> int:
        path = Listing.OPEN_ORDERS
        res = Send.request(
            self,
            path=path,
            verb="GET",
        )
        if isinstance(res, list):
            for order in res:
                order["symbol"] = (
                    order["symbol"],
                    self.symbol_category[order["symbol"]],
                    self.name,
                )
                order["transactTime"] = service.time_converter(
                    time=order["transactTime"], usec=True
                )
        else:
            self.logger.error(
                "The list was expected when the orders were loaded, but it was not received. Reboot."
            )
            return -1
        self.setup_orders = res

        return 0

    def urgent_announcement(self) -> list:
        """
        Public announcements of the exchange
        """
        path = Listing.URGENT_ANNOUNCEMENT

        return Send.request(self, path=path, verb="GET")

    def place_limit(
        self, quantity: int, price: float, clOrdID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Places a limit order
        """
        if symbol[1] == "spot":
            self.logger.warning(
                "Tmatic does not support spot trading on Bitmex. The order clOrdID "
                + clOrdID
                + " was ignored."
            )
            return
        path = Listing.ORDER_ACTIONS
        postData = {
            "symbol": symbol[0],
            "orderQty": quantity,
            "price": price,
            "clOrdID": clOrdID,
            "ordType": "Limit",
        }

        return Send.request(self, path=path, postData=postData, verb="POST")

    def replace_limit(
        self, quantity: int, price: float, orderID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Moves a limit order
        """
        path = Listing.ORDER_ACTIONS
        postData = {
            "symbol": symbol,
            "price": price,
            "orderID": orderID,
            "leavesQty": abs(quantity),
            "ordType": "Limit",
        }

        return Send.request(self, path=path, postData=postData, verb="PUT")

    def remove_order(self, order: dict) -> Union[list, None]:
        """
        Deletes an order
        """
        path = Listing.ORDER_ACTIONS
        postData = {"orderID": order["orderID"]}

        return Send.request(self, path=path, postData=postData, verb="DELETE")

    def get_wallet_balance(self):
        """
        Bitmex sends this information via websocket, "margin" subscription.
        """
        pass

    def get_position_info(self) -> None:
        """
        Gets current positions
        """
        path = Listing.GET_POSITION_INFO
        data = Send.request(self, path=path, verb="GET")
        if isinstance(data, list):
            for values in data:
                if values["symbol"] in self.symbol_category:
                    symbol = (
                        values["symbol"],
                        self.symbol_category[values["symbol"]],
                        self.name,
                    )
                    instrument = self.Instrument[symbol]
                    if "currentQty" in values:
                        instrument.currentQty = values["currentQty"]
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
            self.logger.error(
                "The list was expected when the positions were loaded, but it was not received. Reboot."
            )
            self.logNumFatal = -1
