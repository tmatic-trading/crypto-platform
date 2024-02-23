from .api import WS

class Websockets:
    connect = {"Bitmex": WS(), "Bybit": WS()}