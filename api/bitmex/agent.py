from collections import OrderedDict
from datetime import datetime
from typing import Union

from api.variables import Variables

from .http import Send
from .path import Listing


class Agent(Variables):
    def get_active_instruments(self) -> OrderedDict:
        result = Send.request(self, path=Listing.GET_ACTIVE_INSTRUMENTS, verb="GET")
        if not self.logNumFatal:
            for instrument in result:
                category = Agent.fill_instrument(
                    self,
                    instrument=instrument,
                )
                self.symbol_category[instrument["symbol"]] = category
            for symbol in self.symbol_list:
                if symbol not in self.instruments:
                    self.logger.error(
                        "Unknown symbol: "
                        + str(symbol)
                        + ". Check the SYMBOLS in the .env.Bitmex file. Perhaps \
                        the name of the symbol does not correspond to the \
                        category or such symbol does not exist"
                    )
                    exit(1)
        else:
            return OrderedDict()

        return self.instruments

    def get_user(self) -> Union[dict, None]:
        return Send.request(self, path=Listing.GET_ACCOUNT_INFO, verb="GET")

    def get_instrument(self, symbol: tuple):
        """
        Adds fields such as: isInverse, multiplier...
        """
        path = Listing.GET_INSTRUMENT_DATA.format(SYMBOL=symbol[0])
        instrument = Send.request(self, path=path, verb="GET")[0]
        category = Agent.fill_instrument(self, instrument=instrument)
        self.symbol_category[instrument["symbol"]] = category

    def fill_instrument(self, instrument: dict) -> OrderedDict:
        """
        Filling the instruments dictionary with data
        """
        symbol = tuple()
        category = ""
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
        symbol = (instrument["symbol"], category)
        if symbol not in self.instruments:
            self.instruments[symbol] = dict()
        self.instruments[symbol]["myMultiplier"] = myMultiplier
        self.instruments[symbol]["category"] = category
        if symbol not in self.instruments:
            self.instruments[symbol] = dict()
        self.instruments[symbol]["symbol"] = instrument["symbol"]
        self.instruments[symbol]["multiplier"] = instrument["multiplier"]
        if "settlCurrency" in instrument:
            self.instruments[symbol]["settlCurrency"] = instrument["settlCurrency"]
        else:
            self.instruments[symbol]["settlCurrency"] = None
        self.instruments[symbol]["tickSize"] = instrument["tickSize"]
        self.instruments[symbol]["lotSize"] = instrument["lotSize"]
        if "bidPrice" in instrument:
            self.instruments[symbol]["bidPrice"] = instrument["bidPrice"]
        else:
            self.instruments[symbol]["bidPrice"] = None
        if "askPrice" in instrument:
            self.instruments[symbol]["askPrice"] = instrument["askPrice"]
        else:
            self.instruments[symbol]["askPrice"] = None
        self.instruments[symbol]["isInverse"] = instrument["isInverse"]
        if "expiry" in instrument and instrument["expiry"]:
            self.instruments[symbol]["expiry"] = datetime.strptime(
                instrument["expiry"][:-1], "%Y-%m-%dT%H:%M:%S.%f"
            )
        else:
            self.instruments[symbol]["expiry"] = "Perpetual"
        if "fundingRate" not in instrument:
            self.instruments[symbol]["fundingRate"] = None
        else:
            self.instruments[symbol]["fundingRate"] = instrument["fundingRate"]

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
        self, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, None]:
        """
        Gets timeframe data. Available time interval: 1m,5m,1h,1d.
        """
        path = Listing.TRADE_BUCKETED.format(
            TIMEFRAME=timeframe, SYMBOL=symbol[0], TIME=time
        )

        return Send.request(self, path=path, verb="GET")

    def trading_history(
        self, histCount: int, time=None) -> Union[list, str]:
        if time:
            path = Listing.TRADING_HISTORY.format(HISTCOUNT=histCount, TIME=time)
            result =  Send.request(
                self, 
                path=path, 
                verb="GET",
            )
            for row in result:
                row["symbol"] = (row["symbol"], self.symbol_category[row["symbol"]])
            return result
        else:
            return "error"
        
    def open_orders(self) -> list:
        orders = self.data["order"].values()
        for order in orders:
            order["symbol"] = (order["symbol"], self.symbol_category[order["symbol"]])

        return orders
    
    def get_ticker(self) -> OrderedDict:
        for symbol, val in self.data[self.depth].items():
            if self.depth == "quote":
                if "bidPrice" in val:
                    self.ticker[symbol]["bid"] = val["bidPrice"]
                    self.ticker[symbol]["bidSize"] = val["bidSize"]
                if "askPrice" in val:
                    self.ticker[symbol]["ask"] = val["askPrice"]
                    self.ticker[symbol]["askSize"] = val["askSize"]
            else:
                if val["bids"]:
                    self.ticker[symbol]["bid"] = val["bids"][0][0]
                    self.ticker[symbol]["bidSize"] = val["bids"][0][1]
                if val["asks"]:
                    self.ticker[symbol]["ask"] = val["asks"][0][0]
                    self.ticker[symbol]["askSize"] = val["asks"][0][1]

        return self.ticker
    

    def exit(self):
        """
        Closes websocket
        """        
        try:
            self.logNumFatal = -1
            self.ws.close()
        except Exception:
            pass