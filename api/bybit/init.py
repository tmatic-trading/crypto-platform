from .pybit.unified_trading import HTTP
from .pybit.unified_trading import WebSocket


class Init:
    session = HTTP
    categories = ["spot", "inverse", "option", "linear"]
    ws = {"spot": WebSocket, "inverse": WebSocket, "option": WebSocket, "linear": WebSocket}
