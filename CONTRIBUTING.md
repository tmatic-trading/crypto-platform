# Contributing to Tmatic

We are grateful for your attention to the project and appreciate any contribution to the development and testing of the code, as well as any support aimed at improving and popularizing Tmatic.

> [!NOTE]
> This page is in the process of development, not final.

## Please adhere to the standards adopted when developing the Tmatic code:

- When writing code, stick to `Python 3.9+`.
- To ensure that code is well readable, `pre-commit` on your local computer according to the rules set in the `.pre-commit-config.yaml` file.
- Services for a specific exchange related to WebSocket data-feeds and REST requests should not go beyond `/api/<exchange name>/`.
- Do not go beyond the external libraries specified in the `requirements.txt` file.
- Please reference the relevant GitHub issue (if any) in your pull request comment.

## File structure

First of all, we would like to expand the number of connected exchanges. In order to develop a connector to an exchange you should look at how this is already implemented for other exchanges and repeat the file structure of the newly connected exchange as follows:

:arrow_right: `/api/<exchange name>/agent.py` - interacts with endpoints of an exchange, unifies information, making it compatible with Tmatic.

:arrow_right: `/api/<exchange name>/api_auth.py` - generates an API signature according to the description provided by a particular exchange.

:arrow_right: `/api/<exchange name>/error.py` - description of error codes of a particular exchange with assignment of their status according to Tmatic standards.

:arrow_right: `/api/<exchange name>/path.py` - endpoint addresses.

:arrow_right: `/api/<exchange name>/ws.py` - supports exchange-specific parameters, creates a web socket connection (or multiple connections according to the exchange API documentation), receives data from web socket streams and unifies these data with Tmatic standards, creates a mechanism for subscribing and unsubscribing from instruments.

## Additional functions to use in agent.py and ws.py files which can be found in the services.py file:

`display_exception` - exception trace.

`select_option_strikes` - extracts strikes from option series.

`kline_hi_lo_values` - updates kline minimums and maximums.

`time_converter` - converts time from unix format or string to datetime format.

`set_number` - assigns a dash instead of a number for a spot or if the number is 0.

`check_symbol_list` - checks for expired and non-existent instruments in the subscription.

`unexpected_error` - in some cases assigns FATAL error if any type of error is received during an http request.

`fill_instrument_index` - fills the Instrument menu with data.

`sort_instrument_index` - sorts the Instrument menu.

`precision` - determines the rounding accuracy for price and volume.

## Exchange API requirements

Since each exchange's API has its own specifics, here is a list of requirements to connect Tmatic:

#### 1. Endpoints:
- Available trading instruments
- Instrument info
- Trading history
- Klines (candlesticks)
- Open positions
- Open orders
- Account information
- Buy/sell/replace/cancel order
#### 2. Websocket streams:
- Order book
- Instrument ticker
- Execution/delivery/funding
- Orders/account/positions update
#### 3. User defined order label (clOrdID)

#### The requirements above provide for the following basic scheme of interaction between Tmatic and the exchange API:

- Get all available trading instruments

- Get all open orders

- Setup websocket streams

- Get user information

- Get wallet balance

- Get all open positions

- Download/update trading history

- Get kline data according to bots needs

- Support a stable connection to the exchange

- Send trading instruction separated by bots according to inner order accounting using clOrdID

- Receive orders execution information and distribute it among bots using clOrdID

- Store all trading, delivery and funding information in a database, allowing for records to be kept for each bot or overall for each exchange and currency, including PNL, commissions paid and funding received.

## Connect to a new exchange

Use the `api` folder to place the code, following these instructions:

Let's say you are going to connect to the `Binance`. Make sure that the Binance API meets the `Exchange API Requirements` mentioned above.

1. Create a new folder `binance`.
2. In the `binance` folder create primary files with the bare minimum set of functions and imports that might be useful:

    - Create `ws.py`:

    ```Python
    import threading
    from collections import OrderedDict

    import requests
    import websocket

    import services as service
    from api.errors import Error
    from api.init import Setup
    from api.variables import Variables
    from common.data import MetaAccount, MetaInstrument, MetaResult
    from common.variables import Variables as var
    from display.messages import Message
    from services import display_exception

    from .api_auth import API_auth
    from .error import ErrorStatus


    class Binance(Variables):
        class Account(metaclass=MetaAccount):
            pass

        class Instrument(metaclass=MetaInstrument):
            pass

        class Result(metaclass=MetaResult):
            pass

        def __init__(self):
            self.object = Binance
            self.name = "Binance"
            Setup.variables(self)
            self.session = requests.Session() # Https requests.
            self.timefrs: OrderedDict # Define the default time frames
            # set by the exchange.
            self.ws = websocket # Websocket object.
            self.logger = var.logger # Writes to logfile.log.
            self.klines = dict() # Kline (candlestick) data.
            self.setup_orders = list() # Open orders when loading.
            self.account_disp = "" # Exchange name and account number in
            # the Instrument menu.
            self.pinging: str # Used to monitor the connection using ping.
            self.ticker = dict() # Brings the classification of tickers
            # to a single standard, for example ETH_USDT (Deribit API) ->
            # ETH/USDT (Tmatic standard).
            self.instrument_index = OrderedDict() # Used in the Instrument
            # menu to classify instruments into categories and currencies.
            self.api_auth = API_auth # Generates api key headers and signature.
            self.get_error = ErrorStatus # Error codes.

        def setup_session(self):
            pass
    ```
    - Create `agent.py`:

    ```Python
    import services as service
    from api.errors import Error
    from api.http import Send
    from common.variables import Variables as var
    from display.messages import ErrorMessage, Message

    from .path import Listing
    from .ws import Binance


    class Agent(Binance):
        pass
    ```

    - Create `error.py`:

    ```Python
    from enum import Enum

    class ErrorStatus(Enum):
        RETRY = {}
        FATAL = {}
        BLOCK = {}
        IGNORE = {}
        CANCEL = {}

        def status(error):
            error_number = error["error"]["code"]
            for status in ErrorStatus:
                if error_number in status.value:
                    return status.name
    ```

    - Create `api_auth.py`:

    ```Python
    import hashlib
    import hmac
    import time
    from urllib.parse import urlparse


    class API_auth:
        def generate_headers(
            api_key: str, api_secret: str, method: str, url: str, path: str, data=None
        ) -> dict:
            """
            Called when forming a request - generates api key headers.
            Details in the exchange documentation.
            """
            headers = dict()
            """
            Place the code here.
            """

            return headers

        def generate_signature(
            secret: str, verb: str, url: str, nonce: int, data: str
        ) -> str:
            """
            Generates an API signature. Details in the exchange documentation.
            """
            signature = ""
            """
            Place the code here.
            """

            return signature
    ```

    - Create `path.py`:

    ```Python
    from enum import Enum


    class Listing(str, Enum):
        pass

        def __str__(self) -> str:
            return self.value
    ```

3. In `api/setup.py` file, add `Binance` to the relevant classes and imports.

    - Imports:

    ```Python
    from api.binance.agent import Agent as BinanceAgent
    from api.binance.ws import Binance
    ```

    - Class `MetaMarket`:

    ```Python
    class MetaMarket(type):
        dictionary = dict()
        names = {
            "Bitmex": Bitmex,
            "Bybit": Bybit,
            "Deribit": Deribit,
            "Binance": Binance,
        }

        def __getitem__(
            self, item
        ) -> Union[Bitmex, Bybit, Deribit, Binance,]:
            if item not in self.dictionary:
                if item != "Fake":
                    try:
                        self.dictionary[item] = self.names[item]()
                    except ValueError:
                        raise ValueError(f"{item} not found")
                elif item == "Fake":
                    self.dictionary[item] = Fake()

            return self.dictionary[item]
    ```

    - Class `Markets`:

    ```Python
    class Markets(
        Bitmex,
        Bybit,
        Deribit,
        Binance,
        metaclass=MetaMarket,
    ):
        pass
    ```

    - Class `Agents`:

    ```Python
    class Agents(Enum):
        Bitmex = BitmexAgent
        Bybit = BybitAgent
        Deribit = DeribitAgent
        Binance = BinanceAgent
    ```

    - At least one parameter should be added to the `Default` class:

    ```Python
    class Default(Enum):
        Binance_DEFAULT_SYMBOL = "BTCUSDT"
    ```

If you followed the instructions above, a new instance linked to Binance has been added to Tmatic. You can restart Tmatic and go to the Settings menu to verify that Binance has been added. Continue development by filling the newly added files with functions according to the exchange API documentation. Already implemented Tmatic connectors for other exchanges can be useful as examples.
