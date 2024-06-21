import json
import os
from collections import OrderedDict
from datetime import datetime
from typing import Union

import services as service
from api.http import Send

from .path import Listing
from .ws import Deribit


class Agent(Deribit):
    def get_active_instruments(self) -> int:
        """
        Retrieves available trading instruments. This method can be used to 
        see which instruments are available for trading, or which 
        instruments have recently expired.
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
                    return 0
                else:
                    error = "A list was expected when loading instruments, but was not received. Reboot"
            else:
                error = "When loading instruments 'result' was not received."
        error = "Invalid data was received when loading tools. " + str(data)
        self.logger.error(error)

        
        return -1

    def fill_instrument(self, values: dict) -> str:
        """
        Filling the instruments data. 

        The data is stored in the Instrument class using MetaInstrument class. 
        The data fields of different exchanges are unified through the 
        Instrument class. See detailed description of the fields there.
        """
        pass
        category = values["kind"] + " " + values["instrument_type"]
        self.symbol_category[values["instrument_name"]] = category
        symbol = (values["instrument_name"], category, self.name)
        instrument = self.Instrument[symbol]
        instrument.symbol = values["instrument_name"]    
        instrument.baseCoin = values["counter_currency"]
        instrument.quoteCoin = values["quote_currency"]
        if "settlement_currency" in values:
            instrument.settlCurrency = (values["settlement_currency"], self.name)
        else:
            instrument.settlCurrency = (
                "None",
                self.name,
            )
        instrument.expire = service.time_converter(
                values["expiration_timestamp"] / 1000
            )
        if instrument.expire.year == 3000:
            instrument.expire = "Perpetual"
        instrument.tickSize = values["tick_size"]
        instrument.price_precision = service.precision(
            number=instrument.tickSize
        )
        instrument.minOrderQty = values["min_trade_amount"]
        instrument.qtyStep = values["contract_size"]
        instrument.precision = service.precision(
            number=instrument.qtyStep
        )
        if values["is_active"]:
            instrument.state = "Normal"
        else:
            instrument.state = "Inactive"
        instrument.multiplier = 1
        instrument.myMultiplier = 1
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

    def open_orders(self) -> int:
        """
        Retrieves list of user's open orders across many currencies.
        """
        msg = {
            "jsonrpc" : "2.0",
            "id" : 1953,
            "method" : "private/get_open_orders",
            "params" : {
            }
        }
        path = self.api_version + Listing.OPEN_ORDERS
        data = Send.request(self, path=path, verb="POST", postData=msg)
        if isinstance(data, dict):
            if "result" in data:
                if isinstance(data["result"], list):
                    for order in data["result"]:
                        category = self.symbol_category[order["instrument_name"]]
                        symbol = (order["instrument_name"], category, self.name)
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
                    self.setup_orders = data["result"]
                    os.abort()
                    return 0
                else:
                    error = "The list was expected when the orders were loaded, but was not received. Reboot"
            else:
                error = "When loading instruments 'result' was not received."
        error = "Invalid data was received when loading tools. " + str(data)
        self.logger.error(error)        

        return -1

        