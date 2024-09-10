import threading
from datetime import datetime, timedelta, timezone
from time import sleep

import botinit.init as botinit
import common.init as common
import functions
import services as service
from api.api import WS, Markets, MetaMarket
from api.bitmex.ws import Bitmex
from api.bybit.ws import Bybit
from api.deribit.ws import Deribit
from api.init import Setup
from common.data import Bots
from common.variables import Variables as var
from display.bot_menu import bot_manager, insert_bot_log
from display.functions import info_display
from display.settings import SettingsApp
from display.variables import TreeTable
from display.variables import Variables as disp
from functions import Function

settings = SettingsApp(disp.settings_page)
disp.root.bind("<F3>", lambda event: terminal_reload(event))
Bitmex.transaction = Function.transaction
Bybit.transaction = Function.transaction
Deribit.transaction = Function.transaction
thread = threading.Thread(target=functions.kline_update)
thread.start()
# settings.load()


def setup(reload=False):
    """
    This function works the first time you start the program or when you
    reboot after pressing F3. Markets are loaded using setup_market() in
    parallel in threads to speed up the loading process.
    """
    clear_params()
    settings.load()
    common.setup_database_connecion()
    threads = []
    for name in var.market_list.copy():
        ws = Markets[name]
        # if name in MetaMarket.dictionary:
        Setup.variables(ws)
        ws.setup_session()
        if name in var.market_list:
            t = threading.Thread(target=setup_market, args=(ws, reload))
            threads.append(t)
            t.start()
    [thread.join() for thread in threads]
    for name in var.market_list:
        finish_setup(Markets[name])
    merge_orders()
    functions.clear_klines()
    botinit.load_bots()
    functions.setup_klines()
    if not var.market_list:
        var.market_list = ["Fake"]
        var.current_market = "Fake"
        var.symbol = "BTCUSDT"
    else:
        var.current_market = var.market_list[0]
        var.symbol = Markets[var.current_market].symbol_list[0][0]
    functions.init_tables()
    bot_manager.create_bots_menu()
    bot_threads()
    settings.init()
    if "Fake" in var.market_list:
        disp.on_settings()
        settings.return_main_page()
    else:
        disp.on_main()


def setup_market(ws: Markets, reload=False):
    """
    Market reboot. During program operation, when accessing endpoints or
    receiving information from websockets, errors may occur due to the loss of
    the Internet connection or errors for other reasons. If the program
    detects such a case, it reboots the market to restore data integrity.

    The download process may take time, because there are a large number
    of calls to endpoints and websocket subscriptions. To speed up, many calls
    are performed in parallel threads, within which parallel threads can also
    be opened. If any download component is not received, the program will
    restart again from the very beginning.

    The download process is done in stages because the order in which the
    information is received matters. Loading sequence:

    1) All active instruments.
    2) All active orders. After receiving orders, it may happen that the order
       is executed even before the websocket comes up. In this case, the
       websocket will not send execution, but the integrity of the information
       will not be lost, because execution of order will be processed at the
       end of loading in the load_trading_history() function.
    3) Simultaneous download:
        1. Subscribe to websockets only for those instruments that are
           specified in the .env files.
        2. Getting the user id.
        3. Obtaining information on account balances.
        4. Obtaining initial information about the positions of signed
           instruments.
    4) Reading active bots from the database.
    5) Simultaneous download:
        1. Receiving klines only for those instruments and timeframes that are
           used by bots.
        2. Trading history.
    """

    def get_klines(ws, success, num):
        if functions.init_market_klines(ws):
            success["kline"] = "success"

    def get_history(ws, success, num):
        if common.Init.load_trading_history(ws):
            success["history"] = "success"

    ws.logNumFatal = "SETUP"
    ws.api_is_active = False
    if reload:
        WS.exit(ws)
        sleep(3)
    while ws.logNumFatal not in ["", "CANCEL"]:
        var.queue_order.put({"action": "clear", "market": ws.name})
        ws.logNumFatal = WS.start_ws(ws)
        if ws.logNumFatal:
            WS.exit(ws)
            if ws.logNumFatal != "CANCEL":
                sleep(2)
        else:
            common.Init.clear_params(ws)
            if not ws.logNumFatal:
                threads = []
                success = {"kline": None, "history": None}
                t = threading.Thread(
                    target=get_klines,
                    args=(ws, success, len(success) - 1),
                )
                threads.append(t)
                t.start()
                t = threading.Thread(
                    target=get_history,
                    args=(ws, success, len(success) - 1),
                )
                threads.append(t)
                t.start()
                [thread.join() for thread in threads]
                if not success["history"]:
                    var.logger.error(ws.name + ": The trade history is not loaded.")
                    ws.logNumFatal = "SETUP"
                if not success["kline"]:
                    var.logger.error(ws.name + ": Klines are not loaded.")
                    ws.logNumFatal = "SETUP"
            else:
                var.logger.info("No robots loaded.")
                sleep(2)
        if ws.logNumFatal == "CANCEL":
            service.cancel_market(market=ws.name)
        if ws.logNumFatal not in ["", "CANCEL"]:
            var.logger.info("\n\n")
            var.logger.info(
                "Something went wrong while loading " + ws.name + ". Reboot.\n\n"
            )
            WS.exit(ws)
            sleep(3)


def merge_orders():
    orders_list = list()
    for values in var.orders.values():
        for value in values.values():
            orders_list.append(value)
    orders_list.sort(key=lambda x: x["transactTime"])
    for order in orders_list:
        var.queue_order.put({"action": "put", "order": order})


def finish_setup(ws: Markets):
    """
    This part of the setup does not interact with HTTP, so there is no need to
    load data from different threads to speed up the program and this function
    is executed from the main loop. Moreover, the function uses
    load_database() to fill data into the Treeview tables, which, according to
    Tkinter capabilities, is only possible from the main loop.
    """
    common.Init.load_database(ws)
    common.Init.account_balances(ws)
    common.Init.load_orders(ws, ws.setup_orders)
    for bot_name in Bots.keys():
        ws.robot_status[bot_name] = Bots[bot_name].state
    ws.message_time = datetime.now(tz=timezone.utc)
    ws.api_is_active = True


def reload_market(ws: Markets):
    ws.api_is_active = False
    Function.market_status(
        ws, status="RELOADING...", message="Reloading...", error=True
    )
    TreeTable.market.tree.update()
    setup_market(ws=ws, reload=True)
    var.queue_reload.put(ws)


def refresh() -> None:
    if disp.f3:
        terminal_reload("None")
    while not var.queue_reload.empty():
        ws = var.queue_reload.get()
        finish_setup(ws=ws)
        merge_orders()
        Function.market_status(ws, status="ONLINE", message="", error=False)
        functions.clear_tables()
    while not var.queue_info.empty():
        info = var.queue_info.get()
        if not "bot_log" in info:
            info_display(
                market=info["market"],
                message=info["message"],
                warning=info["warning"],
                tm=info["time"],
            )
        if "emi" in info and info["emi"] in Bots.keys():
            insert_bot_log(
                market=info["market"],
                bot_name=info["emi"],
                message=info["message"],
                warning=info["warning"],
                tm=info["time"],
            )
    while not var.queue_order.empty():
        """
        The queue thread-safely displays current orders that can be queued:
        1. From the websockets of the markets.
        2. When retrieving current orders from the endpoints when loading or
           reloading the market.
        3. When processing the trading history data.

        Possible queue jobs:
        1.     "action": "put"
           Display a row with the new order in the table. If an order with the
           same clOrdID already exists, then first remove it from the table
           and print the order on the first line.
        2.     "action": "delete"
           Delete order by clOrdID.
        3.     "action": "clear"
           Before reloading the market, delete all orders of a particular
           market from the table, because the reboot process will update
           information about current orders, so possibly canceled orders
           during the reloading will be removed.
        """
        job = var.queue_order.get()
        if job["action"] == "delete":
            clOrdID = job["clOrdID"]
            if clOrdID in TreeTable.orders.children:
                TreeTable.orders.delete(iid=clOrdID)
        elif job["action"] == "put":
            order = job["order"]
            clOrdID = order["clOrdID"]
            ws = Markets[order["market"]]
            if clOrdID in var.orders[order["emi"]]:
                Function.orders_display(ws, val=order)
        elif job["action"] == "clear":
            TreeTable.orders.clear_all(market=job["market"])

    for name in var.market_list:
        ws = Markets[name]
        utc = datetime.now(tz=timezone.utc)
        if not ws.logNumFatal:
            if ws.api_is_active:
                if utc > ws.message_time + timedelta(seconds=10):
                    if not WS.ping_pong(ws):
                        info_display(
                            market=ws.name,
                            message="The websocket does not respond within 10 sec. Reboot",
                            warning="error",
                        )
                        ws.logNumFatal = "FATAL"  # reboot
                    ws.message_time = utc
        elif ws.logNumFatal == "BLOCK":
            if ws.message2000 == "":
                ws.message2000 = "Fatal error. Trading stopped"
                Function.market_status(
                    ws, status="Error", message=ws.message2000, error=True
                )
            sleep(1)
        elif ws.logNumFatal == "FATAL":  # reboot
            if ws.api_is_active:
                t = threading.Thread(target=reload_market, args=(ws,))
                t.start()
    var.lock_market_switch.acquire(True)
    ws = Markets[var.current_market]
    if ws.api_is_active:
        Function.refresh_on_screen(Markets[var.current_market], utc=utc)
    var.lock_market_switch.release()


def clear_params():
    var.market_list = []


def bot_threads() -> None:
    for bot_name in Bots.keys():
        functions.activate_bot_thread(bot_name=bot_name)


def terminal_reload(event) -> None:
    disp.menu_robots.pack_forget()
    disp.settings.pack_forget()
    disp.pw_rest1.pack(fill="both", expand="yes")
    functions.info_display(market="Tmatic", message="Restarting...")
    service.close(Markets)
    disp.root.update()
    setup()
    functions.clear_tables()
    disp.f3 = False


def on_closing(root, refresh_var):
    root.after_cancel(refresh_var)
    root.destroy()
    service.close(Markets)
    var.kline_update_active = False


def init_fake():
    Markets["Fake"]
