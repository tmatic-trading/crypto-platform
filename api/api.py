from collections import OrderedDict

from api.bitmex.ws import Bitmex
from api.bybit.ws import Bybit

from typing import Union


class WS(Bitmex, Bybit):
    select_ws = {"Bitmex": Bitmex.start, "Bybit": Bybit.start}

    def start_ws(self, name) -> None:
        self.select_ws[name](self)

    def get_active_instruments(self) -> OrderedDict:
        """
        Gets all active instruments from the exchange REST API
        """

        return self.agent.get_active_instruments(self)
    
    def get_user(self) -> Union[dict, None]:
        """
        Gets account info
        """

        return self.agent.get_user(self)
    
    def get_instrument_data(self, symbol: tuple) -> OrderedDict:
        
        return self.agent.get_instrument_data(self, symbol=symbol)
    

class Websockets:
    connect = {"Bitmex": WS(), "Bybit": WS()}
