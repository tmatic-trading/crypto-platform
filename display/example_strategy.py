###############################################################################
#                               Instructions                                  #
#                                                                             #
# 1. Add a market                                                             #
# ---------------                                                             #
#                                                                             #
# from tools import Bitmex                                                    #
#                                                                             #
# 2. Add multiple markets                                                     #
# -----------------------                                                     #
#                                                                             #
# from tools Bitmex, Bybit, Deribit                                           #
#                                                                             #
# 3. Get bot parameters                                                       #
# ---------------------                                                       #
#                                                                             #
# from tools import Bot                                                       #
# bot = Bot()                                                                 #
# bot.name           Bot name (str)                                           #
# bot.timefr         Timeframe expressed in minutes (int)                     #
# bot.bot_positions  All positions opened by this bot (dict)                  #
# bot.bot_orders     All active orders of this bot (dict)                     #
# bot.timefr         Kline timeframe used by bot expressed in minutes (int)   #
# bot.pnl            Bot's pnl separated by currencies (dict)                 #
# bot.state          Possible values: "Suspended" or "Active" (str)           #
# bot.created        Bot creation time (datetime)                             #
# bot.updated        Bot parameters or strategy.py file update time           #
#                    (datetime)                                               #
# bot.error_message  Normally "" or an error message if one occured (str)     #
#                                                                             #
# 4. Get instrument                                                           #
# -----------------                                                           #
#                                                                             #
# from tools import Bybit                                                     #
# btcusd = Bybit["BTCUSD"]                                                    #
#                                                                             #
# Instrument parameters:                                                      #
#                                                                             #
# btcusd.asks           Orderbook asks (list)                                 #
# btcusd.bids           Orderbook bids (list)                                 #
# btcusd.asks[0]        First ask price and volume (list)                     #
# btcusd.asks[0][0]     First ask price (float)                               #
# btcusd.asks[0][1]     First ask volume (float)                              #
# btcusd.category       Instrument category (str)                             #
# btcusd.expire         Inspiration date (datetime)                           #
# btcusd.settlCurrency  Settlement currency of the instrument (tuple)         #
# btcusd.qtyStep        The step to increase/reduce order quantity. Also      #
#                       called LotSize (float)                                #
# btcusd.tickSize       The step to increase/reduce order price (float)       #
#                                                                             #
# The full list of instrument parameters is in the common/data.py Instrument  #
# class                                                                       #
#                                                                             #
# 5. Add kline (candlestick) data to a specific instrument                    #
# --------------------------------------------------------                    #
#                                                                             #
# data = Bybit["BTCUSD"].add_kline()                                          #
#                                                                             #
# 6. Get kline data                                                           #
# -----------------                                                           #
#                                                                             #
# data = Bybit["BTCUSD"].add_kline()                                          #
# data[-1]             data set for the latest period (dict)                  #
# data[-1]["date"]     date of the last period in yymmdd format (int)         #
# data[-1]["time"]     time of the last period in hhmmss format (int)         #
# data[-1]["bid"]      first bid price at the beginning of the period (float) #
# data[-1]["ask"]      first ask price at the beginning of the period (float) #
# data[-1]["hi"]       highest price of the period (float)                    #
# data[-1]["lo"]       lowest price of the period (float)                     #
# data[-1]["funding"]  funding rate for perpetual instruments (float)         #
# data[-1]["datetime"] date and time in datetime format (datetime)            #
#                                                                             #
# 7. Functions related to instruments                                         #
# -----------------------------------                                         #
#                                                                             #
# <instrument>.buy()       places a limit buy order                           #
# <instrument>.sell()      places a limit sell order                          #
#                                                                             #
# 7.1. buy()                                                                  #
#   Parameters                                                                #
#   ----------                                                                #
#   qty: float (optional)                                                     #
#      Order quantity. If qty is omitted, then: qty is taken as               #
#      minOrderQty.                                                           #
#   price: float (optional)                                                   #
#      Order price. If price is omitted, then price is taken as the           #
#      current first bid in the order book.                                   #
#   move: bool (optional)                                                     #
#      Checks for open buy orders for this bot and if there are any,          #
#      takes the last buy order and moves it to the new price. If not,        #
#      places a new order.                                                    #
#  cancel: bool (optional)                                                    #
#      If True, cancels all buy orders for this bot.                          #
#  Returns                                                                    #
#  -------                                                                    #
#  str | None                                                                 #
#      If successful, the clOrdID of this order is returned, otherwise None.  #
#                                                                             #
# 7.2. sell()                                                                 #
#   The description of the buy() function also applies to the sell()          #
#   function.                                                                 #
#                                                                             #
# 8. Strategy example                                                         #
# -------------------                                                         #
#                                                                             #
# The minimum possible code to run a strategy might look like this. Let's say #
# the strategy buys when the current price is higher than the price 10        #
# periods ago, and sells when the current price is lower than or equal to the #
# price 10 periods ago. When buying, the strategy places a limit order to buy #
# at the first bid price in the order book, and does the same when selling by #
# placing a limit order at the first ask price. Instrument BTCUSDT, exchange  #
# Bybit, limit - the minimum possible quantity for the given instrument.      #
#                                                                             #
# This code is just a simple example and does not claim to be a profitable    #
# strategy.                                                                   #
#                                                                             #
# from tools import Bybit                                                     #
#                                                                             #
# instrument = Bybit["BTCUSDT"]                                               #
# kline = instrument.add_kline()                                              #
#                                                                             #
# def strategy():                                                             #
#   if kline("bid", -1) > kline("bid", -10)                                   #
#       instrument.buy(move=True, cancel=True)                                #
#   else:                                                                     #
#       insrument.sell(move=True, cancel=True)                                #
#                                                                             #
#                                                                             #
#                                                                             #
# This file is under development.                                             #
#                                                                             #
###############################################################################
