from enum import Enum


class Tips(Enum):
    SETTINGS = (
        "Make changes to the application settings. Here you can enable "
        + "or disable markets, as well as configure their connection.\n\n"
        + "After making changes, click the `Update` button. The changes "
        + "will take effect after rebooting <F3> or restarting the "
        + "application."
    )
    SQLITE_DATABASE = (
        "Your current database is located in the file {DATABASE}. You can "
        + "change this database to another one. If a database with "
        + "the assigned name does not exist, it will be created without "
        + "records. The old database will not be deleted. You can return to it "
        + "using these settings. To restore trading activity in the new "
        + "database, manage dates in the file ``history.ini``. The changes "
        + "will take effect after restarting <f3> or relaunching Tmatic."
    )
    ORDER_BOOK_DEPTH = (
        "Select ``orderBook`` for an order book depth of between 2-10 lines "
        + "for both buys and sells, or ``qoute`` which displays only the "
        + "best bid and ask quotes. Setting ``qoute`` reduces network "
        + "traffic since the amount of data received is smaller."
    )
    BOTTOM_FRAME = (
        "You can select your preferred table from `Orders`, `Positions`, "
        + "`Trades`, `Funding`, `Account`, `Results`, `Robots`, which will "
        + "always be visible at the bottom of the main page. Other tables "
        + "will be grouped in the notebook widget. The default table is "
        + "`Robots`."
    )
    REFRESH_RATE = (
        "This setting determines how often the information on the screen "
        + "is updated: from 1 to 10 times per second. This can increase "
        + "or decrease the load on your computer to some extent, depending "
        + "on its performance."
    )
    MARKET = (
        "Select or deselect the checkbox associated with the market to enable "
        + "or disable it. You can drag the row with the market up and down "
        + "to change the order in which the market is displayed."
    )
    URLS = "URLs are provided by the specific exchange in their documentation."
    HTTP_URL = URLS
    WS_URL = URLS
    TESTNET_HTTP_URL = URLS
    TESTNET_WS_URL = URLS
    API = "API keys can be obtained from the link below."
    API_KEY = API
    API_SECRET = API
    TESTNET_API_KEY = API
    TESTNET_API_SECRET = API
    TESTNET = "Select YES if you are using a test account, otherwise select NO."
    ACTIVE_STATE = "`Active` - all functions are operational. Trading is allowed."
    SUSPENDED_STATE = (
        "`Suspended` - the bot file strategy.py is loaded "
        + "into memory. All functions are operational. Trading instructions "
        + "are ignored."
    )
    DISCONNECTED_STATE = (
        "`Disconnected` - the bot file strategy.py is not " + "operational."
    )
    DOCS_NOT_PROVIDED = (
        "Documentation link not provided. See Documentation class api/setup.py"
    )
