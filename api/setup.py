from enum import Enum
from typing import Union

from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit
from api.deribit.agent import Agent as DeribitAgent
from api.deribit.ws import Deribit
from api.mexc.agent import Agent as MexcAgent
from api.mexc.ws import Mexc
from api.fake import Fake


class MetaMarket(type):
    dictionary = dict()
    names = {
        "Bitmex": Bitmex,
        "Bybit": Bybit,
        "Deribit": Deribit,
        "Mexc": Mexc, 
    }

    def __getitem__(
        self, item
    ) -> Union[Bitmex, Bybit, Deribit, Mexc,]:
        if item not in self.dictionary:
            if item != "Fake":
                try:
                    self.dictionary[item] = self.names[item]()
                except ValueError:
                    raise ValueError(f"{item} not found")
            elif item == "Fake":
                self.dictionary[item] = Fake()

        return self.dictionary[item]


class Markets(
    Bitmex,
    Bybit,
    Deribit,
    Mexc, 
    metaclass=MetaMarket,
):
    pass


class Agents(Enum):
    Bitmex = BitmexAgent
    Bybit = BybitAgent
    Deribit = DeribitAgent
    Mexc = Mexc


class Default(Enum):
    """
    When adding a new exchange, all parameters except DEFAULT_SYMBOL can
    be omitted. DEFAULT_SYMBOL is required.
    """

    Bitmex_HTTP_URL = "https://www.bitmex.com/api/v1"
    Bitmex_WS_URL = "wss://ws.bitmex.com/realtime"
    Bitmex_TESTNET_HTTP_URL = "https://testnet.bitmex.com/api/v1"
    Bitmex_TESTNET_WS_URL = "wss://testnet.bitmex.com/realtime"
    Bitmex_DEFAULT_SYMBOL = "XBTUSDT"
    #
    Bybit_HTTP_URL = "https://api.bybit.com/v5"
    Bybit_WS_URL = "wss://api.bybit.com/v5"
    Bybit_TESTNET_HTTP_URL = "https://api-testnet.bybit.com/v5"
    Bybit_TESTNET_WS_URL = "wss://api-testnet.bybit.com/v5"
    Bybit_DEFAULT_SYMBOL = "BTCUSDT"
    #
    Deribit_HTTP_URL = "https://www.deribit.com"
    Deribit_WS_URL = "wss://ws.deribit.com/ws"
    Deribit_TESTNET_HTTP_URL = "https://test.deribit.com"
    Deribit_TESTNET_WS_URL = "wss://test.deribit.com/ws"
    Deribit_DEFAULT_SYMBOL = "BTC-PERPETUAL"
    #
    Mexc_HTTP_URL = "https://contract.mexc.com/api/v1"
    Mexc_WS_URL = "wss://contract.mexc.com/edge"
    Mexc_DEFAULT_SYMBOL = "BTCUSDT"


class Documentation:
    """
    When adding a new exchange, links to documentation are not required.
    They only provide additional information in the Settings menu.
    """

    docs = {
        "Bitmex": {
            "HTTP_URL": "https://www.bitmex.com/app/apiOverview",
            "WS_URL": "https://www.bitmex.com/app/apiOverview",
            "TESTNET_HTTP_URL": "https://testnet.bitmex.com/app/apiOverview",
            "TESTNET_WS_URL": "https://testnet.bitmex.com/app/apiOverview",
        },
        "Bybit": {
            "HTTP_URL": "https://bybit-exchange.github.io/docs/v5/intro",
            "WS_URL": "https://bybit-exchange.github.io/docs/v5/intro",
            "TESTNET_HTTP_URL": "https://bybit-exchange.github.io/docs/v5/intro",
            "TESTNET_WS_URL": "https://bybit-exchange.github.io/docs/v5/intro",
        },
        "Deribit": {
            "HTTP_URL": "https://docs.deribit.com/",
            "WS_URL": "https://docs.deribit.com/",
            "TESTNET_HTTP_URL": "https://docs.deribit.com/",
            "TESTNET_WS_URL": "https://docs.deribit.com/",
        },
    }
    api = {
        "Bitmex": {
            "API_KEY": "https://www.bitmex.com/app/apiKeys",
            "API_SECRET": "https://www.bitmex.com/app/apiKeys",
            "TESTNET_API_KEY": "https://testnet.bitmex.com/app/apiKeys",
            "TESTNET_API_SECRET": "https://testnet.bitmex.com/app/apiKeys",
        },
        "Bybit": {
            "API_KEY": "https://www.bybit.com/app/user/api-management",
            "API_SECRET": "https://www.bybit.com/app/user/api-management",
            "TESTNET_API_KEY": "https://testnet.bybit.com/app/user/api-management",
            "TESTNET_API_SECRET": "https://testnet.bybit.com/app/user/api-management",
        },
        "Deribit": {
            "API_KEY": "https://www.deribit.com/account/BTC/API",
            "API_SECRET": "https://www.deribit.com/account/BTC/API",
            "TESTNET_API_KEY": "https://test.deribit.com/account/BTC/API",
            "TESTNET_API_SECRET": "https://test.deribit.com/account/BTC/API",
        },
    }
