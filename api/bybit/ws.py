from api.variables import Variables
from .agent import Agent


class Bybit(Variables):
    def __init__(self):
        pass
    def start(self):
        self.agent = Agent

    def get_active_instruments(self, symbol: tuple):
        
        return self.agent.get_active_instruments(self, symbol=symbol)
