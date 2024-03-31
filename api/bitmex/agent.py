from collections import OrderedDict
from datetime import datetime
from typing import Union

#from api.variables import Variables

from .http import Send
from .path import Listing

from .ws import Bitmex
import services as service

import logging


class Agent(Bitmex):
    logger = logging.getLogger(__name__)

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
                    Agent.logger.error(
                        "Unknown symbol: "
                        + str(symbol)
                        + ". Check the SYMBOLS in the .env.Bitmex file. Perhaps "
                        + "the name of the symbol does not correspond to the "
                        + "category or such symbol does not exist"
                    )
                    exit(1)
        else:
            return OrderedDict()
        return self.instruments

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
        self.instruments[symbol]["myMultiplier"] = int(myMultiplier)
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
        self.instruments[symbol]["state"] = instrument["state"]
        self.instruments[symbol]["volume24h"] = instrument["volume24h"]
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
            self.instruments[symbol]["expiry"] = service.time_converter(
                time=instrument["expiry"]
            )
        else:
            self.instruments[symbol]["expiry"] = "Perpetual"
        if "fundingRate" not in instrument:
            self.instruments[symbol]["fundingRate"] = 0
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
            TIMEFRAME=timeframe, SYMBOL=symbol[0], TIME=time
        )

        return Send.request(self, path=path, verb="GET")

    def trading_history(self, histCount: int, time=None) -> Union[list, str]:
        if time:
            path = Listing.TRADING_HISTORY.format(HISTCOUNT=histCount, TIME=time)
            result = Send.request(
                self,
                path=path,
                verb="GET",
            )
            for row in result:
                row["market"] = self.name
                row["symbol"] = (row["symbol"], self.symbol_category[row["symbol"]])
            return result
        else:
            return "error"

    def open_orders(self) -> list:
        orders = self.data["order"].values()
        for order in orders:
            order["symbol"] = (order["symbol"], self.symbol_category[order["symbol"]])
            order["transactTime"] = service.time_converter(time=order["transactTime"], usec=True)

        return orders

    def get_ticker(self) -> OrderedDict:
        
        return service.fill_ticker(self, depth=self.depth, data=self.data)


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

    def remove_order(self, orderID: str) -> Union[list, None]:
        """
        Deletes an order
        """
        path = Listing.ORDER_ACTIONS
        postData = {"orderID": orderID}

        return Send.request(self, path=path, postData=postData, verb="DELETE")
    
    def get_wallet_balance(self):
        """
        Bitmex sends this information via websocket, "margin" subscription.
        """
        pass
    
    def get_position_info(self):
        """
        Bitmex sends this information via websocket, "position" subscription.
        """
        pass

    #del 
    '''def exit(self):
        """
        Closes websocket
        """
        try:
            self.logNumFatal = -1
            self.ws.close()
        except Exception:
            pass'''
