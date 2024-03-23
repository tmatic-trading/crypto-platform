from api.variables import Variables
from api.init import Setup

from .agent import Agent
from .pybit.unified_trading import HTTP
from .init import Init


class Bybit(Init, Variables):
    def __init__(self):
        pass


    def start(self):
        print("-----statr Bybit----")
        self.name = "Bybit"
        self.count = 0
        self.agent = Agent
        Setup.variables(self)
        self.session = HTTP(
        api_key=self.api_key,
        api_secret=self.api_secret,
        testnet=True,
        )
        self.instruments = self.agent.get_active_instruments(self)

    def get_active_instruments(self, symbol: tuple):
        return self.agent.get_active_instruments(self, symbol=symbol)
