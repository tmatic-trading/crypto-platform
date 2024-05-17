import concurrent.futures
import os
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
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.functions import info_display
from display.variables import TreeTable
from display.variables import Variables as disp
from functions import Function


def setup():
    disp.root.bind("<F3>", lambda event: terminal_reload(event))
    disp.root.bind("<F9>", lambda event: trade_state(event))
    Bitmex.transaction = Function.transaction
    Bybit.transaction = Function.transaction
    clear_params()
    common.setup_database_connecion()
    var.robots_thread_is_active = False
    threads = []
    for name in var.market_list:
        t = threading.Thread(target=setup_market, args=(Markets[name],))
        threads.append(t)
        t.start()
    [thread.join() for thread in threads]
    for name in var.market_list:
        finish_setup(Markets[name])
    functions.load_labels()
    var.robots_thread_is_active = True
    thread = threading.Thread(target=robots_thread)
    thread.start()


def setup_market(ws: Markets):
    def get_timeframes(ws):
        return bots.Init.init_timeframes(ws)

    def get_history(ws):
        common.Init.load_trading_history(ws)

    def get_orders(ws):
        return WS.open_orders(ws)

    ws.logNumFatal = -1
    ws.api_is_active = False
    WS.exit(ws)
    while ws.logNumFatal:
        ws.logNumFatal = -1
        WS.start_ws(ws)
        if ws.logNumFatal:
            WS.exit(ws)
            sleep(2)
        else:
            common.Init.clear_params(ws)
            if bots.Init.load_robots(ws):
                algo.init_algo(ws)
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    frames = executor.submit(get_timeframes, ws)
                    executor.submit(get_history, ws)
                    open_orders = executor.submit(get_orders, ws)
                    frames = frames.result()
                    ws.setup_orders = open_orders.result()
                if isinstance(frames, dict):
                    pass
                else:
                    var.logger.info("Error during loading timeframes.")
                    WS.exit(ws)
                    ws.logNumFatal = -1
                    sleep(2)
            else:
                var.logger.info("No robots loaded.")


def finish_setup(ws: Markets):
    common.Init.load_database(ws)
    common.Init.account_balances(ws)
    common.Init.load_orders(ws, ws.setup_orders)
    bots.Init.delete_unused_robot(ws)
    for emi, value in ws.robot_status.items():
        if emi in ws.robots:
            ws.robots[emi]["STATUS"] = value
    ws.api_is_active = True


def refresh() -> None:
    while not var.info_queue.empty():
        info = var.info_queue.get()
        info_display(info["market"], info["message"])
    for name in var.market_list:
        ws = Markets[name]
        utc = datetime.now(tz=timezone.utc)
        if ws.logNumFatal > 0:
            if ws.logNumFatal > 2000:
                if ws.message2000 == "":
                    ws.message2000 = (
                        "Fatal error=" + str(ws.logNumFatal) + ". Market is frozen"
                    )
                    Function.market_status(
                        ws, status="Error", message=ws.message2000, error=True
                    )
                sleep(1)
            elif ws.logNumFatal >= 1000 or ws.timeoutOccurred != "":  # reload
                Function.market_status(
                    ws, status="RESTARTING...", message="RESTARTING...", error=True
                )
                TreeTable.market.tree.update()
                setup_market(ws=ws)
                finish_setup(ws=ws)
                Function.market_status(ws, status="ONLINE", message="", error=False)
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
    disp.symb_book = ()


def robots_thread() -> None:
    def bot_in_thread():
        # Bots entry point
        bot.robo[robot["emi"]](
            robot=robot["robot"],
            frame=robot["frame"],
            instrument=robot["instrument"],
        )

    while var.robots_thread_is_active:
        utcnow = datetime.now(tz=timezone.utc)
        bot_list = list()
        for market in var.market_list:
            ws = Markets[market]
            if ws.api_is_active:
                if ws.frames:
                    bot_list = Function.robots_entry(ws, bot_list, utc=utcnow)
        threads = []
        for robot in bot_list:
            t = threading.Thread(target=bot_in_thread)
            threads.append(t)
            t.start()
        [thread.join() for thread in threads]
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
        for market in var.market_list:
            Markets[market].logNumFatal = 0
            print(market, disp.f9)


def on_closing(root, refresh_var):
    root.after_cancel(refresh_var)
    root.destroy()
    service.close(Markets)
    # os.abort()
