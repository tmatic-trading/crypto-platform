from enum import Enum


class Tips(Enum):
    SQLITE_DATABASE = (
        "Your current database is {DATABASE}. You can change this database to "
        + "another one. If a database with the assigned name does not exist, "
        + "it will be created without records. The old database will not be "
        + "deleted. You can return to it using these settings. To restore "
        + "trading activity in the new database, manage dates in the "
        + "``history.ini`` file. The settings take effect after restarting "
        + "<f3> or relaunching Tmatic."
    )
    ORDER_BOOK_DEPTH = (
        "Select ``orderBook`` for an order book depth of between 10 lines "
        + "for both buys and sells, or ``qoute`` which displays only the "
        + "best bid and ask quotes. The ``qoute`` setting reduces network "
        + "traffic as the data received is smaller."
    )
    BOTTOM_FRAME = (
        "You can select your preferred table from `Orders`, `Robots`, "
        + "`Wallet`, `Trades`, `Funding`, `Result`, which will "
        + "always be visible at the bottom of the main page. Other tables "
        + "will be grouped in the notebook widget. The default table is "
        + "`Robots`."
    )
    REFRESH_RATE = (
        "This parameter determines the frequency of updating information "
        + "on the screen: from 1 to 10 times per second. This may increase "
        + "or decrease the load on your computer to some extent depending "
        + "on its performance."
    )
    URLS = "URLs are provided by the specific exchange in their documentation."
    HTTP_URL = URLS
    WS_URL = URLS
    TESTNET_HTTP_URL = URLS
    TESTNET_WS_URL = URLS
    docs = {
        "Bitmex": {
            "HTTP_URL": "www.bitmex.com/app/apiOverview",
            "WS_URL": "www.bitmex.com/app/apiOverview",
            "TESTNET_HTTP_URL": "testnet.bitmex.com/app/apiOverview",
            "TESTNET_WS_URL": "testnet.bitmex.com/app/apiOverview",
        },
        "Bybit": {
            "HTTP_URL": "bybit-exchange.github.io/docs/v5/intro",
            "WS_URL": "bybit-exchange.github.io/docs/v5/intro",
            "TESTNET_HTTP_URL": "bybit-exchange.github.io/docs/v5/intro",
            "TESTNET_WS_URL": "bybit-exchange.github.io/docs/v5/intro",
        },
        "Deribit": {
            "HTTP_URL": "docs.deribit.com/",
            "WS_URL": "docs.deribit.com/",
            "TESTNET_HTTP_URL": "docs.deribit.com/",
            "TESTNET_WS_URL": "docs.deribit.com/",
        },
    }
    API = "API keys can be obtained from the link below."
    API_KEY = API
    API_SECRET = API
    TESTNET_API_KEY = API
    TESTNET_API_SECRET = API
    api = {
        "Bitmex": {
            "API_KEY": "www.bitmex.com/app/apiKeys",
            "API_SECRET": "www.bitmex.com/app/apiKeys",
            "TESTNET_API_KEY": "testnet.bitmex.com/app/apiKeys",
            "TESTNET_API_SECRET": "testnet.bitmex.com/app/apiKeys",
        },
        "Bybit": {
            "API_KEY": "www.bybit.com/app/user/api-management",
            "API_SECRET": "www.bybit.com/app/user/api-management",
            "TESTNET_API_KEY": "testnet.bybit.com/app/user/api-management",
            "TESTNET_API_SECRET": "testnet.bybit.com/app/user/api-management",
        },
        "Deribit": {
            "API_KEY": "www.deribit.com/account/BTC/API",
            "API_SECRET": "www.deribit.com/account/BTC/API",
            "TESTNET_API_KEY": "test.deribit.com/account/BTC/API",
            "TESTNET_API_SECRET": "test.deribit.com/account/BTC/API",
        },
    }
    TESTNET = "Select YES if you are using a test account, otherwise select NO."
