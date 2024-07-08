import tkinter as tk
from tkinter import ttk, StringVar

from .variables import Variables as disp, TreeviewTable

# ROBOTS MENU:
#
# Update Robot     (active if the bot's algorithm changed)
#
# Algo Syntax      (checks wheather the bot's algo code is syntactically correct)
#
# Start / Suspend  (starts or suspends algo trading)
#
# Backtest         (makes backtesting according to the bot's algorithm)
#
# Back             (leave the robot's page for the main one)
#
# Delete Robot     (completely deletes the bot's directory)

ttk.Style().configure("default.TEntry", fieldbackground=disp.bg_color)
ttk.Style().configure("changed.TEntry", fieldbackground=disp.bg_color)

pw_menu_robots = tk.PanedWindow(
    disp.menu_robots,
    orient=tk.HORIZONTAL,
    bd=0,
    sashwidth=0,
    height=1,
)
pw_menu_robots.pack(fill="both", expand="yes")

robots_left = tk.Frame(pw_menu_robots)
#robots_left.pack(fill="both", expand="yes")
robots_right = tk.Frame(pw_menu_robots)#, bg=disp.bg_color)

bot_title = tk.Frame(robots_right)
bot_title.grid(row=0, column=0, sticky="W", columnspan=2)
bot_title_label = tk.Label(bot_title, text="New Robot (This page is under development)", fg="red")
bot_title_label.pack()

bot_name_0 = tk.Frame(robots_right)
bot_name_0.grid(row=1, column=0, sticky="W")
bot_name_label = tk.Label(bot_name_0, text="Name (EMI)")
bot_name_label.pack(side="left")
bot_name_1 = tk.Frame(robots_right)
bot_name_1.grid(row=1, column=1, sticky="W")
entry_bot_name = ttk.Entry(bot_name_1, width=30, style="default.TEntry")
entry_bot_name.pack()

bot_currency_0 = tk.Frame(robots_right)
bot_currency_0.grid(row=2, column=0, sticky="W")
bot_currency_label = tk.Label(bot_currency_0, text="Currency")
bot_currency_label.pack(side="left")
bot_currency_1 = tk.Frame(robots_right)
bot_currency_1.grid(row=2, column=1, sticky="W")
entry_bot_currency = ttk.Entry(bot_currency_1, width=30, style="default.TEntry")
entry_bot_currency.pack()

bot_button_0 = tk.Frame(robots_right)
bot_button_0.grid(row=3, column=0, sticky="W")

bg_active = '#ffcccc'
bot_button_1 = tk.Frame(robots_right)
bot_button_1.grid(row=3, column=1, sticky="W")
bot_button = tk.Button(bot_button_1, bg=disp.bg_select_color, activebackground=bg_active, text="Create New", command=lambda: create_bot("button"))
bot_button.pack()

robots_right.grid_columnconfigure(0, weight=1)
robots_right.grid_columnconfigure(1, weight=10)
robots_right.grid_rowconfigure(0, weight=0)
robots_right.grid_rowconfigure(1, weight=0)
robots_right.grid_rowconfigure(2, weight=0)
robots_right.grid_rowconfigure(3, weight=0)


def create_bot(value):
    print(value)


robots_button_back = tk.Button(
    robots_left,
    bg=disp.bg_select_color,
    text="Back",
    command=lambda: back_to_main(),
)
robots_button_back.pack()

pw_menu_robots.add(robots_left)
pw_menu_robots.add(robots_right)
pw_menu_robots.bind(
        "<Configure>",
        lambda event: disp.resize_width(
            event, pw_menu_robots, disp.window_width // 9.5, 6
        ),
    )

def back_to_main():
    disp.menu_robots.pack_forget()
    disp.pw_rest1.pack(fill="both", expand="yes")
