import tkinter as tk

import connect
import functions as function
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.variables import Variables as disp

disp.root.bind("<F3>", lambda event: terminal_reload(event))
disp.root.bind("<F9>", lambda event: trade_state(event))


def terminal_reload(event) -> None:
    function.info_display("Restarting...")
    disp.root.update()
    var.ws = connect.connection()


def trade_state(event) -> None:
    if disp.f9 == "ON":
        disp.f9 = "OFF"
    elif disp.f9 == "OFF":
        disp.f9 = "ON"
        disp.messageStopped = ""
        var.ws.logNumFatal = 0
    print(disp.f9)


def load_labels() -> None:
    # Robots table

    rows = max(disp.num_robots, len(bot.robots) + 1)
    for name in var.name_robots:
        tmp = []
        for _ in range(rows):
            tmp.append(tk.Label(disp.frame_robots, text=name, pady=0))
        disp.label_robots.append(tmp)
    for row in range(rows):
        for column in range(len(var.name_robots)):
            if row > 0:
                disp.label_robots[column][row]["text"] = ""
                disp.label_robots[column][row].bind(
                    "<Button-1>",
                    lambda event, row_position=row: function.handler_robots(
                        event, row_position
                    ),
                )
            disp.label_robots[column][row].grid(
                row=row, column=column, sticky="N" + "S" + "W" + "E"
            )
            disp.frame_robots.grid_columnconfigure(column, weight=1)

    function.change_color(color=disp.title_color, container=disp.root)

    # Positions widget

    for row in range(disp.num_pos):
        for column in range(len(var.name_pos)):
            if row == 0:
                disp.labels["position"][column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
                )
            else:
                disp.labels["position"][column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
                )
                color = "yellow" if row == 1 else disp.bg_color
                disp.labels["position"][column][row]["text"] = ""
                disp.labels["position"][column][row]["bg"] = color
                disp.labels["position"][column][row].bind(
                    "<Button-1>",
                    lambda event, row_position=row: function.handler_pos(
                        event, row_position
                    ),
                )
            disp.frame_positions.grid_columnconfigure(column, weight=1)

    # Order book table

    num = int(disp.num_book / 2)
    for row in range(disp.num_book):
        for column in range(len(var.name_book)):
            if row == 0:
                disp.label_book[column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1
                )
            else:
                if (row <= num and column == 0) or (row > num and column == 2):
                    disp.label_book[column][row]["fg"] = disp.bg_color
                if row <= num and column == 2:
                    disp.label_book[column][row]["anchor"] = "w"
                if row > num and column == 0:
                    disp.label_book[column][row]["anchor"] = "e"
                disp.label_book[column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1
                )
                disp.label_book[column][row]["text"] = ""
                disp.label_book[column][row]["bg"] = disp.bg_color
                disp.label_book[column][row]["height"] = 1
                disp.label_book[column][row].bind(
                    "<Button-1>",
                    lambda row_position=row: function.handler_book(row_position),
                )
            disp.label_book[column][row].grid(row=row, column=column)
            disp.frame_3row_3col.grid_columnconfigure(column, weight=1)

    # Account table

    for row in range(disp.num_acc):
        for column in range(len(var.name_acc)):
            if row == 0:
                disp.label_account[column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
                )
            else:
                disp.label_account[column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
                )
                disp.label_account[column][row]["text"] = ""
                disp.label_account[column][row]["bg"] = disp.bg_color
            disp.label_account[column][row].grid(row=row, column=column)
            disp.frame_4row_1_2_3col.grid_columnconfigure(column, weight=1)
