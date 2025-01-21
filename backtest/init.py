# from common.variables import Variables as var
# import threading
# from datetime import datetime, timedelta, timezone
# from time import sleep

import botinit.init as botinit
import common.init as common

# from api.bitmex.ws import Bitmex
# from api.bybit.ws import Bybit
# from api.deribit.ws import Deribit
from api.init import Setup

# import functions
# import services as service
from api.setup import Markets

# from common.data import Bots, MetaInstrument
from common.variables import Variables as var

# from display.bot_menu import bot_manager, insert_bot_log
# from display.functions import info_display
from display.settings import SettingsApp
from display.variables import Variables as disp

common.setup_database_connecion()


var.backtest = True
settings = SettingsApp(disp.settings_page)
settings.load()
market_list = var.env["MARKET_LIST"].split(",")
for market in market_list:
    ws = Markets[market]
    Setup.variables(ws)

botinit.load_bot_parameters()
