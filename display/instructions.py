#                               Instructions
#
# 1. Add a market
# ---------------
#
# from tools import Bitmex
#
#
# 2. Add multiple markets
# -----------------------
#
# from tools Bitmex, Bybit, Deribit
#
#
# 3. Get bot parameters
# ---------------------
#
# from tools import Bot
# bot = Bot()
# bot.name           Bot name (str)
# bot.timefr         Timeframe expressed in minutes (int)
# bot.bot_positions  All positions opened by this bot (dict)
# bot.bot_orders     All active orders of this bot (dict)
# bot.timefr         Kline timeframe used by bot expressed in minutes (int)
# bot.pnl            Bot's pnl separated by currencies (dict)
# bot.state          Possible values: "Suspended" or "Active" (str)
# bot.created        Bot creation time (datetime)
# bot.updated        Bot parameters or strategy.py file update time (datetime)
# bot.error_message  Normally "" or an error message if one occured (str)
#
#
# 4. Get instrument
# -----------------
#
# from tools import Bybit
# btcusd = Bybit["BTCUSD"]
#
# Instrument parameters:
#
# btcusd.asks           Orderbook asks (list)
# btcusd.bids           Orderbook bids (list)
# btcusd.asks[0]        First ask price and volume (list)
# btcusd.asks[0][0]     First ask price (float)
# btcusd.asks[0][1]     First ask volume (float)
# btcusd.category       Instrument category (str)
# btcusd.expire         Inspiration date (datetime)
# btcusd.settlCurrency  Settlement currency of the instrument (tuple)
# btcusd.qtyStep        The step to increase/reduce order quantity. Also
#                       called LotSize (float)
# btcusd.tickSize       The step to increase/reduce order price (float)
#
# The full list of instrument parameters is in the common/data.py Instrument
# class
#
#
# 5. Add kline (candlestick) data to a specific instrument
# --------------------------------------------------------
#
# data = Bybit["BTCUSD"].add_kline()
#
#
# 6. Get kline data
# -----------------
#
# data = Bybit["BTCUSD"].add_kline()
# data(-1)             data set for the latest period (dict)
# data("date", -1)     date of the last period in yymmdd format (int)
# data["time", -1)     time of the last period in hhmmss format (int)
# data("open_bid", -1)      first bid price at the beginning of the period (float)
# data("open_ask", -1)      first ask price at the beginning of the period (float)
# data("hi", -1)       highest price of the period (float)
# data("lo", -1)       lowest price of the period (float)
# data("funding", -1)  funding rate for perpetual instruments (float)
# data("datetime", -1) date and time in datetime format (datetime)
#
# Index -1 refers to the most recent period, -2 to the period before the most
# recent, and so on.
#
#
# 7. Functions related to instruments
# -----------------------------------
#
# <instrument>.buy()       places a limit buy order.
# <instrument>.sell()      places a limit sell order.
# <instrument>.set_limit() specifies the position limits.
# <instrument>.limit()     gets the bot limit for the given instrument.
# <instrument>.position()  gets the position for the given instrument.
# <instrument>.orders()    gets the current open orders for a given instrument.
#
# 7.1. buy()
#   Parameters
#   ----------
#   bot: Bot
#      An instance of a bot in the Bot class.
#   qty: float (optional)
#      Order quantity. If qty is omitted, then: qty is taken as
#      minOrderQty.
#   price: float (optional)
#      Order price. If price is omitted, then price is taken as the
#      current first bid in the order book.
#   move: bool (optional)
#      Checks for open buy orders for this bot and if there are any,
#      takes the last buy order and moves it to the new price. If not,
#      places a new order.
#  cancel: bool (optional)
#      If True, cancels all buy orders for this bot.
#  Returns
#  -------
#  str | None
#      If successful, the clOrdID of this order is returned, otherwise None.
#
# 7.2. sell()
#   The description of the buy() function also applies to the sell()
#   function.
#
# Example:
#
# Bitmex["XBTUSDT"].sell(bot=bot, move=True, cancel=True)
#
# 7.3 set_limit()
#
# Use set_limit() method to specify the position limits that the bot is
# allowed to trade on the instrument:
#
# Bitmex["XBTUSDT"].set_limit(bot=bot, limit=0.003)
#
# 7.4 limit()
#
# This method allows you to get the instrument limit for a specific bot.
#
# Parameters
# ----------
# bot: Bot
#     An instance of a bot in the Bot class.
#
# Returns
# -------
# float
#     Bot position limit for the instrument.
#
# Example:
#
# import Bitmex, Bot
# bot = Bot()
#
# limit = Bitmex["XBTUSDT"].limit(bot=bot)
#
# 7.5 position()
#
# Gets the bot position for the given instrument.
#
# Parameters
# ----------
# bot: Bot
#     An instance of a bot in the Bot class.
#
# Returns
# -------
# float
#     The bot position value for the instrument.
#
# Example:
#
# import Bitmex, Bot
# bot = Bot()
#
# position = Bitmex["XBTUSDT"].position(bot=bot))
#
# 7.6 orders()
#
# Gets the current open orders for a given instrument. If necessary, it
# filters the orders by sell or buy side and sort them in descending
# order.
#
# Parameters
# ----------
# bot: Bot
#     An instance of a bot in the Bot class.
# side: str
#     The Sell or Buy side of the order. If the parameter is omitted, both
#     sides are returned.
# descend: bool
#     If omitted, the data is sorted in ascending order by the value of
#     ``transactTime``. If True, descending order is returned.
#
# Returns
# -------
# OrderedDict
#     Orders are sorted by ``transactTime`` in the order specified in the
#     ``descend`` parameter. The OrderedDict key is the clOrdID value.
#
# Example:
#
# import Bitmex, Bot
# bot = Bot()
#
# orders = Bitmex["XBTUSDT"].orders(bot=bot, side="Buy")
#
#
# 8. Functions related to the Bot class
# -------------------------------------
#
# <bot>.remove()        deletes an open order by its clOrdID.
# <bot>.replace()       moves an open order to a new price using its clOrdID.
#
# 8.1. remove()
#
# Parameters:
# -----------
# bot: Bot
#    An instance of a bot in the Bot class.
# clOrdID: str
#    Order ID. Example: "1348642035.Super"
#
# Example: This example shows how to place a sell order at the first ask
# price and remove it in 5 seconds.
#
# import time
# import Bitmex, Bot
#
# bot = Bot()
#
# id = Bitmex["XBTUSDT"].sell(bot=bot)
# time.sleep(5)
# bot.remove(clOrdID=id)
#
# 8.2. replace()
#
# Parameters
# ----------
# bot: Bot
#     An instance of a bot in the Bot class.
# clOrdID: str
#     Order ID. Order ID. Example: "1348642035.Super"
# price: float
#     New price to reset order to.
#
# Returns
# -------
# str | None
#     On success, clOrdID is returned, otherwise an error type.
#
# Example: This example shows how to place a sell order at the first ask
# price and move it to the first ask price + 100 in 5 seconds.
#
# import time
# import Bitmex, Bot
#
# bot = Bot()
# instrument = Bitmex["XBTUSDT"]
#
# id = instrument.sell(bot=bot)
# time.sleep(5)
# price = instrument.asks[0][0] + 100
# bot.replace(clOrdID=id, price=price)
#
#
# 9. Strategy example
# -------------------
#
# The minimum possible code to run a strategy might look like this. Let's say
# the strategy buys when the current price is higher than the price 10
# periods ago, and sells when the current price is lower than or equal to the
# price 10 periods ago. When buying, the strategy places a limit order to buy
# at the first bid price in the order book, and does the same when selling by
# placing a limit order at the first ask price. Instrument BTCUSDT, exchange
# Bybit, limit - the minimum possible quantity for the given instrument.
#
# This code is just a simple example and does not claim to be a profitable
# strategy.
#
# from tools import Bybit, Bot
#
# bot = Bot()
# instrument = Bybit["BTCUSDT"]
# kline = instrument.add_kline()
#
# def strategy():
#   if kline("bid", -1) > kline("open_bid", -10):
#       instrument.buy(bot=bot, move=True, cancel=True)
#   else:
#       instrument.sell(bot=bot, move=True, cancel=True)
#
#
#
