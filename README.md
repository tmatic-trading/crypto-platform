![](https://img.shields.io/badge/Python-3.9+-blue) ![](https://img.shields.io/badge/SQLite-latest-004864)

# Cryptocurrency platform designed for automated trading on the Bitmex and Bybit crypto exchanges

![Image](https://github.com/evgrmn/tmatic/blob/main/scr/tmatic.png)

Working condition tested on Linux, Windows and macOS, Python 3.9+

This software is designed for trading on the [Bitmex.com](https://www.bitmex.com) and [Bybit.com](https://www.bybit.com) marketplaces.

API information:

| Exchange|API Overview|API Explorer|API Connector|
| ------------- | ------------- | ------------- | ------------- |
|Bitmex|[bitmex.com/app/apiOverview](https://www.bitmex.com/app/apiOverview)|[bitmex.com/api/explorer/](https://testnet.bitmex.com/api/explorer/)|[github.com/BitMEX/api-connectors](https://github.com/BitMEX/api-connectors)|
|Bybit|[bybit-exchange.github.io/docs/v5/intro](https://bybit-exchange.github.io/docs/v5/intro)|[bybit-exchange.github.io/docs/api-explorer/v5/category](https://bybit-exchange.github.io/docs/api-explorer/v5/category)|[github.com/bybit-exchange/pybit](https://github.com/bybit-exchange/pybit)|

The software allows you to monitor trading balances and make transactions manually and automatically for both Bitmex and Bybit exchanges simultaneously.

## Software Features

- Automatic placement of trade orders and tracking their execution.

- Monitoring of funding and open positions.

- Accounting in the database of all transactions, calculation of results and funding.

- Simultaneous use of any number of trading strategies for different trading instruments with separation of financial results in the database.

- Bot management feature that allows you to create, delete, merge bots and track their activity.

## Who is this software for

If you are a trader who is thinking about automating your strategies, this software can save you months of effort in creating an application that can interact with exchanges.

## Before launch

Although the software can be used for manual trading, it is mainly intended to be used for automated one, opposite to the standard exchange trading web-interface.

You can use your local computer to run the software, but for stable 24/7 operation, it is highly recommended to use a remote server. For these purposes, it is enough to subscribe to any VPS (Virtual Private Server) with 4GB of memory and several gigabytes of free disk space after installing the operating system and the required packages. To monitor the server, you can utilize the standard capabilities provided by the VPS provider or use, for example, ssh+vncviewer tools.

Python is a cross-platform programming language, so it is suitable for Windows, Linux and macOS. It is more convenient for the server to use Linux with any current distribution at the moment, e.g. Debian 11.

Before running the program on a real account, it is strongly recommended to debug it on the testnet:

- [testnet.bitmex.com](https://testnet.bitmex.com)
- [testnet.bybit.com](https://testnet.bybit.com)

A local computer is sufficient to debug the software.

## Installation on local computer

1. Create a new folder and download the program there. *This is not required, but it is recommended to install and activate the venv virtual environment to avoid installing Python packages globally.*
2. Install the packages:

```
pip3 install pycryptodome
pip3 install python-dotenv
pip3 install websocket-client
pip3 install requests
pip3 install pygments
```

*or use the command:*

```
pip3 install -r requirements.txt
```
3. The program uses an SQLite database and can work without installing a database management system. After running Tmatic for the first time, the tmatic.db file will be generated automatically. The database consists of two tables:

- ```coins``` - stores all previously executed transactions and accrued funding.
- ```robots``` - parameters of trading bots.

The "coins" table receives data from the websocket execution stream or trade history endpoint. Explanations for the columns of the "coins" table:
* ID - row number in the database.
* EXECID - unique code that exchange assigns to any transaction.
* EMI is the identification name of the bot taken from the "clOrdID" field. EMI usually corresponds to the EMI field of the SQLite "robots" table. If the "clOrdID" field is empty, then the EMI field contains the value taken from the "symbol" field. If the "clOrdID" field is not empty and contains an EMI, and such an EMI is not in the SQLite "robots" table, then "symbol" field value is also assigned.

| execution|myBot is in the "robots" table|EMI|
| ------------- |:------------------:|:-----:|
| {"clOrdID": "1109594183.myBot", "symbol": "XBTUSD"}|yes|myBot|
| {"clOrdID": "", "symbol": "XBTUSD"}|-|XBTUSD|
| {"clOrdID": "1109594183.myBot", "symbol": "XBTUSD"}|no|XBTUSD|

* REFER - the EMI part of "clOrdID" field. E.g. REFER = "myBot" for ```{"clOrdID": "1109594183.myBot"}```
* MARKET - name of the exchange.
* CURRENCY - currency of a transaction or funding.
* TICKER - instrument symbol as presented in the exchange API.
* SYMBOL - almost the same as TICKER, with exception of the spot category, where SYMBOL looks like "instrument baseCoin / instrument quoteCoin", example "BTC/USDT".
* CATEGORY - instrument category. Possible values ​​depend on the specific exchange. Example: "linear", "inverse", "quanto", "spot", "option", etc.
* SIDE - side of a transaction: "Buy", "Sell", "Fund" (funding), "Delivery" (appears when the exchange closes an open position after the instrument expires).
* QTY - transaction volume.
* QTY_REST - rest of transaction volume after partial execution.
* PRICE - order price.
* THEOR_PRICE - target price.
* TRADE_PRICE - transaction price or estimated funding price. The transaction price may be better or worse than PRICE.
* SUMREAL - execution value, which is expressed in the currency of the transaction instrument and is calculated in accordance with the documentation of the exchange for each instrument.
* COMMISS - commission for completing a transaction or funding, expressed in the currency of the instrument, and is calculated in accordance with the documentation of the exchange for each instrument. A negative commission value means a rebate.
* TTIME - transaction time received from the exchange.
* DAT - time the current row was written into the database.
* CLORDID - unique order identifier assigned by user corresponding to the "clOrdID" field, which the exchange registers as an additional parameter when sending an order. For example, clOrdID = "1109594183.myBot" where 1109594183 is a unique order number assigned by user, "myBot" after the dot is the bot name (EMI). When writing "clOrdID" to the SQLite "coins" table it is split and in this case "myBot" is written to the EMI column and 1109594183 is written to the CLORDID column. An order can be executed in parts, and by receiving information from the exchange using "clOrdID" you can understand which order is being executed and which bot placed it. The "clOrdID" field can be 0. This means that it was funding, or it was delivery, or the order was made from outside this platform where "clOrdID" was not used.
* ACCOUNT - account number.

Explanations for the columns of the SQLite "robots" table:
* EMI - bot identity name.
* SORT - allows you to do your own sorting when reading from the database.
* DAT - time the current row was written to the database.
* TIMEFR - timeframe that the bot uses. Possible values at the moment: "1min", "5min", "1h".
* STATE - Possible values: "Suspended" or "Active".
* UPDATED - Bot parameters or strategy.py file update time.

## Launch the program

It is recommended to first debug the program on the test network.

Get your API key and secret code at:
|exchange|url|
| ------------- | ------------------ |
|Bitmex|[testnet.bitmex.com/app/apiKeys](https://testnet.bitmex.com/app/apiKeys)|
|Bybit|[testnet.bybit.com/app/user/api-management](https://testnet.bybit.com/app/user/api-management)|

Create a new file named ```.env``` in the program's root folder with your settings. The file might look like this:

```python
MARKET_LIST = "Bitmex, Bybit"
SQLITE_DATABASE = "tmatic.db"
ORDER_BOOK_DEPTH = "orderBook"
REFRESH_RATE = "5"
TESTNET = "True"
```

- MARKET_LIST currently supports Bitmex and Bybit exchange.

- ORDER_BOOK_DEPTH is a choice between "orderBook" which allows you to see the order book ten lines deep, and "quote" which shows only the best buy and sell while significantly reducing network traffic.

- REFRESH_RATE refers to how often the information on the screen is refreshed, ranging from 1 to 10 times per second.

- TESTNET - choose between the main (False) and test (True) networks.

Create a new file named ```.env.Bitmex``` in the root folder of the program with your settings for the Bitmex exchange if it is in the MARKET_LIST. The file might look like this:

```python
SYMBOLS = "XBTUSDT, SOLUSDT, XBTUSD, ETHUSD"
CURRENCIES = "XBt, USDt"
HTTP_URL = "https://www.bitmex.com/api/v1/"
WS_URL = "wss://ws.bitmex.com/realtime"
API_KEY = "XXXX"
API_SECRET = "XXXX"
TESTNET_HTTP_URL = "https://testnet.bitmex.com/api/v1/"
TESTNET_WS_URL = "wss://testnet.bitmex.com/realtime"
TESTNET_API_KEY = "your testnet API key"
TESTNET_API_SECRET = "your testnet API secret"
```

Create a new file named ```.env.Bybit``` in the root folder of the program with your settings for the Bybit exchange if it is in the MARKET_LIST. The file might look like this:

```python
SYMBOLS = "BTCUSDT, ETHUSDT, BTCUSD, BTC/USDT, ETH/USDT"
CURRENCIES = "BTC, USDT"
HTTP_URL = "https://api.bybit.com/v5"
WS_URL = "wss://api.bybit.com/v5"
API_KEY = "XXXX"
API_SECRET = "XXXX"
TESTNET_HTTP_URL = "https://api-testnet.bybit.com/v5"
TESTNET_WS_URL = "wss://api-testnet.bybit.com/v5"
TESTNET_API_KEY = "your testnet API key"
TESTNET_API_SECRET = "your testnet API secret"
```

Check the variable SYMBOLS for each exchange where there must be at least one instrument symbol, for example for Bitmex: XBTUSD. Check the CURRENCIES variable where your account currencies should be. If your account supports multiple currencies, specify them if necessary, for example for Bitmex: "XBt, USDt", where XBt is Bitcoin, USDt is Tether stablecoin.

Check the ```history.ini``` file which keeps the date and time of the last transaction in the format: ```year-month-day hours:minutes:seconds``` (example ```2023-12-08 12:53:36```). You can use any date and time depending on your needs. For instance, if you want to be guaranteed to download all the transactions that were made on your current account, simply specify the year, e.g. 2000, any month, day and time. Thus, the program will download all transactions for your account starting from the very beginning. Transactions and funding will be recorded to the database in the SQLite "coins" table. Please keep in mind that **Bitmex has removed trade history prior to 2020 for [testnet.bitmex.com](https://testnet.bitmex.com) test accounts**, so if your trading activity on [testnet.bitmex.com](https://testnet.bitmex.com) was prior to 2020, you will not be able to get your entire trade history. **Bybit only supports last two years of trading history**. Its API allows trading history to be downloaded in 7-day chunks, so retrieving data for a long period may take time.

Launch the program:
- in Linux or macOS terminal ```python3 main.py```
- in Windows command prompt (cmd.exe) ```python main.py```

*If the program does not start, check the logfile.log file for errors. For example, your computer's system time may be out of sync. If your OS is Windows you should check the “Date and Time” settings: in the “Synchronize clocks” section, you must click the “Sync now” button.*

## How it works

Once the program is running, you can submit buy and sell orders by clicking on the order book, then cancel or move orders. However, the point of the program is the possibility of automatic trading around the clock in accordance with the established algorithms. You can use different algorithms for the same financial instrument, distributing balances and financial results separately for each algorithm or, to put it another way, for each bot. This feature is implemented in the program through the key parameter EMI, which is the bot’s identity name. When you submit an order through the program, you pass the "clOrdID" field to the exchange, which contains the bot's EMI. Thus, after the order is executed, when you receive the transaction parameters, there will also be a "clOrdID" field from which the program finds out the order number of your internal accounting and the bot’s EMI. Consequently, the program will calculate the financial result of a particular bot, its balance and make an entry into the database. Having the entire register of transactions in the database, each time after switching on, the program can correctly recalculate the balances for each bot.

EMI can be equal to the instrument symbol as the default name, for example, if you made a trade from the exchange web interface. In this case, the EMI may look, for example,  like ```"XBTUSD"```. When the program processes data from the ```execution``` stream or ```trade history``` endpoint and does not find a correspondence between the EMI from the "clOrdID" field and the field in the SQLite "robots" table, in this case the EMI may also be equal to the instrument symbol.

What happens if you place an order from the standard exchange trading web interface? You will see this order in the program with EMI equal the instrument symbol, but only if you are subscibed to a specific instrument in ```.env.<exchange>``` file. You will be able to cancel or move this order.

## Program controls

![Image](https://github.com/evgrmn/tmatic/blob/main/scr/control.png)

1. Use the Menu to activate the auto trading mode, or go to the Bot menu, or restart the program.

2. The information widget displays all trading operations and various useful information during the program operation, including errors if they occur.

3. The Market menu switches between exchanges, displays the connection status, account number and the number of exchange reloads due to poor connection or other reasons.

4. You can click on the order book area to place a new order. You can place an order for all available bots. Moreover, an order can be placed for a specific instrument that does not belong to any bot.

5. Click on the instrument area to switch the order book to another instrument.

6. You can choose between information blocks related to your trading activity, accounts and trading results.

![Image](https://github.com/evgrmn/tmatic/blob/main/scr/notebook.png)

- To cancel or move an order, click on the desired order in the Orders table.

7. The bots available to you are displayed in section 7. Click on a specific bot to go to the bots menu.

## Bot menu

The Bot Menu simplifies the management of bots using the GUI. The functions available in the Bot Menu:

* Add a new bot.
* Update bot's state: "Active" or "Suspended".
* Edit bot parameters.
* Merge two bots.
* Duplicate bot.
* Delete bot.
* View and edit bot's strategy.
* Check the strategy syntax.
* View bot activity, including:
    * Open orders
    * Positions
    * Trades
    * Profit/Loss for each position
    * Total results, split by currency

### Add a new bot

![Image](https://github.com/evgrmn/tmatic/blob/main/scr/newbot.png)

Currently bots can only trade on timeframes, so timeframe is the only parameter that needs to be selected. Each new bot will have its own folder in the algo folder, where the strategy.py file with the bot code is placed. To manage the bot parameters, as well as to delete the bot, use the menu on the left.

Once the bot is created, a page with current parameters will open as shown below.

![Image](https://github.com/evgrmn/tmatic/blob/main/scr/bot.png)

## Add trading algorithm

### Selecting an instrument

Once you've added a new bot, you can edit strategy.py using the Tmatic interface or, more conveniently, using an IDE like PyCharm or Visual Studio code, whichever you prefer.

The functionality for the bot is in the tools.py module, so first you need to import market from that module, for example:

```python
from tools import Bybit
```

Now you can access any Bybit instrument, such as the ```BTCUSDT``` perpetual contract:

```python
instrument = Bybit["BTCUSDT"]
```

```Bybit["BTCUSDT"]``` is a class whose full list of attributes are described below:

```python
class Instrument:
    """
    Stores data for each instrument.

    Parameters
    -----------
    asks: list
        Asks. The elements are sorted by price in ascending order. There can
        only be one element if the ORDER_BOOK_DEPTH in the .env file is
        defined as ``quote``.
    avgEntryPrice: float
        Average entry price
    baseCoin: str
        Base coin
    bids: list
        Bids. The element is sorted by price in descending order. There can
        only be one element if the ORDER_BOOK_DEPTH in the .env file is
        defined as ``quote``.
    category: str
        Possible instrument categories depend on the specific exchange.
    currentQty: float
        Position size
    expire: datetime
        Expiration time.
    fundingRate: float
        Funding rate.
    marginCallPrice: float
        Position margin call or liquidation price.
    market: str
        Exchange name.
    maxOrderQty: float
        Not used
    minOrderQty: float
        Minimum order quantity or lotsize
    multiplier: int
        :::For Bitmex only::: How much is one contract worth? You can see
        this information under the Bitmex Contract Specifications for each
        instrument. For other exchanges it is equal to 1.
    myMultiplier: int
        :::For Bitmex only::: Converts quantity when displayed on screen. For
        other exchanges it is equal to 1.
    precision: int
        Based on the ``lotSize`` of the instrument. Used to round volumes
        when displayed on the screen. For other exchanges it is equal to 1.
    price_precision: int
        Based on the ``tickSize`` of the instrument. Used to round prices
        ​​when displayed on the screen.
    qtyStep: float
        The step to increase/reduce order quantity. Also called LotSize.
    quoteCoin: str
        Quote coin.
    settlCurrency: tuple
        Settlement currency of the instrument.
    state: str
        Instrument status. Normally "Open".
    symbol: str
        A unique value corresponding to the ticker, except in the spot
        category, where the symbol matches ``baseCoin``/``quoteCoin``.
    ticker: str
        Symbol of the instrument in the exchange classification.
    tickSize: float
        The step to increase/reduce order price.
    unrealisedPnl: float
        Unrealised PnL.
    volume: float
        The total trading volume on a given account.
    volume24h: float
        Volume for 24h
    valueOfOneContract: float
        :::For Bitmex only::: Used when calculating trade value. For other
        exchanges it is equal to 1.
    """
```

So, for example, to print a list of all asks in the order book for the given instrument ```BTCUSD```, enter:

```Python
print(instrument.asks)
```

Or you can enter it in such a way that the result will be the same:

```Python
print(Bybit["BTCUSDT"].asks)
```

One bot can use multiple markets and instruments connected to Tmatic. For example, if you want ```BTCUSDT``` from Bybit and a similar instrument ```XBTUSDT``` from Bitmex, just import both markets in the strategy.py file.

```Python
from tools import Bybit, Bitmex

print(Bybit["BTCUSDT"].asks)
print(Bitmex["XBTUSDT"].asks)
```

> [!IMPORTANT]
> *To access the asks data of the Bybit ```BTCUSDT``` instrument, you must be subscribed to this instrument in the ```.env.Bybit``` file in the ```SYMBOLS``` field. The same applies to Bitmex ```XBTUSDT```. The order book data is updated via a websocket, so a subscription is required. However, to get a value such as ```qtyStep```, a subscription is not required. Such values ​​are preloaded for all available instruments after the program is launched.*

### Adding kline (candlestick) data to the instrument

#### Initialization

Exchanges support thousands of instruments. Downloading kline data and then updating it for all instruments will take a lot of resources, so Tmatic will only download the data that the trader specifies in his strategy.py files.

To get kline data for an instrument, use the add_kline() method. For example, add to your strategy.py file:

```Python
import Bitmex

kline = Bitmex["XBTUSDT"].add_kline()
```

Click ```Update strategy``` if you are in the Bot menu. Tmatic will make a request to the exchange and load the data into memory in the number of lines according to ```CANDLESTICK_NUMBER``` in the ```botinit/variables.py``` file. Then the data will be accumulated from the websocket, so in this case, a subscription to ```XBTUSDT``` in ```.env.Bitmex``` is required.

While ```Bitmex["XBTUSDT"].add_kline()``` is present in the ```strategy.py``` file, when Tmatic is launched or a specific exchange is restarted while Tmatic is running, the kline data will also be reloaded.

#### Get access to data

Each line of kline data is a dictionary:

```
"date": int
    date yymmdd, example 240814
"time": int
    time hhmmss, example 143200
"bid": float
    first bid price at the beginning of the period
"ask": float
    first ask price at the beginning of the period
"hi": float
    highest price of the period
"lo": float
    lowest price of the period
"funding": float
    funding rate for perpetual instruments
"datetime": datetime
    date and time in datetime format
```

The ```Bitmex["XBTUSDT"].add_kline()``` expression returns a callable object that can take one or two arguments, or be called without arguments.

```Python
kline = Bitmex["XBTUSDT"].add_kline()
```

1. Without arguments
```Python
kline()
```

Returns a list of data in ascending order by datetime. The last element is the data for the most recent period.

```Python
[
    {
        "date": 240820,
        "time": 120500,
        "bid": 57996.0,
        "ask": 57996.0,
        "hi": 57996.0,
        "lo": 57996.0,
        "datetime": datetime.datetime(
            2024, 8, 20, 12, 5, tzinfo=datetime.timezone.utc
        ),
    },
    ...,
    ...,
    {
        "date": 240820,
        "time": 134500,
        "bid": 63259.5,
        "ask": 63260.0,
        "hi": 63260.0,
        "lo": 63259.5,
        "funding": -0.11806,
        "datetime": datetime.datetime(
            2024, 8, 20, 13, 45, tzinfo=datetime.timezone.utc
        ),
    },
]
```

2. One argument
```Python
kline(-1)
```

Returns the data for the most recent period.

```Python
{
    "date": 240820,
    "time": 134500,
    "bid": 63259.5,
    "ask": 63260.0,
    "hi": 63260.0,
    "lo": 63259.5,
    "funding": -0.11806,
    "datetime": datetime.datetime(
        2024, 8, 20, 13, 45, tzinfo=datetime.timezone.utc
    ),
}
```

3. Two arguments. Possible values of the first argument: "date", "time", "bid", "ask", "hi", "lo", "funding", "datetime".
```Python
kline("bid", -1)
```

Returns open first bid price of the latest period.

```Python
63259.5
```

> [!NOTE]
> *All data refers to the timeframe (timefr) specified in the bot parameters.*

### Buying and Selling instructions

Timatic has only one order type - limit. If a buy order is placed above the best ask price, the trade will be executed for this ask price. The same applies to sell order.

Buy and sell orders are methods that can be called for any instrument from such classes as Bitmex or Bybit of the tools module. For more details, see ```Selecting an instrument``` above.

The syntax is as follows:

```Python
from tools import Bitmex, Bot
bot = Bot()

Bitmex["XBTUSDT"].sell(bot=bot)
```

or

```Python
Bitmex["XBTUSDT"].buy(bot=bot)
```

```Python
"""
Parameters
----------
bot: Bot
    An instance of a bot in the Bot class.
qty: float
    Order quantity. If qty is omitted, then: qty is taken as minOrderQty.
price: float
    Order price. If price is omitted, then price is taken as the current
    first offer in the order book.
move: bool
    Checks for open sell orders for the current instrument for this bot and
    if there are any, takes the last order and moves it to the new price. If
    not, places a new order.
cancel: bool
    If True, cancels all buy orders for the current instrument for this bot.

Returns
-------
str | None
    If successful, the clOrdID of this order is returned, otherwise None.
"""
```

The parameters of the sell order are described above. All parameters except ```bot``` are optional and can be omitted.

> [!NOTE]
> *The parameters of the buy order are the same, except that the price defaults to the first bid in the order book, the method moves the last buy order and cancels all sell orders accordingly.*

Examples:

```Python
import Bitmex, Bot
bot = Bot()
```

```Python
Bitmex["XBTUSD"].sell(bot=bot)
```
Sends a sell order, qty of XBTUSD ```minOrderQty``` is 100, price is equal the first ask in the order book.

```Python
Bitmex["XBTUSD"].sell(bot=bot, qty=200)
```
Sends a sell order, qty is 200, price is equal the first ask in the order book.

```Python
Bitmex["XBTUSD"].buy(bot=bot, qty=200, move=True)
```

Sends a buy order, qty is 200, price is equal the first bid in the order book. Checks for open buy orders on ```XBTUSD``` for this bot and if there are any, takes the last order and moves it to the new price. If not, places a new order.

```Python
Bitmex["XBTUSD"].buy(bot=bot, qty=200, price=50000, move=True)
```

Sends a buy order, qty is 200, price is 50000. Checks for open buy orders on ```XBTUSD``` for this bot and if there are any, takes the last order and moves it to the new price. If not, places a new order.

```Python
Bitmex["XBTUSD"].buy(bot=bot, qty=200, price=50000, move=True, cancel=True)
```

Sends a buy order, qty is 200, price is 50000. Checks for open buy orders on ```XBTUSD``` for this bot and if there are any, takes the last order and moves it to the new price. If not, places a new order. Cancels all sell orders for the ```XBTUSD``` for this bot.

#### Limits control

When an order is submitted, Tmatic does not allow the bot to exceed the set limit for the instrument. It decreases quantity if the limit is exceeded. If the limit is completely exhausted, the order will not be send to the exchange. If the bot does not have a position for this instrument, then such a position will be added to the bot, and the limit is set as default equal ```minOrderQty``` of the instrument.

Examples:

Let's say the bot is trading ```BTCUSDT``` on Bybit. ```minOrderQty``` for ```BTCUSDT``` is 0.001. The table below shows possible scenarios:

|Current position|Limit|Side|Qty|Result|
| ------------- |:-----:|:-----:|:-----:|:-----------------------------------:|
|None|None|Buy|0.001|The limit is set to 0.001. Buy order sent, qty = **0.001**|
|None|None|Buy|0.002|The limit is set to 0.001. Buy order sent, qty = **0.001**|
|0.001|0.001|Buy|0.001|Nothing happens. Buy order ignored|
|-0.001|0.001|Buy|0.002|Buy order sent, qty = **0.002**|
|-0.001|0.002|Buy|0.005|Buy order sent, qty = **0.003**|
|0.002|0.002|Sell|0.005|Sell order sent, qty = **0.004**|
|-0.001|0.002|Sell|0.005|Sell order sent, qty = **0.001**|

### Setting limits

Use ```set_limit()``` method to specify the position limits that the bot is allowed to trade on the instrument.

```Python
"""
Parameters
----------
bot: Bot
    An instance of a bot in the Bot class.
limit: float
    The limit of positions the bot is allowed to trade on this instrument.
    If this parameter is less than the instrument's minOrderQty, it
    becomes minOrderQty.
"""
```

Example:

```Python
import Bitmex, Bot
bot = Bot()

Bitmex["XBTUSDT"].set_limit(bot=bot, limit=0.003)
```

### Get limit

Use ```limit()``` method to get bot limit on the instrument.

```Python
"""
Parameters
----------
bot: Bot
    An instance of a bot in the Bot class.

Returns
-------
float
    Bot position limit for the instrument.
"""
```

Example:

```Python
import Bitmex, Bot
bot = Bot()

print(Bitmex["XBTUSDT"].limit(bot=bot))
```

```Python
0.001
```

### Get position

Use ```position()``` method to get the bot position for the given instrument.

```Python
"""
Parameters
----------
bot: Bot
    An instance of a bot in the Bot class.

Returns
-------
float
    The bot position value for the instrument.
"""
```

Example:

```Python
import Bitmex, Bot
bot = Bot()

print(Bitmex["XBTUSDT"].position(bot=bot))
```

```Python
0.001
```

### Get orders

Use the ```position()``` method to get the current open orders for a given instrument. If necessary, filter the orders by sell or buy side and sort them in ascending or descending order.

```Python
"""
Parameters
----------
bot: Bot
    An instance of a bot in the Bot class.
side: str
    The Sell or Buy side of the order. If the parameter is omitted, both 
    sides are returned.
descend: bool
    If omitted, the data is sorted in ascending order by the value of 
    ``transactTime``. If True, descending order is returned.  

Returns
-------
OrderedDict
    Orders are sorted by ``transactTime`` in the order specified in the 
    ``descend`` parameter. The OrderedDict key is the clOrdID value.
"""
```

Example:

```Python
import Bitmex, Bot
bot = Bot()

print(Bitmex["XBTUSDT"].orders(bot=bot, side="Buy"))
```

Result:

```Python
OrderedDict(
    [
        (
            "1332492130.Mybot",
            {
                "emi": "Mybot",
                "leavesQty": 0.001,
                "transactTime": datetime.datetime(
                    2024, 8, 21, 14, 7, 49, 485000, 
                                tzinfo=datetime.timezone.utc
                ),
                "price": 40000,
                "symbol": ("XBTUSDT", "Bitmex"),
                "category": "linear",
                "market": "Bitmex",
                "side": "Buy",
                "orderID": "2f27fd1f-5d45-4169-a1de-c7e2c628ce7e",
                "clOrdID": "1332492130.Mybot",
            },
        ),
        (
            "1332516744.Mybot",
            {
                "emi": "Mybot",
                "leavesQty": 0.001,
                "transactTime": datetime.datetime(
                    2024, 8, 21, 14, 49, 38, 132000, 
                                tzinfo=datetime.timezone.utc
                ),
                "price": 43000,
                "symbol": ("XBTUSDT", "Bitmex"),
                "category": "linear",
                "market": "Bitmex",
                "side": "Buy",
                "orderID": "05108401-dba7-443c-8216-d034ac25226d",
                "clOrdID": "1332516744.Mybot",
            },
        ),
    ]
)

...

### Strategy example

...



## Development

This project is under development. New functions and connections to other crypto exchanges may appear in the near future. Over time, the program interface should become more user-friendly by customizing settings through the GUI. Attention will be paid to speeding up the program, since loading two or more exchanges, as well as working with REST, requires multi-threading.
