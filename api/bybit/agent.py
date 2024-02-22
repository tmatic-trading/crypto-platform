from .http import Send
from collections import OrderedDict


class Agent:
    def get_active_instruments(self) -> OrderedDict:
        pass
        #Send.request(self)