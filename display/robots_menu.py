import tkinter as tk
from tkinter import ttk, StringVar
import os
import re

from .variables import Variables as disp
#from api.api import Markets

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

ttk.Style().configure("free.TEntry", foreground=disp.fg_color)
ttk.Style().configure("used.TEntry", foreground="red")

class CustomButton(tk.Menubutton):
    def __init__(self, master, app, button, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.name = button
        self.var = tk.IntVar()
        self.bind("<ButtonPress-1>", self.on_press)

    def on_press(self, event):
        if self["state"] != "disabled":
            if self.name == "Back":
                disp.menu_robots.pack_forget()
                disp.pw_rest1.pack(fill="both", expand="yes")
            else:
                print(self.name, self["state"])

    def set_background_color(self, frame, checked):
        '''Set background color for selected button'''
        '''if frame != self.app.selected_frame or checked == "true":
            self.app.selected_frame.config(bg=self.app.market_color[self.app.selected_frame.market])
            self.app.selected_frame = frame
            frame.config(bg=self.app.bg_select_color)
            self.app.click_market = "true"
            self.app.set_market_fields(frame.market)
            self.app.click_market = "false"'''

class SettingsApp:
    def __init__(self, root):
        self.root_frame = root
        self.button_list = ["Syntax", "Backtest", "Activate", "Update", "Delete", "Back"]
        self.rows_list = ["Name", "Currency", "Created", "Updated", "Timeframe", "Capital", "Leverage", "PNL"]
        self.selected_bot = ""
        self.algo_dir = f"{os.getcwd()}/algo/"
        self.bots_list = [x[0].replace(self.algo_dir, "") for x in os.walk(self.algo_dir)]

        # To trace whether a new bot's name is unique
        self.name_trace = StringVar(name="Name" + str(self))

        # Create initial frames
        self.create_right_frames()

        # CustomButton array
        self.buttons_center = []

        for button in self.button_list:
            state = "disabled" if button != "Back" else "normal"
            frame = CustomButton(self.root_frame, self, button, bg=disp.bg_select_color, text=button, bd=0, activebackground=disp.bg_active, state=state)
            self.buttons_center.append(frame)

        self.draw_buttons()

    def draw_buttons(self):
        #self.buttons_center.sort(key=lambda f: f.winfo_y())
        total_height = 0
        for i, button in enumerate(self.buttons_center):
            button.update_idletasks()
            button_height = button.winfo_reqheight()
            y_pos = 0
            if i == 0:
                y_pos = button_height / 2
                total_height = y_pos
            else:
                y_pos = total_height
                if button.name == "Back":
                    y_pos += button_height / 2
            button.place_configure(x=0, y=y_pos, height=button_height, relwidth=1.0)
            total_height += button_height * 1.5

    def redraw_bot(self):
        for row in self.rows_list:
            self.bot_0_label[row].pack(side="left", padx=10)
            self.bot_1_entry[row].pack_forget()
            self.bot_1_label[row].pack(side="left", padx=10)
        self.bot_1_label["Name"].config(text=self.selected_bot)
        self.button_create.pack_forget()


    def create_bot(self):
        bot_name = self.name_trace.get()
        path = os.path.join(self.algo_dir, bot_name)

        # Create a new directory with the name as the new bot's name
        os.mkdir(path)

        # Create the '__init__.py' file in the new directory. This file is empty
        os.mknod(f"{str(path)}/__init__.py")

        # Load the content of 'init.py' file
        file = open(f"{self.algo_dir}init.py", 'r')
        content = file.read()
        file.close()

        # Create new 'init.py' file in the new directory
        os.mknod(f"{str(path)}/init.py")

        # Write the initial content into the new 'init.py' file
        file = open(f"{str(path)}/init.py", 'a')
        file.write(content)
        file.close()

        # Create new 'strategy.py' file in the new directory
        os.mknod(f"{str(path)}/strategy.py")
        # Write the initial content into the new 'strategy.py' file
        file = open(f"{str(path)}/strategy.py", 'a')
        file.write("import services as service\nfrom api.api import Markets\nfrom common.data import Instrument\nfrom functions import Function\n")
        file.close()

        # Create new '.gitignore' file in the new directory
        os.mknod(f"{str(path)}/.gitignore")
        # Write the initial content into the new '.gitignore' file
        file = open(f"{str(path)}/.gitignore", 'a')
        file.write("*\n!__init__.py\n!.gitignore\n!init.py\n!strategy.py\n")
        file.close()

        self.selected_bot = bot_name
        self.redraw_bot()

    def trace_callback(self, var, index, mode):
        name = var.replace(str(self), "")
        bot_name = re.sub('[\W]+', '', self.name_trace.get())
        if bot_name in self.bots_list or bot_name != self.name_trace.get():
            self.bot_1_entry[name].config(style=f"used.TEntry")
            self.button_create.config(state="disabled")
        else:
            self.bot_1_entry[name].config(style=f"free.TEntry")
            self.button_create.config(state="normal")

    def create_right_frames(self):
        target_frame = robots_right
        widget_row = 0
        self.bot_top = tk.Frame(target_frame)
        self.bot_top.grid(row=widget_row, column=0, sticky="EW", columnspan=2)
        self.setting_label = tk.Label(self.bot_top, text="This page is under development", fg="red")
        self.setting_label.pack(side="left", padx=10)

        self.bot_0 = {}
        self.bot_0_label = {}
        self.bot_1 = {}
        self.bot_1_entry = {}
        self.bot_1_label = {}

        for i, row in enumerate(self.rows_list):
            widget_row += 1
            self.bot_0[row] = tk.Frame(target_frame)
            self.bot_0[row].grid(row=widget_row, column=0, sticky="W")
            self.bot_0_label[row] = tk.Label(self.bot_0[row], text=row)
            if i < 2 or self.selected_bot != "":
                self.bot_0_label[row].pack(side="left", padx=10)
            self.bot_1[row] = tk.Frame(target_frame)
            self.bot_1[row].grid(row=widget_row, column=1, sticky="W")
            self.bot_1_entry[row] = ttk.Entry(self.bot_1[row], width=30, style="default.TEntry")
            if row == "Name":
                self.bot_1_entry[row].config(textvariable=self.name_trace)
                self.name_trace.trace_add('write', self.trace_callback)
            self.bot_1_label[row] = tk.Label(self.bot_1[row])
            if i < 2 or self.selected_bot != "":
                self.bot_1_entry[row].pack()
            elif i == 2:
                self.button_create = tk.Button(self.bot_1[row], activebackground=disp.bg_active, text="Create Bot", command=lambda: self.create_bot())
                self.button_create.pack()

        target_frame.grid_columnconfigure(0, weight=1)
        target_frame.grid_columnconfigure(1, weight=10)
        for i in range(widget_row):
            target_frame.grid_rowconfigure(i, weight=0)

#ws = Markets[var.current_market]
#for val in ws.robots:
#print(Markets)

pw_menu_robots = tk.PanedWindow(
    disp.menu_robots,
    orient=tk.HORIZONTAL,
    bd=0,
    sashwidth=0,
    height=1,
)
pw_menu_robots.pack(fill="both", expand="yes")

robots_left = tk.Frame(pw_menu_robots, relief="sunken", borderwidth=1)
robots_right = tk.Frame(pw_menu_robots)#, bg=disp.bg_color)

pw_menu_robots.add(robots_left)
pw_menu_robots.add(robots_right)
pw_menu_robots.bind(
        "<Configure>",
        lambda event: disp.resize_width(
            event, pw_menu_robots, disp.window_width // 9.5, 6
        ),
    )

buttons_menu = SettingsApp(robots_left)