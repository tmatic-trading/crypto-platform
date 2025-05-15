from datetime import datetime, timezone
from typing import Union

import services as service
from api.errors import Error
from api.http import Send
from common.variables import Variables as var
from display.messages import ErrorMessage, Message

from .path import Listing
from .ws import Mexc


class Agent(Mexc):
    def get_active_instruments(self) -> str:
        """
        Retrieves available trading instruments. This method can be used to
        see which instruments are available for trading, or which
        instruments have recently expired.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error.
        """
        path = Listing.GET_ACTIVE_INSTRUMENTS
        data = Send.request(self, path=path, verb="GET")

        if isinstance(data, dict):
            if "data" in data:
                if isinstance(data["data"], list):
                    for values in data["data"]:
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
                        self, index=self.instrument_index
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

    def fill_instrument(self, values: dict) -> str:
        """
        Filling the instruments data.

        The data is stored in the Instrument class using MetaInstrument class.
        The data fields of different exchanges are unified through the
        Instrument class. See detailed description of the fields there.
        """

        # Possible settleCoin {'ETH', 'USDC', 'AVAX', 'BTC', 'SUI', 'XRP',
        # 'SOL', 'ADA', 'USDT', 'LINK', 'LTC', 'DOGE'}

        if values["settleCoin"] not in ["USDC", "USDT"]:
            category = "linear"
        else:
            category = "inverse"
        symb = values["baseCoin"] + values["quoteCoin"]
        symbol = (symb, self.name)
        self.ticker[values["symbol"]] = symb
        instrument = self.Instrument.add(symbol)
        instrument.market = self.name
        instrument.symbol = symb
        instrument.ticker = values["symbol"]
        instrument.category = category
        instrument.baseCoin = values["baseCoin"]
        instrument.quoteCoin = values["quoteCoin"]
        instrument.settlCurrency = (values["settleCoin"], self.name)
        instrument.expire = "Perpetual"
        instrument.tickSize = values["priceUnit"]
        instrument.price_precision = service.precision(number=instrument.tickSize)
        instrument.minOrderQty = values["contractSize"]
        instrument.qtyStep = instrument.minOrderQty
        instrument.precision = service.precision(number=instrument.qtyStep)
        if values["state"] == 0:
            instrument.state = "Open"
        else:
            instrument.state = "Inactive"
        instrument.multiplier = 1
        instrument.myMultiplier = 1
        instrument.marginCallPrice = var.NA
        instrument.fundingRate = var.DASH
        instrument.valueOfOneContract = 1
        instrument.makerFee = values["makerFeeRate"]
        instrument.takerFee = values["takerFeeRate"]
        if category == "inverse":
            instrument.isInverse = True
        else:
            instrument.isInverse = False
        if instrument.state == "Open":
            self.instrument_index = service.fill_instrument_index(
                index=self.instrument_index, instrument=instrument, ws=self
            )

    def open_orders(self) -> str:
        path = Listing.OPEN_ORDERS
        res = Send.request(
            self,
            path=path,
            verb="GET",
        )

        print("_________res", res)

        # if isinstance(res, list):
        #     for order in res:
        #         order["symbol"] = (
        #             self.ticker[order["symbol"]],
        #             self.name,
        #         )
        #         instrument = self.Instrument[order["symbol"]]
        #         order["orderQty"] /= instrument.myMultiplier
        #         order["leavesQty"] /= instrument.myMultiplier
        #         order["cumQty"] /= instrument.myMultiplier
        #         order["transactTime"] = service.time_converter(
        #             time=order["transactTime"], usec=True
        #         )
        #         if order["symbol"] not in self.symbol_list:
        #             self.symbol_list.append(order["symbol"])
        #             message = Message.NON_SUBSCRIBED_SYMBOL_ORDER.format(
        #                 SYMBOL=order["symbol"][0]
        #             )
        #             self._put_message(message=message, warning="warning")
        # else:
        #     self.logger.error(
        #         "The list was expected when the orders were loaded, but it was not received."
        #     )
        #     return service.unexpected_error(self)
        # self.setup_orders = res

        return ""

    def activate_funding_thread(self):
        """
        Not used for Mexc.
        """
        return ""

    def trading_history(
        self, histCount: int, start_time: datetime = None, funding: bool = False
    ) -> Union[dict, str]:
        return ""
