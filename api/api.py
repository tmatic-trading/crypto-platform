from collections import OrderedDict
from typing import Union

from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit


class WS(Bitmex, Bybit):
    select_ws = {"Bitmex": Bitmex.start, "Bybit": Bybit.start}
    agent_get_active_instruments = {
        "Bitmex": BitmexAgent.get_active_instruments,
        "Bybit": BybitAgent.get_active_instruments,
    }
    agent_get_user = {"Bitmex": BitmexAgent.get_user, "Bybit": BybitAgent.get_user}
    agent_get_instrument = {
        "Bitmex": BitmexAgent.get_instrument,
        "Bybit": BybitAgent.get_instrument,
    }
    agent_get_position = {
        "Bitmex": BitmexAgent.get_position,
        "Bybit": BybitAgent.get_position,
    }

    def start_ws(self, name) -> None:
        self.select_ws[name](self)

    def get_active_instruments(self, name) -> OrderedDict:
        """
        Gets all active instruments from the exchange REST API
        """

        return self.agent_get_active_instruments[name](self)

    def get_user(self, name) -> Union[dict, None]:
        """
        Gets account info
        """

        return self.agent_get_user[name](self)

    def get_instrument(self, name, symbol: tuple) -> None:

        return self.agent_get_instrument[name](self, symbol=symbol)
    
    def get_position(self, name, symbol: tuple) -> None:

        return self.agent_get_position[name](self, symbol=symbol)


