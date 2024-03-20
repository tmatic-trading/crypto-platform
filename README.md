![](https://img.shields.io/badge/Python-3.5+-blue) ![](https://img.shields.io/badge/MySQL-latest-167d7d)

# Trading platform designed for automated trading on the Bitmex crypto exchange

![Image](https://github.com/evgrmn/tmatic/blob/prod/timatic240320.gif)

Working condition tested on Linux, Windows and macOS, Python 3.5+

This software is designed for trading on the [Bitmex.com](https://www.bitmex.com) marketplace.

API information:

- [API Overview](https://www.bitmex.com/app/apiOverview)

- [BitMEX API Explorer](https://www.bitmex.com/api/explorer/)

- [BitMEX API Connectors](https://github.com/BitMEX/api-connectors)

The software allows you to control trade balances and make transactions manually and automatically.

## Software Features

- Automatic placement of trade orders and tracking their execution.

- Monitoring of funding and open positions.

- Accounting in the database of all transactions, calculation of results and funding.

- Simultaneous use of any number of trading strategies for different trading instruments with separation of financial results in the database.

- Keeping of all previously completed transactions and funding in the database.

## Before launch

Although the software can be used for manual trading, it is mainly intended to be used for automated one, opposite to the standard Bitmex trading web-interface.

You can use your local computer to run the software, but for stable 24/7 operation, it is highly recommended to use a remote server. For these purposes, it is enough to subscribe to any VPS (Virtual Private Server) with 4GB of memory and several gigabytes of free disk space after installing the operating system and the required packages. To monitor the server, you can utilize the standard capabilities provided by the VPS provider or use, for example, ssh+vncviewer tools.

Python is a cross-platform programming language, so it is suitable for both Windows and Linux. It is more convenient for the server to use Linux with any current distribution at the moment, e.g. Debian 11.

Before running the program on a real account, it is strongly recommended to debug it on the test circuit [testnet.bitmex.com](https://testnet.bitmex.com). A local computer is sufficient to debug the software.

## Installation on local computer

1. Create a new folder and download the program there. *This is not required, but it is recommended to install and activate the venv virtual environment to avoid installing Python packages globally.*
2. Install the packages:

```
pip3 install pymysql
pip3 install cryptography
pip3 install python-dotenv
pip3 install websocket-client
pip3 install requests
```

*or use the command:*

```
pip3 install -r requirements.txt
```

4. Install the MySQL database on your local computer by following the instructions according to your operating system.
5. Install your favorite visual tool like MySQL Workbench or something else if you need to.
6. Create a database, for example "my_db".
```SQL
CREATE DATABASE my_db;
```
7. Create SQL tables:
```SQL
CREATE TABLE my_db.coins (
  `ID` int NOT NULL AUTO_INCREMENT,
  `EXECID` varchar(45) DEFAULT NULL,
  `EMI` varchar(25) DEFAULT NULL,
  `REFER` varchar(20) DEFAULT NULL,
  `MARKET` varchar(20) DEFAULT NULL,
  `CURRENCY` varchar(10) DEFAULT NULL,
  `SYMBOL` varchar(20) DEFAULT NULL,
  `CATEGORY` varchar(10) DEFAULT NULL,
  `SIDE` tinyint DEFAULT NULL,
  `QTY` int DEFAULT NULL,
  `QTY_REST` int DEFAULT NULL,
  `PRICE` decimal(16,8) DEFAULT NULL,
  `THEOR_PRICE` decimal(16,8) DEFAULT NULL,
  `TRADE_PRICE` decimal(16,8) DEFAULT NULL,
  `SUMREAL` decimal(19,12) DEFAULT NULL,
  `COMMISS` decimal(19,15) DEFAULT '0.000000000000000',
  `TTIME` datetime DEFAULT NULL,
  `DAT` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `CLORDID` int DEFAULT '0',
  `ACCOUNT` int DEFAULT '0',
  UNIQUE KEY `ID_UNIQUE` (`ID`),
  KEY `EXECID_ix` (`EXECID`),
  KEY `EMI_QTY_ix` (`EMI`,`QTY`),
  KEY `SIDE_ix` (`SIDE`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
```
```SQL
CREATE TABLE my_db.robots (
  `EMI` varchar(20) DEFAULT NULL,
  `SYMBOL` varchar(20) DEFAULT NULL,
  `CATEGORY` varchar(10) DEFAULT NULL,
  `MARKET` varchar(20) DEFAULT NULL,
  `SORT` tinyint DEFAULT NULL,
  `DAT` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `TIMEFR` tinyint DEFAULT '0',
  `CAPITAL` int DEFAULT '0',
  `MARGIN` int DEFAULT '0'
  UNIQUE KEY `EMI_UNIQUE` (`EMI`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
```
The "coins" table is filled with data from the ```/execution``` or ```/execution/tradeHistory``` endpoints. Explanations for the columns of the “coins” table:
* ID - row number in the database.
* EXECID - unique code that Bitmex assigns to any transaction.
* EMI - identification name of a bot, the same as the EMI field of the "robots" table. This name is taken from the "clOrdID" field of ```/execution``` or ```/execution/tradeHistory``` endpoint. For example, EMI = ```"myBot"``` for ```{"clOrdID": "1109594183.myBot", "symbol": "XBTUSD"}```. If the "clOrdID" field is empty, then the EMI field contains the value "symbol" and "category" separated by a dot between them, for example ```"XBTUSD.inverse"```. If the "clOrdID" field is not empty and contains an EMI, and such an EMI is not in the "robots" table, then "symbol" value is also assigned.
* REFER - the EMI part of "clOrdID" field. E.g. REFER = "myBot" for ```{"clOrdID": "1109594183.myBot", "symbol": "XBTUSD"}```.
* MARKET - name of the exchange.
* CURRENCY - currency of a transaction or funding.
* SYMBOL - instrument symbol, for example "XBTUSD".
* CATEGORY - instrument category. Possible values: "linear", "inverse", "quanto", "spot", "option".
* SIDE - side of a transaction: 0 - "buy", 1 - "sell", -1 - "funding".
* QTY - transaction volume.
* QTY_REST - rest of transaction volume after partial execution.
* PRICE - order price.
* THEOR_PRICE - target price.
* TRADE_PRICE - transaction price or estimated funding price. The transaction price may be better or worse than PRICE.
* SUMREAL - entry/exit value, which is expressed in the currency of the transaction instrument and is calculated in accordance with the documentation of the exchange for each instrument.
* COMMISS - commission for completing a transaction or funding, expressed in the currency of the instrument, and is calculated in accordance with the documentation of the exchange for each instrument. A negative commission value means a rebate.
* TTIME - transaction time received from the exchange.
* DAT - time the current row was written to the database.
* CLORDID - unique order identifier corresponding to the "clOrdID" field, which the exchange registers as an additional parameter when sending an order. For example, "1109594183.myBot" where 1109594183 is a unique order number, "myBot" after the dot is the bot name (EMI). When writing "clOrdID" to the "coins" table it is split and in this case "myBot" is written to the EMI column and 1109594183 is written to the CLORDID column. An order can be executed in parts, and by receiving information from the exchange using "clOrdID" you can understand which order is being executed and which bot placed it. The "clOrdID" field can be 0. This means that it was funding or the order was made from outside this platform where "clOrdID" was not used.
* ACCOUNT - account number.

Explanations for the columns of the "robots" table:
* EMI - bot identity name. String format.
* SYMBOL - instrument symbol, for example "XBTUSD".
* CATEGORY - instrument category. Possible values: "linear", "inverse", "quanto", "spot", "option".
* MARKET - name of the exchange.
* SORT - allows you to do your own sorting when reading from the database.
* DAT - time the current row was written to the database.
* TIMEFR - timeframe that the bot uses, expressed in minutes.
* CAPITAL - financial limit for the bot expressed in the number of minimum lots. For example, the minimum lot for XBTUSD is 100USD. 10 will mean that the bot makes trades with a volume of 1000USD.
* MARGIN - margin trading leverage (not currently in use).

## Launch the program

It is recommended to debug the program on a test circuit [testnet.bitmex.com](https://testnet.bitmex.com)

Get your API key and secret code at [testnet.bitmex.com/app/apiKeys](https://testnet.bitmex.com/app/apiKeys)

Create a new file named ```.env``` in the program's root folder with your settings. The file might look like this:

```python
MARKET_LIST = "Bitmex"
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "your password"
MYSQL_DATABASE = "your database name"
ORDER_BOOK_DEPTH = "orderBook10"
REFRESH_RATE = "5"
TESTNET = "True"
```

- MARKET_LIST currently only supports Bitmext exchange.

- ORDER_BOOK_DEPTH is a choice between "orderBook10" which allows you to see the order book ten lines deep, and "quote" which shows only the best buy and sell while reducing network traffic by about 3 times.

- REFRESH_RATE refers to how often the information on the screen is refreshed, ranging from 1 to 10 times per second.

- TESTNET - choose between the main and test networks.

Create a new file named ```.env.Bitmex`` in the root folder of the program with your settings for the Bitmex exchange. The file might look like this:

```python
LINEAR_SYMBOLS = "XBTUSDT, SOLUSDT"
INVERSE_SYMBOLS = "XBTUSD"
QUANTO_SYMBOLS = "ETHUSD"
SPOT_SYMBOLS = ""
OPTION_SYMBOLS = ""
CURRENCIES = "XBt, USDt"
HTTP_URL = "https://www.bitmex.com/api/v1/"
WS_URL = "wss://ws.bitmex.com/realtime"
API_KEY = "your API key"
API_SECRET = "your API secret"
TESTNET_HTTP_URL = "https://testnet.bitmex.com/api/v1/"
TESTNET_WS_URL = "wss://testnet.bitmex.com/realtime"
TESTNET_API_KEY = "your testnet API key"
TESTNET_API_SECRET = "your testnet API secret"
```

Check the LINEAR_SYMBOLS, INVERSE_SYMBOLS, QUANTO_SYMBOLS, SPOT_SYMBOLS, OPTION_SYMBOLS variables where there should be at least one instrument symbol, for example XBTUSD. Check the CURRENCIES variable where your account currencies should be. If your account supports multiple currencies, specify them if necessary, for example: "XBt, USDt", where XBt is Bitcoin, USDt is Tether stablecoin.

Check the ```history.ini``` file which keeps the date and time of the last transaction in the format: ```year-month-day hours:minutes:seconds``` (example ```2023-12-08 12:53:36```). You can use any date an time depending on your needs. For example, if you want to be guaranteed to download all the transactions that were made on your current account, simply specify the year, e.g. 2000, any month, day and time. Thus, the program will download all transactions for your account starting from the very beginning. Transactions and funding will be recorded to the database in the "coins" table. Please keep in mind that **Bitmex has removed trade history prior to 2020 for [testnet.bitmex.com](https://testnet.bitmex.com) test accounts**, so if your trading activity on [testnet.bitmex.com](https://testnet.bitmex.com) was prior to 2020, you will not be able to get your entire trade history.

Launch the program:
- in Linux and macOS terminal ```python3 main.py```
- in Windows command prompt (cmd.exe) ```python main.py```

## How it works

Once the program is running, you can submit buy and sell orders by clicking on the order book, then cancel or move orders. However, the point of the program is the possibility of automatic trading around the clock in accordance with the established algorithms. You can use different algorithms for the same financial instrument, distributing balances and financial results separately for each algorithm or, to put it another way, for each bot. This feature is implemented in the program through the key parameter EMI, which is the bot’s identity name. When you submit an order through the program, you pass the "clOrdID" field to Bitmex, which contains the bot's EMI. Thus, after the order is executed, when you receive the transaction parameters, there will also be a "clOrdID" field from which the program finds out the order number of your internal accounting and the bot’s EMI. Consequently, the program will calculate the financial result of a particular bot, its balance and make an entry into the database. Having the entire register of transactions in the database, each time after switching on, the program can correctly recalculate the balances for each bot. The same applies to funding. Bitmex does not know anything about your internal accounting and sends funding data for the position volume for the corresponding instrument. The program distributes funding among bots in accordance with their balances.

EMI can be equal to the instrument symbol as the default name, for example, if you made a trade from the Bitmex web interface. In this case, the EMI may look, for example,  like ```"XBTUSD.inverse"```. When the program processes data from the ```/execution``` or ```/execution/tradeHistory``` endpoint and does not find a correspondence between the EMI from the "clOrdID" field and the field in the "robots" table, in this case the EMI may also be equal to the instrument symbol. Sometimes ignoring the "clOrdID" field can be useful when restoring trades to the "coins" table. This will be discussed below.

Be careful when assigning EMI to bots. Keep in mind that the "clOrdID" field will permanently store the bot's EMI in the Bitmex registries. You can't change it. Different instruments such as XBTUSD and XBTUSDT may have different settlement currencies such as XBt and USDt. Therefore, you should not assign the same EMI to a bot that first traded XBTUSD and then started trading XBTUSDT. The program will not be able to correctly recalculate the financial result. If you once assigned EMI="myBot" to XBTUSD, then in the future for a bot with EMI="myBot" the instrument must always have the same currency, because... It is impossible to sum XBt and USDt.

Even if you use the same EMI for different instruments but with the same currency, when switching from one instrument to another, you must ensure that the balance is zero. Let's say you traded XBTUSD and you have 100 purchased contracts left. If you change SYMBOL from XBTUSD to ETHUSD, the program will show 100 purchased contracts, but ETHUSD, which will be an error.

The best practice when using the program is to assign the only SYMBOL instrument to a specific EMI and never change it again for this EMI.

If there is still confusion with the purpose of EMI, you can do the following:

- Delete all entries or only unwanted rows from the MySQL "coins" table, delete all or only unwanted bots from the MySQL "robots" table.
- Change the date in the ```history.ini``` file to the date from which you want to restore transactions and funding in the database.
- Restart the program. As a result, the "coins" table will be filled with default (RESERVED) EMI for each instrument, ignoring custom values in the "clOrdID" field, which will be saved in the "REFER" column for reference.
- You can then use the program again by assigning EMI names in the "robots" table.

If you have open positions in RESERVED EMI and custom EMI at the same time and you receive funding, the program will first distribute the funding according to the custom bot positions and then write the balance to the RESERVED EMI account.

It may happen that according to your internal accounting, for example, for the XBTUSD instrument one bot has a position of -100, and the other +100. In this case, funding will not come, because... Bitmex has a position of 0 on its balance sheet. You have to come to terms with this fact.

What happens if you place an order from the standard Bitmex trading web interface? Yes, you will see this order in the program with EMI equal the instrument symbol, but only if you are subscibed to a specific instrument in ```.env.Bitmex``` file. You will be able to cancel or move this order.

It may happen that you have unclosed positions or active orders on one or another EMI, and you have already removed this EMI from the "robots" table. When you reboot, the program will find EMIs with unclosed positions or orders and add them to the list of bots with the status "NOT DEFINED". Automatic trading with these bots is not possible, but positions can be closed or orders canceled manually.

Possible bot STATUS:

* WORK - the bot is capable of performing transactions automatically. EMI is read from the "robots" table. You also can make transactions manually if trading status ```F9``` is "OFF".
* OFF - the bot is temporarily disabled from automatic mode. You can make transactions manually.
* RESERVED - all SYMBOLS from the ```.env.Bitmex``` file receive an additional bot instance with EMI equal to symbol and category, for example, ```"XBTUSD.inverse"```. This status allows you to make transactions manually.
* NOT DEFINED - when loading the program, a bot with a position not equal to zero or active orders was found and this bot is not in the MySQL "robots" table. Positions can be closed manually.
* NOT IN LIST - when loading the program, a bot with a position not equal to zero was found and its symbol was not found in SYMBOLS of the ```.env``` file. You cannot make trades because you're not subscribed to the symbol in the ```.env``` file. Add symbol to SYMBOLS and restart the program.

Red STATUS color can be for OFF, NOT DEFINED, NOT IN LIST or RESERVED with unclosed positions.

## Program controls

To activate automatic trading mode, use the ```F9``` key. To reboot the program, use the ```F3``` key.

Click the area in the upper right corner of the window to select the SYMBOL.

Click on the order book area to place a new order (automatic trading mode must be disabled, use ```F9```).

Click in the orders area to move an order to a different price or cancel an order.

You can disable a bot ("OFF" status) and enable it ("WORK" status) by clicking on the area with the list of bots.

## Add trading algorithm

Make a new database entry in the "robots" table, for example:

```SQL
INSERT INTO my_db.robots (
  EMI, SYMBOL, CATEGORY, MARKET, SORT, TIMEFR, CAPITAL, MARGIN
  ) 
  values (
    "myBot", "XBTUSDT", "linear", "Bitmex", 1, 1, 1, 1
    );
```

*A bot will only appear if its symbol, in this case "XBTUSDT", is included in the LINEAR_SYMBOLS variable in the ```.env.Bitmex``` file.*

Add the currency "USDt" to CURRENCIES in the ```.env.Bitmex``` file because "USDt" is the settlement currency for "XBTUSDT".

```Python
CURRENCIES = "XBt, USDt"
```

The program will download candlestick data from Bitmex for the number of days specified in the ```missing_days_number``` constant. The data is stored in the ```frames``` dictionary and is updated as the program runs. At the same time, the ```framing``` dictionary stores timeframe parameters and a list of EMI bots that belong to this timeframe.

Let's say you want to program a simple algorithm, the essence of which is as follows: if the current price is higher than 10-periods ago, then you should buy, otherwise if the current price is lower than the price 10-periods ago, then sell. Let the bot place limit orders with an indent from the bid or offer price equal to 1/3 of the difference between the high and low of the previous period. This is just a simple example and does not claim to be a profitable strategy.

1. Modify the ```init.py``` file in the ```algo``` folder:
```python
from bots.variables import Variables as bot
import algo.strategy

def init_algo():
    bot.robo["myBot"] = algo.strategy.algo
    algo.strategy.init_variables(robot=bot.robots["myBot"])
```
2. Create a file ```strategy.py``` in the ```algo``` folder:
```python
from common.variables import Variables as var
import functions as function
from functions import Function
from api.websockets import Websockets


def algo(robot: dict, frame: dict, ticker: dict, instrument: dict) -> None:
    ws = Websockets.connect[robot["MARKET"]]
    period = robot["PERIOD"]
    quantaty = (
        robot["lotSize"]
        * robot["CAPITAL"]
        * instrument["myMultiplier"]
    )
    emi = robot["EMI"]
    symbol = robot["SYMBOL"]
    indent = (frame[-1]["hi"] - frame[-1]["lo"]) / 3
    sell_price = function.ticksize_rounding(
        price=(ticker["ask"] + indent), ticksize=instrument["tickSize"]
    )
    buy_price = function.ticksize_rounding(
        price=(ticker["bid"] - indent), ticksize=instrument["tickSize"]
    )
    if frame[-1]["ask"] > frame[-1 - period]["ask"]:
        buy_quantaty = quantaty - robot["POS"]
        clOrdID = order_search(emi=emi, side="Buy")
        # Move an existing order
        if clOrdID:
            if (
                buy_price != var.orders[clOrdID]["price"]
                or buy_quantaty != var.orders[clOrdID]["leavesQty"]
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
        clOrdID = order_search(emi=emi, side="Sell")
        # Move an existing order
        if clOrdID:
            if (
                sell_price != var.orders[clOrdID]["price"]
                or sell_quantaty != var.orders[clOrdID]["leavesQty"]
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


def order_search(emi: int, side: str) -> str:
    res = ""
    for clOrdID, order in var.orders.items():
        if order["emi"] == emi and order["side"] == side:
            res = clOrdID
            break

    return res


def delete_orders(ws, emi: int, side: str) -> None:
    for clOrdID, order in var.orders.copy().items():
        if order["emi"] == emi and order["side"] == side:
            Function.del_order(ws, clOrdID=clOrdID)
```
Launch the program:
- in Linux terminal ```python3 main.py```
- in Windows command prompt (cmd.exe) ```python main.py```

Press ```F9```

## Development

This project is under development. New functions and connections to other crypto exchanges may appear in the near future.
