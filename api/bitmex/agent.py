import logging
from collections import OrderedDict
from datetime import datetime
from typing import Union

import services as service

from .http import Send
from .path import Listing
from .ws import Bitmex

# from api.variables import Variables


class Agent(Bitmex):
    logger = logging.getLogger(__name__)

    def get_active_instruments(self) -> None:
        result = Send.request(self, path=Listing.GET_ACTIVE_INSTRUMENTS, verb="GET")
        if not self.logNumFatal:
            for instrument in result:
                category = Agent.fill_instrument(
                    self,
                    instrument=instrument,
                )
                self.symbol_category[instrument["symbol"]] = category
            for symbol in self.symbol_list:
                if symbol not in self.Instrument.get_keys():
                    Agent.logger.error(
                        "Unknown symbol: "
                        + str(symbol)
                        + ". Check the SYMBOLS in the .env.Bitmex file. Perhaps "
                        + "the name of the symbol does not correspond to the "
                        + "category or such symbol does not exist."
                    )
                    exit(1)

    def get_user(self) -> Union[dict, None]:
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
            Agent.logger.info(str(symbol) + " not found in get_instrument()")

    def fill_instrument(self, instrument: dict) -> str:
        """
        Filling the instruments dictionary with data
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
        else:  # Linear
            if "underlyingToPositionMultiplier" in instrument:
                valueOfOneContract = 1 / instrument["underlyingToPositionMultiplier"]
            elif instrument["underlyingToSettleMultiplier"]:
                valueOfOneContract = (
                    instrument["multiplier"]
                    / instrument["underlyingToSettleMultiplier"]
                )
            minimumTradeAmount = valueOfOneContract * instrument["lotSize"]
            category = "linear"
        myMultiplier = instrument["lotSize"] / minimumTradeAmount
        symbol = (instrument["symbol"], category, self.name)
        self.Instrument[symbol].category = category
        self.Instrument[symbol].symbol = instrument["symbol"]
        self.Instrument[symbol].myMultiplier = int(myMultiplier)
        self.Instrument[symbol].multiplier = instrument["multiplier"]
        if "settlCurrency" in instrument:
            self.Instrument[symbol].settlCurrency = (
                instrument["settlCurrency"],
                self.name,
            )
        else:
            self.Instrument[symbol].settlCurrency = None
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
        if "expire" in instrument and instrument["expire"]:
            self.Instrument[symbol].expire = service.time_converter(
                time=instrument["expiry"]
            )
        else:
            self.Instrument[symbol].expire = "Perpetual"
        if "fundingRate" in instrument:
            self.Instrument[symbol].fundingRate = instrument["fundingRate"]
        self.Instrument[symbol].asks = [[0, 0]]
        self.Instrument[symbol].bids = [[0, 0]]

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
            Agent.logger.info(
                str(symbol)
                + " has been added to the positions dictionary for "
                + self.name
            )
        else:
            Agent.logger.info(str(symbol) + " not found in get_position()")

    def trade_bucketed(
        self, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, None]:
        """
        Gets timeframe data. Available time interval: 1m,5m,1h,1d.
        """
        path = Listing.TRADE_BUCKETED.format(
            TIMEFRAME=self.timefrs[timeframe], SYMBOL=symbol[0], TIME=str(time)[:19]
        )
        values = Send.request(self, path=path, verb="GET")
        for value in values:
            value["symbol"] = symbol
            value["timestamp"] = service.time_converter(time=value["timestamp"])

        return values

    def trading_history(self, histCount: int, time=None) -> Union[list, str]:
        if time:
            path = Listing.TRADING_HISTORY.format(
                HISTCOUNT=histCount, TIME=str(time)[:19]
            )
            result = Send.request(
                self,
                path=path,
                verb="GET",
            )
            for row in result:
                if row["symbol"] not in self.symbol_category:
                    Agent.get_instrument(
                        self, symbol=(row["symbol"], "category not defined", self.name)
                    )
                row["market"] = self.name
                row["symbol"] = (
                    row["symbol"],
                    self.symbol_category[row["symbol"]],
                    self.name,
                )
                row["transactTime"] = service.time_converter(
                    time=row["transactTime"], usec=True
                )
                row["settlCurrency"] = (row["settlCurrency"], self.name)
                if row["execType"] == "Funding":
                    if row["foreignNotional"] > 0:
                        row["lastQty"] = -row["lastQty"]
                        row["commission"] = -row["commission"]
            return result
        else:
            return "error"

    def open_orders(self) -> list:
        orders = self.data["order"].values()
        for order in orders:
            order["symbol"] = (
                order["symbol"],
                self.symbol_category[order["symbol"]],
                self.name,
            )
            order["transactTime"] = service.time_converter(
                time=order["transactTime"], usec=True
            )

        return orders

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
        res = Send.request(self, path=path, verb="GET")
        for values in res:
            if values["symbol"] in self.symbol_category:
                symbol = (
                        values["symbol"],
                        self.symbol_category[values["symbol"]],
                        self.name,
                    )            
                if symbol in self.symbol_list:
                    instrument = self.Instrument[symbol]
                    if "currentQty" in values:
                        instrument.currentQty = values["currentQty"]
                    if instrument.currentQty != 0:
                        if "avgEntryPrice" in values:
                            instrument.avgEntryPrice = values["avgEntryPrice"]
                        if "marginCallPrice" in values:
                            instrument.marginCallPrice = values["marginCallPrice"]
                        if "unrealisedPnl" in values:
                            instrument.unrealisedPnl = values["unrealisedPnl"]

