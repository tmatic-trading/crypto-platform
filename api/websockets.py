from .api import WS
from .bybit.ws import Bybit
from .bitmex.ws import Bitmex

class Websockets:
    #connect = {"Bitmex": WS(Bitmex()), "Bybit": WS(Bybit())}
    connect = {"Bitmex": WS(), "Bybit": WS()}