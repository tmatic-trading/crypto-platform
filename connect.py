import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from time import sleep

import algo.init as algo
import bots.init as bots
import common.init as common
import functions
import services as service
from api.api import WS, Markets
from api.bitmex.ws import Bitmex
from api.bybit.ws import Bybit
from common.variables import Variables as var
from display.functions import info_display
from display.variables import Tables
from display.variables import Variables as disp
from functions import Function, funding, orders, trades


def setup():
    disp.root.bind("<F3>", lambda event: terminal_reload(event))
    disp.root.bind("<F9>", lambda event: trade_state(event))
    Bitmex.transaction = Function.transaction
    Bybit.transaction = Function.transaction
    clear_params()
    common.setup_database_connecion()
    var.robots_thread_is_active = False
    for name in var.market_list:
        setup_market(Markets[name])
    functions.load_labels()
    var.robots_thread_is_active = True
    thread = threading.Thread(target=robots_thread)
    thread.start()


def setup_market(ws: Markets):
    ws.logNumFatal = -1
    ws.api_is_active = False
    WS.exit(ws)
    while ws.logNumFatal:
        ws.logNumFatal = -1
        WS.start_ws(ws)
        WS.get_user(ws)
        WS.get_wallet_balance(ws)
        WS.get_position_info(ws)
        if ws.logNumFatal:
            WS.exit(ws)
            sleep(2)
        else:
            common.Init.clear_params(ws)
            if bots.Init.load_robots(ws):
                algo.init_algo(ws)
                if isinstance(bots.Init.init_timeframes(ws), dict):
                    trades.clear_columns(market=ws.name)
                    funding.clear_columns(market=ws.name)
                    orders.clear_columns(market=ws.name)
                    common.Init.load_database(ws)
                    common.Init.load_trading_history(ws)
                    common.Init.account_balances(ws)
                    common.Init.load_orders(ws)
                    bots.Init.delete_unused_robot(ws)
                    for emi, value in ws.robot_status.items():
                        ws.robots[emi]["STATUS"] = value
                    trades.insert_columns()
                    funding.insert_columns()
                    orders.insert_columns()
                else:
                    print("Error during loading timeframes.")
                    WS.exit(ws)
                    ws.logNumFatal = -1
                    sleep(2)
            else:
                var.logger.info("No robots loaded.")
    if hasattr(Tables, "market"):
        Tables.market.color_market(
            state="online", row=var.market_list.index(ws.name), market=ws.name
        )
    ws.api_is_active = True


def refresh() -> None:
    for name in var.market_list:
        ws = Markets[name]
        utc = datetime.now(tz=timezone.utc)
        if ws.logNumFatal > 0:
            if ws.logNumFatal > 2000:
                if ws.message2000 == "":
                    ws.message2000 = (
                        "Fatal error=" + str(ws.logNumFatal) + ". Terminal is frozen"
                    )
                    info_display(ws.name, ws.message2000)
                    Tables.market.color_market(
                        state="error",
                        row=var.market_list.index(ws.name),
                        market=ws.name,
                    )
                sleep(1)
            elif ws.logNumFatal >= 1000 or ws.timeoutOccurred != "":  # reload
                # Function.market_status(ws, "RESTARTING...")
                setup_market(ws=ws)
            else:
                if ws.logNumFatal > 0 and ws.logNumFatal <= 10:
                    if ws.messageStopped == "":
                        ws.messageStopped = (
                            "Error=" + str(ws.logNumFatal) + ". Trading stopped"
                        )
                        info_display(name, ws.messageStopped)
                    if ws.logNumFatal == 2:
                        info_display(name, "Insufficient available balance!")
                    disp.f9 = "OFF"
                    ws.logNumFatal = 0
    Function.refresh_on_screen(Markets[var.current_market], utc=utc)


def clear_params():
    var.orders = OrderedDict()
    var.current_market = var.market_list[0]
    var.symbol = var.env[var.current_market]["SYMBOLS"][0]


def robots_thread() -> None:
    while var.robots_thread_is_active:
        utcnow = datetime.now(tz=timezone.utc)
        for market in var.market_list:
            ws = Markets[market]
            if ws.api_is_active:
                if ws.frames:
                    Function.robots_entry(ws, utc=utcnow)
        rest = 1 - time.time() % 1
        time.sleep(rest)


def terminal_reload(event) -> None:
    var.robots_thread_is_active = ""
    functions.info_display("Tmatic", "Restarting...")
    service.close(Markets)
    disp.root.update()
    setup()


def trade_state(event) -> None:
    if disp.f9 == "ON":
        disp.f9 = "OFF"
    elif disp.f9 == "OFF":
        disp.f9 = "ON"
        for num, market in enumerate(var.market_list):
            Markets[market].logNumFatal = 0
            Tables.market.color_market(state="online", row=num, market=market)
            print(market, disp.f9)
