###########################################################################
############################### Instructions ##############################
###########################################################################
#
#
############################### Add a market ##############################
#
# from tools import Bitmex
#
########################### Add multiple markets ##########################
#
# from tools Bitmex, Bybit, Deribit
#
############################ Get bot parameters ###########################
#
# from tools import Bot
#
# bot = Bot()
# bot.name              Bot name (str)
# bot.timefr            Timeframe expressed in minutes (int)
# bot.position          All positions opened by this bot (dict)
# bot.timefr            Kline timeframe used by bot expressed in minutes (int)
# bot.pnl               Bot's pnl divided by currencies (dict)
# bot.state             Possible values: "Suspended" or "Active" (str)
# bot.created           Bot creation time (datetime)
# bot.updated           Bot strategy file update time (datetime)
# bot.error_message     Normally "" or an error message if one occured (str)
#
############################# Get instrument ##############################
#
# btcusd = Bybit["BTCUSD"]
#
######################### Instrument parameters ###########################
#
# btcusd = Bybit["BTCUSD"]
# btcusd.asks           Orderbook asks (list)
# btcusd.bids           Orderbook bids (list)
# btcusd.asks[0]        First ask price and volume (list)
# btcusd.asks[0][0]     First ask price (float)
# btcusd.asks[0][1]     First ask volume (float)
# btcusd.category       Instrument category (str)
# btcusd.expire         Inspiration date (datetime)
# btcusd.settlCurrency  Settlement currency of the instrument (tuple)
# btcusd.qtyStep        The step to increase/reduce order quantity. Also called LotSize (float)
# btcusd.tickSize       The step to increase/reduce order price (float)
#
# The full list of instrument parameters is in the common/data.py Instrument class
#
########## Add kline (candlestick) data to a specific instrument ##########
#
# Bybit["BTCUSD"].add_kline()
#
#
###########################################################################
########################### Strategy example ##############################
###########################################################################
#
# You can try your own strategy. Connect your preferred market in the .env file, for example Bitmex. The minimum possible code to run the strategy might look like this:
#
# from tools import Bitmex
#
# def strategy():
#   pass
#
#
#
# This file is under development.
