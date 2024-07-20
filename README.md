![](https://img.shields.io/badge/Python-3.9+-blue) ![](https://img.shields.io/badge/SQLite-latest-004864)

# Cryptocurrency platform designed for automated trading on the Bitmex and Bybit crypto exchanges

![Image](https://github.com/evgrmn/tmatic/blob/main/tmaticDark.png)

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
* EMI is the identification name of the bot taken from the "clOrdID" field, usually the same as the EMI field of the SQLite "robots" table. If the "clOrdID" field is empty, then the EMI field contains the value "symbol". If the "clOrdID" field is not empty and contains an EMI, and such an EMI is not in the SQLite "robots" table, then "symbol" value is also assigned.

| execution|myBot is in the "robots" table|EMI|
| ------------- |:------------------:|:-----:|
| {"clOrdID": "1109594183.myBot", "symbol": "XBTUSD"}|yes|myBot|
| {"clOrdID": "", "symbol": "XBTUSD"}|-|XBTUSD|
| {"clOrdID": "1109594183.myBot", "symbol": "XBTUSD"}|no|XBTUSD|

* REFER - the EMI part of "clOrdID" field. E.g. REFER = "myBot" for ```{"clOrdID": "1109594183.myBot"}```
* MARKET - name of the exchange.
* CURRENCY - currency of a transaction or funding.
* TICKER - instrument symbol is the same as presented in the exchange API.
* SYMBOL - unique instrument symbol within the exchange corresponding to the ticker, with the exception of the spot category, where the symbol matches as "instrument baseCoin / instrument quoteCoin", examble "BTC/USDT".
* CATEGORY - instrument category. Possible values ​​depend on the specific exchange. Example: "linear", "inverse", "quanto", "spot", "option", etc.
* SIDE - side of a transaction: "Buy", "Sell", "Fund" - "funding".
* QTY - transaction volume.
* QTY_REST - rest of transaction volume after partial execution.
* PRICE - order price.
* THEOR_PRICE - target price.
* TRADE_PRICE - transaction price or estimated funding price. The transaction price may be better or worse than PRICE.
* SUMREAL - execution value, which is expressed in the currency of the transaction instrument and is calculated in accordance with the documentation of the exchange for each instrument.
* COMMISS - commission for completing a transaction or funding, expressed in the currency of the instrument, and is calculated in accordance with the documentation of the exchange for each instrument. A negative commission value means a rebate.
* TTIME - transaction time received from the exchange.
* DAT - time the current row was written into the database.
* CLORDID - unique order identifier assigned by user corresponding to the "clOrdID" field, which the exchange registers as an additional parameter when sending an order. For example, "1109594183.myBot" where 1109594183 is a unique order number, "myBot" after the dot is the bot name (EMI). When writing "clOrdID" to the SQLite "coins" table it is split and in this case "myBot" is written to the EMI column and 1109594183 is written to the CLORDID column. An order can be executed in parts, and by receiving information from the exchange using "clOrdID" you can understand which order is being executed and which bot placed it. The "clOrdID" field can be 0. This means that it was funding or the order was made from outside this platform where "clOrdID" was not used.
* ACCOUNT - account number.

Explanations for the columns of the SQLite "robots" table:
* EMI - bot identity name.
* TICKER - instrument symbol is the same as presented in the exchange API.
* SYMBOL - unique instrument symbol. Corresponds to TICKER except in the spot category, where SYMBOL matches as "instrument baseCoin / instrument quoteCoin", for example "BTC/USDT".
* CATEGORY - instrument category. Possible values ​​depend on the specific exchange. Example: "linear", "inverse", "quanto", "spot", "option", etc.
* MARKET - name of the exchange.
* SORT - allows you to do your own sorting when reading from the database.
* DAT - time the current row was written to the database.
* TIMEFR - timeframe that the bot uses, expressed in minutes.
* CAPITAL - financial limit for the bot expressed in the number of minimum lots. For example, the minimum lot for XBTUSD is 100USD. 10 will mean that the bot makes trades with a volume of 1000USD.
* MARGIN - margin trading leverage (not currently in use).

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

Check the variables LINEAR_SYMBOLS, INVERSE_SYMBOLS, QUANTO_SYMBOLS, SPOT_SYMBOLS, OPTION_SYMBOLS for each exchange where there must be at least one instrument symbol, for example for Bitmex: XBTUSD in INVERSE_SYMBOLS, other variables can be empty. Check the CURRENCIES variable where your account currencies should be. If your account supports multiple currencies, specify them if necessary, for example: "XBt, USDt", where XBt is Bitcoin, USDt is Tether stablecoin.

Check the ```history.ini``` file which keeps the date and time of the last transaction in the format: ```year-month-day hours:minutes:seconds``` (example ```2023-12-08 12:53:36```). You can use any date and time depending on your needs. For instance, if you want to be guaranteed to download all the transactions that were made on your current account, simply specify the year, e.g. 2000, any month, day and time. Thus, the program will download all transactions for your account starting from the very beginning. Transactions and funding will be recorded to the database in the SQLite "coins" table. Please keep in mind that **Bitmex has removed trade history prior to 2020 for [testnet.bitmex.com](https://testnet.bitmex.com) test accounts**, so if your trading activity on [testnet.bitmex.com](https://testnet.bitmex.com) was prior to 2020, you will not be able to get your entire trade history. **Bybit only supports last two years of trading history**. Its API allows trading history to be downloaded in 7-day chunks, so retrieving data for a long period may take time.

Launch the program:
- in Linux or macOS terminal ```python3 main.py```
- in Windows command prompt (cmd.exe) ```python main.py```

*If the program does not start, check the logfile.log file for errors. For example, your computer's system time may be out of sync. If your OS is Windows you should check the “Date and Time” settings: in the “Synchronize clocks” section, you must click the “Sync now” button.*

## How it works

Once the program is running, you can submit buy and sell orders by clicking on the order book, then cancel or move orders. However, the point of the program is the possibility of automatic trading around the clock in accordance with the established algorithms. You can use different algorithms for the same financial instrument, distributing balances and financial results separately for each algorithm or, to put it another way, for each bot. This feature is implemented in the program through the key parameter EMI, which is the bot’s identity name. When you submit an order through the program, you pass the "clOrdID" field to the exchange, which contains the bot's EMI. Thus, after the order is executed, when you receive the transaction parameters, there will also be a "clOrdID" field from which the program finds out the order number of your internal accounting and the bot’s EMI. Consequently, the program will calculate the financial result of a particular bot, its balance and make an entry into the database. Having the entire register of transactions in the database, each time after switching on, the program can correctly recalculate the balances for each bot. The same applies to funding. The exchange does not know anything about your internal accounting and sends funding data for the position volume for the corresponding instrument. The program distributes funding among bots in accordance with their balances.

EMI can be equal to the instrument symbol as the default name, for example, if you made a trade from the exchange web interface. In this case, the EMI may look, for example,  like ```"XBTUSD.inverse"```. When the program processes data from the ```execution``` stream or ```trade history``` endpoint and does not find a correspondence between the EMI from the "clOrdID" field and the field in the SQLite "robots" table, in this case the EMI may also be equal to the instrument symbol. Sometimes ignoring the "clOrdID" field can be useful when restoring trades to the SQLite "coins" table. This will be discussed below.

Be careful when assigning EMI to bots. Keep in mind that the "clOrdID" field will permanently store the bot's EMI in the exchange registries. You can't change it. Different instruments such as XBTUSD and XBTUSDT may have different settlement currencies such as XBt and USDt. Therefore, you should not assign the same EMI to a bot that first traded XBTUSD and then started trading XBTUSDT. The program will not be able to correctly recalculate the financial result. If you once assigned EMI="myBot" to XBTUSD, then in the future for a bot with EMI="myBot" the instrument must always have the same currency, because... It is impossible to sum XBt and USDt.

Even if you use the same EMI for different instruments but with the same currency, when switching from one instrument to another, you must ensure that the balance is zero. Let's say you traded XBTUSD and you have 100 purchased contracts left. If you change SYMBOL from XBTUSD to ETHUSD, the program will show 100 purchased contracts, but ETHUSD, which will be a mistake.

The best practice when using the program is to assign the only SYMBOL instrument to a specific EMI and never change it again for this EMI.

If there is still confusion with the purpose of EMI, you can do the following:

- Delete all entries or only unwanted rows from the SQLite "coins" table, delete all or only unwanted bots from the SQLite "robots" table.
- Change the date in the ```history.ini``` file to the date from which you want to restore transactions and funding in the database.
- Restart the program. As a result, the "coins" table will be filled with default (RESERVED) EMI for each instrument, ignoring custom values in the "clOrdID" field, which will be saved in the "REFER" column for reference.
- You can then use the program again by assigning EMI names in the "robots" table.

If you have open positions in RESERVED EMI and custom EMI at the same time and you receive funding, the program will first distribute the funding according to the custom bot positions and then write the balance to the RESERVED EMI account.

It may happen that according to your internal accounting, for example, for the XBTUSD instrument one bot has a position of -100, and the other +100. In this case, funding will not come, because the exchange has a position of 0 on its balance sheet. You have to come to terms with this fact.

What happens if you place an order from the standard exchange trading web interface? Yes, you will see this order in the program with EMI equal the instrument symbol, but only if you are subscibed to a specific instrument in ```.env.<exchange>``` file. You will be able to cancel or move this order.

It may happen that you have unclosed positions or active orders on one or another EMI, and you have already removed this EMI from the SQLite "robots" table. When you reboot, the program will find EMIs with unclosed positions or orders and add them to the list of bots with the status "NOT DEFINED". Automatic trading with these bots is not possible, but positions can be closed or orders canceled manually.

Possible bot STATUS:

* WORK - the bot is capable of performing transactions automatically. EMI is read from the SQLite "robots" table. You also can make transactions manually if trading status ```F9``` is "OFF".
* OFF - the bot is temporarily disabled from automatic mode. You can make transactions manually.
* RESERVED - all SYMBOLS from the ```.env``` files receive an additional bot instance with EMI equal to symbol and category, for example, ```"XBTUSD.inverse"```. This status allows you to make transactions manually.
* NOT DEFINED - when loading the program, a bot with a position not equal to zero or active orders was found and this bot is not in the SQLite "robots" table. Positions can be closed manually.
* NOT IN LIST - when loading the program, a bot with a position not equal to zero was found and its symbol was not found in SYMBOLS of the ```.env``` file. You cannot make trades because you're not subscribed to the symbol in the ```.env``` file. Add symbol to SYMBOLS and restart the program.

Red STATUS color is for OFF, NOT DEFINED, NOT IN LIST and for RESERVED with unclosed positions.

## Program controls

To activate automatic trading mode, use the ```F9``` key. To reboot the program, use the ```F3``` key.

Click the area in the upper right corner of the window to select the SYMBOL.

Click on the order book area to place a new order (automatic trading mode must be disabled, use ```F9```).

Click in the orders area to move an order to a different price or cancel an order.

Click in the exchange area to select an exchange.

You can disable a bot ("OFF" status) and enable it ("WORK" status) by clicking on the area with the list of bots.

## Add trading algorithm

Make a new database entry in the "robots" table, for example:

```SQL
INSERT INTO robots (
  EMI, SYMBOL, TICKER, CATEGORY, MARKET, SORT, TIMEFR, CAPITAL, MARGIN
  )
  values (
    "myBot", "XBTUSDT", "XBTUSDT", "linear", "Bitmex", 1, 1, 1, 1
    );
```

*A bot will only appear if its symbol, in this case "XBTUSDT", is included in the LINEAR_SYMBOLS variable in the ```.env.Bitmex``` file.*

Add the currency "USDt" to CURRENCIES in the ```.env.Bitmex``` file because "USDt" is the settlement currency for "XBTUSDT".

```Python
CURRENCIES = "XBt, USDt"
```

The program will download candlestick data from the exchange for the number specified in the ```CANDLESTICK_NUMBER``` constant. The data is stored in the ```frames``` dictionary and is updated as the program runs. At the same time, the ```framing``` dictionary stores timeframe parameters and a list of EMI bots that belong to this timeframe.

Let's say you want to program a simple algorithm, the essence of which is as follows: if the current price is higher than 10-periods ago, then you should buy, otherwise if the current price is lower than the price 10-periods ago, then sell. Let the bot place limit orders with an indent from the bid or offer price equal to 1/3 of the difference between the high and low of the previous period. This is just a simple example and does not claim to be a profitable strategy.

Create a file ```strategy.py``` in the ```algo``` folder:
```python
import services as service
from api.api import Markets
from common.data import Instrument
from functions import Function


def algo(robot: dict, frame: dict, instrument: Instrument) -> None:
    ws = Markets[robot["MARKET"]]
    period = robot["PERIOD"]
    quantaty = robot["lotSize"] * robot["CAPITAL"]
    emi = robot["EMI"]
    symbol = robot["SYMBOL"]
    indent = (frame[-1]["hi"] - frame[-1]["lo"]) / 3
    sell_price = service.ticksize_rounding(
        price=(instrument.asks[0][0] + indent), ticksize=instrument.tickSize
    )
    buy_price = service.ticksize_rounding(
        price=(instrument.bids[0][0] - indent), ticksize=instrument.tickSize
    )
    if frame[-1]["ask"] > frame[-1 - period]["ask"]:
        buy_quantaty = quantaty - robot["POS"]
        clOrdID = order_search(ws, emi=emi, side="Buy")
        # Move an existing order
        if clOrdID:
            if (
                buy_price != ws.orders[clOrdID]["price"]
                or buy_quantaty != ws.orders[clOrdID]["leavesQty"]
            ):
                if robot["POS"] < quantaty:
                    clOrdID = Function.put_order(
                        ws,
                        clOrdID=clOrdID,
                        price=buy_price,
                        qty=buy_quantaty,
                    )
        # Place a new order
        else:
            if robot["POS"] < quantaty:
                clOrdID = Function.post_order(
                    ws,
                    name=robot["MARKET"],
                    symbol=symbol,
                    emi=emi,
                    side="Buy",
                    price=buy_price,
                    qty=buy_quantaty,
                )
                delete_orders(ws, emi=emi, side="Sell")
    elif frame[-1]["bid"] <= frame[-1 - period]["bid"]:
        sell_quantaty = quantaty + robot["POS"]
        clOrdID = order_search(ws, emi=emi, side="Sell")
        # Move an existing order
        if clOrdID:
            if (
                sell_price != ws.orders[clOrdID]["price"]
                or sell_quantaty != ws.orders[clOrdID]["leavesQty"]
            ):
                if robot["POS"] > -quantaty:
                    clOrdID = Function.put_order(
                        ws,
                        clOrdID=clOrdID,
                        price=sell_price,
                        qty=sell_quantaty,
                    )
        # Place a new order
        else:
            if robot["POS"] > -quantaty:
                clOrdID = Function.post_order(
                    ws,
                    name=robot["MARKET"],
                    symbol=symbol,
                    emi=emi,
                    side="Sell",
                    price=sell_price,
                    qty=sell_quantaty,
                )
                delete_orders(ws, emi=emi, side="Buy")


def init_variables(robot: dict):
    robot["PERIOD"] = 10


def order_search(ws: Markets, emi: int, side: str) -> str:
    res = ""
    for clOrdID, order in ws.orders.items():
        if order["EMI"] == emi and order["SIDE"] == side:
            res = clOrdID
            break

    return res


def delete_orders(ws, emi: int, side: str) -> None:
    for clOrdID, order in ws.orders.copy().items():
        if order["EMI"] == emi and order["SIDE"] == side:
            Function.del_order(ws, order=order, clOrdID=clOrdID)

```
Launch the program:
- in Linux or macOS terminal ```python3 main.py```
- in Windows command prompt (cmd.exe) ```python main.py```

Press ```F9```

## Development

This project is under development. New functions and connections to other crypto exchanges may appear in the near future. Over time, the program interface should become more user-friendly by customizing settings through the GUI. Attention will be paid to speeding up the program, since loading two or more exchanges, as well as working with REST, requires multi-threading.
