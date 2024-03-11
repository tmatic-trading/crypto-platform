import tkinter as tk
from datetime import datetime

import functions
from api.websockets import Websockets
from common.variables import Variables as var
from display.variables import GridTable, ListBoxTable
from display.variables import Variables as disp

disp.root.bind("<F3>", lambda event: terminal_reload(event))
disp.root.bind("<F9>", lambda event: trade_state(event))


def terminal_reload(event) -> None:
    var.robots_thread_is_active = ""
    functions.info_display("Restarting...")
    disp.root.update()
    connect.connection()


def trade_state(event) -> None:
    if disp.f9 == "ON":
        disp.f9 = "OFF"
    elif disp.f9 == "OFF":
        disp.f9 = "ON"
        disp.messageStopped = ""
        ws = Websockets.connect[var.current_exchange]
        ws.logNumFatal = 0
    print(var.current_exchange, disp.f9)


def load_labels() -> None:
    functions.change_color(color=disp.title_color, container=disp.root)
    ws = Websockets.connect[var.current_exchange]
    GridTable(
        frame=disp.position_frame,
        name="position",
        title=var.name_pos,
        size=max(5, var.position_rows + 1),
        canvas_height=65, 
        bind=functions.handler_pos,
        color=disp.bg_color,
        select=True,
    )
    GridTable(
        frame=disp.frame_4row_1_2_3col,
        name="account",
        title=var.name_acc,
        size=var.account_rows + 1,
        canvas_height=60, 
        color=disp.bg_color,
    )
    GridTable(
        frame=disp.frame_5row_1_2_3col,
        name="robots",
        title=var.name_robots,
        size=max(disp.num_robots, len(ws.robots) + 1),
        canvas_height=150, 
        bind=functions.handler_robots,
        color=disp.title_color,
    )
    GridTable(
        frame=disp.frame_3row_1col,
        name="exchange",
        title=var.name_exchange,
        size=2,
        color=disp.title_color,
        select=True,
    )
    for row, emi in enumerate(ws.robots):
        if ws.robots[emi]["STATUS"] in ["NOT IN LIST", "OFF", "NOT DEFINED"] or (
            ws.robots[emi]["STATUS"] == "RESERVED" and ws.robots[emi]["POS"] != 0
        ):
            disp.labels["robots"][row + 1][5]["fg"] = "red"
        else:
            disp.labels["robots"][row + 1][5]["fg"] = "#212121"
    GridTable(
        frame=disp.orderbook_frame,
        name="orderbook",
        title=var.name_book,
        size=disp.num_book,
        canvas_height=440, 
        bind=functions.handler_orderbook,
        color=disp.bg_color,
    )
    num = int(disp.num_book / 2)
    for row in range(disp.num_book):
        for column in range(len(var.name_book)):
            if row > 0:
                if row <= num and column == 2:
                    disp.labels["orderbook"][row][column]["anchor"] = "w"
                if row > num and column == 0:
                    disp.labels["orderbook"][row][column]["anchor"] = "e"

trades = ListBoxTable(frame=disp.frame_trades, title=var.name_trade, size=0, expand=True)
funding = ListBoxTable(frame=disp.frame_funding, title=var.name_funding, size=0, expand=True)


