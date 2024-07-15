import os
import re
import shutil
import tkinter as tk
from tkinter import font
import time

# from pygments.token import Token
import traceback
from tkinter import StringVar, ttk

from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name

from .variables import AutoScrollbar
from .variables import Variables as disp

# from api.api import Markets

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

    def check_syntax(self, code):
        try:
            # Compile the code to check for syntax errors
            compiled_code = compile(code, "<string>", "exec")
            # Execute the compiled code to check for runtime errors
            exec(compiled_code, {})
            return True, None
        except (SyntaxError, Exception) as e:
            return False, traceback.format_exc()

    def open_popup(self, bot_name, content):
        if self.app.pop_up:
            self.app.pop_up.destroy()
        self.app.pop_up = tk.Toplevel()
        self.app.pop_up.geometry("750x350")
        self.app.pop_up.title(f"Check syntax for the bot named: {bot_name}")

        scroll = AutoScrollbar(self.app.pop_up, orient="vertical")
        text = tk.Text(
            self.app.pop_up,
            highlightthickness=0,
            yscrollcommand=scroll.set,
            bg=disp.title_color,
        )
        scroll.config(command=text.yview)
        text.grid(row=0, column=0, sticky="NSEW")
        scroll.grid(row=0, column=1, sticky="NS")
        self.app.pop_up.grid_columnconfigure(0, weight=1)
        self.app.pop_up.grid_columnconfigure(1, weight=0)
        self.app.pop_up.grid_rowconfigure(0, weight=1)

        is_syntax_correct, error_message = self.check_syntax(content)
        if is_syntax_correct:
            text.insert(tk.END, "The bot's code is correct")
            text.config(state="disabled")
        else:
            text.insert(tk.END, error_message)

    def on_press(self, event):
        if self["state"] != "disabled":
            if self.name == "New Bot":
                self.app.selected_bot = ""
                self.app.action = self.name
                comment = f"\nCreate a bot.\nEvery new bot\nmust have\na unique name."
                self.app.show_bot(comment)
                self.app.draw_buttons()
            elif self.name == "Back":
                if self.app.action == "Duplicate":
                    self.app.action = ""
                    self.app.show_bot("")
                    self.app.draw_buttons()
                else:
                    #self.app.selected_bot = ""
                    #self.app.show_bot("")
                    #self.app.draw_buttons()
                    disp.menu_robots.pack_forget()
                    disp.pw_rest1.pack(fill="both", expand="yes")
            elif self.name == "Delete":
                self.app.delete_bot()
            elif self.name == "Syntax":
                content = self.app.strategy_text.get("1.0", tk.END)
                self.open_popup(self.app.selected_bot, content)
            elif self.name == "Duplicate":
                self.app.action = self.name
                comment = f"\nYou are about to duplicate the bot named '{self.app.selected_bot}'.\nSince every new bot must have a unique title,\nchoose any name that differs from '{self.app.selected_bot}'.\n\nThe newly created bot will get the same algorithm code\nas the '{self.app.selected_bot}' currently has."
                self.app.show_bot(comment)
                self.app.draw_buttons()
            else:
                print(self.name, self["state"])

    def set_background_color(self, frame, checked):
        """Set background color for selected button"""
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

        self.pop_up = None
        self.selected_bot = ""# "112"
        self.bot_path = ""
        self.algo_dir = f"{os.getcwd()}/algo/"
        self.action = ""

        self.button_list = [
            "New Bot",
            "Syntax",
            "Backtest",
            "Activate",
            "Update",
            "Merge",
            "Duplicate",
            "Delete",
            "Back",
        ]
        self.rows_list = [
            "Name",
            "Created",
            "Updated",
            "Status",
        ]
        '''"Timeframe",
        "Capital",
        "Leverage",
        "PNL",'''

        # Keeps all bots' names in the array
        self.bots_list = []

        # Keeps the bot's algorithm derived from strategy.py file
        self.bot_algo = ""

        # To trace whether a new bot's name is unique
        self.name_trace = StringVar(name="Name" + str(self))

        # Create initial frames
        self.bot_info_frame()
        self.show_bot("New bot")

        # CustomButton array
        self.buttons_center = []

        for button in self.button_list:
            frame = CustomButton(
                self.root_frame,
                self,
                button,
                bg=disp.bg_select_color,
                text=button,
                bd=0,
                activebackground=disp.bg_active,
            )
            self.buttons_center.append(frame)

        self.collect_bots()
        self.draw_buttons()

    def collect_bots(self):
        '''Reviews all created bots in the algo directory and puts them in the array'''
        self.bots_list = [
            x[0].replace(self.algo_dir, "") for x in os.walk(self.algo_dir)
        ]

    def draw_buttons(self):
        '''Draws bot menu buttons accordingly'''
        # self.buttons_center.sort(key=lambda f: f.winfo_y())
        total_height = 0
        for i, button in enumerate(self.buttons_center):
            if button.name == "New Bot":
                if self.selected_bot == "":
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            elif button.name == "Back":
                button.configure(state="normal")
            elif button.name == "Delete":
                if self.selected_bot == "" or self.action == "Duplicate":
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            elif button.name == "Syntax":
                if self.selected_bot == "" or self.action == "Duplicate":
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            elif button.name == "Duplicate":
                if self.selected_bot == "" or self.action == "Duplicate":
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            else:
                button.configure(state="disabled")
            # button.update_idletasks()#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
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

    def show_bot(self, comment):
        """Shows the bot's info when bot is selected. Otherwise hides"""
        for item in self.rows_list:
            if self.selected_bot == "" or self.action != "":
                if item == "Name":
                    self.info_name[item].pack(anchor="w")
                    self.info_entry[item].pack(anchor="w")
                    self.info_entry[item].delete(0, tk.END)
                    if self.action == "Duplicate":
                        self.info_entry[item].insert(0, self.selected_bot)
                    self.button_create.pack(anchor="w")
                    self.button_create.config(state="disabled")
                    self.strategy.grid_forget()
                    self.bot_algo = ""
                    self.pw_info.forget(self.bot_note)
                    if self.action != "":
                        self.label_comment.config(text=comment)
                        self.pw_info.add(self.frame_comment)
                else:
                    self.info_name[item].pack_forget()
                self.info_value[item].config(text="")
                self.info_value[item].pack_forget()
            else:
                if item == "Name":
                    self.info_value[item].config(text=self.selected_bot)
                    self.info_entry[item].pack_forget()
                    self.button_create.pack_forget()
                    self.strategy.grid(row=self.strategy_row, column=0, sticky="NSWE", columnspan=2)
                    if self.bot_path == "":
                        self.bot_path = os.path.join(self.algo_dir, self.selected_bot)
                    self.bot_algo = self.read_file(f"{self.bot_path}/strategy.py")
                    self.insert_code(self.strategy_text, self.bot_algo)
                    self.pw_info.forget(self.frame_comment)
                    self.pw_info.add(self.bot_note)
                elif item == "Created":
                    my_time = time.ctime(os.path.getctime(self.bot_path))
                    t_stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(my_time))
                    self.info_value[item].config(text=t_stamp)
                elif item == "Updated":
                    my_time = time.ctime(os.path.getmtime(self.bot_path))
                    t_stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(my_time))
                    self.info_value[item].config(text=t_stamp)
                elif item == "Status":
                    self.info_value[item].config(text="Suspended")
                self.info_name[item].pack(anchor="w")
                self.info_value[item].pack(anchor="w")

    def delete_bot(self):
        #path = os.path.join(self.algo_dir, self.selected_bot)
        # files = os.listdir(path)
        shutil.rmtree(str(self.bot_path))
        self.selected_bot = ""
        self.bot_path = ""
        self.show_bot("")
        self.draw_buttons()
        self.collect_bots()

    def insert_code(self, text_widget, code):
        """Function to insert Python code into a Tkinter Text widget with syntax highlighting"""
        text_widget.delete(1.0, tk.END)
        lexer = PythonLexer()
        style = get_style_by_name("default")  # You can change the style if desired

        for token, content in lex(code, lexer):
            tag_name = str(token)
            text_widget.insert(tk.END, content, tag_name)

            # Configure the tag if it hasn't been already
            if not text_widget.tag_cget(tag_name, "foreground"):
                color = style.style_for_token(token).get("color")
                if color:
                    text_widget.tag_configure(tag_name, foreground="#" + color)

    def create_file(self, file_name):
        os.mknod(file_name)

    def read_file(self, file_name):
        file = open(file_name, "r")
        content = file.read()
        file.close()
        return content

    def write_file(self, file_name, content):
        file = open(file_name, "a")
        file.write(content)
        file.close()

    def create_bot(self):
        bot_name = self.name_trace.get()
        self.bot_path = os.path.join(self.algo_dir, bot_name)
        # Create a new directory with the name as the new bot's name
        os.mkdir(self.bot_path)
        # Create the '__init__.py' file in the new directory. This file is empty
        self.create_file(f"{str(self.bot_path)}/__init__.py")
        # Load the content of 'init.py' file
        content = self.read_file(f"{self.algo_dir}init.py")
        # Create new 'init.py' file in the new directory
        self.create_file(f"{str(self.bot_path)}/init.py")
        # Write the initial content into the new 'init.py' file
        self.write_file(f"{str(self.bot_path)}/init.py", content)
        # Create new 'strategy.py' file in the new directory
        self.create_file(f"{str(self.bot_path)}/strategy.py")
        # Write the initial content into the new 'strategy.py' file
        self.write_file(
            f"{str(self.bot_path)}/strategy.py",
            "import services as service\nfrom api.api import Markets\nfrom common.data import Instrument\nfrom functions import Function\n",
        )
        # Create new '.gitignore' file in the new directory
        self.create_file(f"{str(self.bot_path)}/.gitignore")
        # Write the initial content into the new '.gitignore' file
        self.write_file(
            f"{str(self.bot_path)}/.gitignore",
            "*\n!__init__.py\n!.gitignore\n!init.py\n!strategy.py\n",
        )

        self.selected_bot = bot_name
        self.action = ""
        self.show_bot("")
        self.draw_buttons()
        self.collect_bots()

    def trace_callback(self, var, index, mode):
        name = var.replace(str(self), "")
        bot_name = re.sub("[\W]+", "", self.name_trace.get())
        if bot_name in self.bots_list or bot_name != self.name_trace.get():
            self.info_entry[name].config(style=f"used.TEntry")
            self.button_create.config(state="disabled")
        else:
            self.info_entry[name].config(style=f"free.TEntry")
            self.button_create.config(state="normal")

    def bot_info_frame(self):
        #target_frame = robots_right
        frame_row = 0
        top_frame = tk.Frame(info_frame)
        top_frame.grid(row=frame_row, column=0, sticky="NSEW", columnspan=2)
        under_dev_label = tk.Label(
            top_frame, text="This page is under development", fg="red"
        )
        under_dev_label.pack(anchor="center")

        empty_frame = []
        empty_frame_label = []
        for i in range(10):
            frame_row += 1
            empty_frame.append(tk.Frame(info_frame))
            empty_frame[i].grid(row=frame_row, column=0, sticky="NSEW")
            empty_frame_label.append(tk.Label(empty_frame[i], text=" "))
            empty_frame_label[i].pack(anchor="w")

        filled_frame = tk.Frame(info_frame)
        filled_frame.grid(row=1, column=1, sticky="NSEW", rowspan=frame_row)

        self.pw_info = tk.PanedWindow(
            filled_frame,
            orient=tk.HORIZONTAL,
            bd=0,
            sashwidth=0,
            height=1,
        )
        self.pw_info.pack(fill="both", expand="yes")

        info_left = tk.Frame(self.pw_info)

        if disp.ostype == "Mac":
            self.bot_note = ttk.Notebook(self.pw_info, padding=(-9, 0, -9, -9))
        else:
            self.bot_note = ttk.Notebook(self.pw_info, padding=0)
        bot_positions = tk.Frame(self.bot_note)
        bot_orders = tk.Frame(self.bot_note)
        bot_trades = tk.Frame(self.bot_note)
        bot_results = tk.Frame(self.bot_note)
        self.bot_note.add(bot_positions, text="Positions")
        self.bot_note.add(bot_orders, text="Orders")
        self.bot_note.add(bot_trades, text="Trades")
        self.bot_note.add(bot_results, text="Results")

        self.pw_info.add(info_left)
        self.pw_info.bind(
            "<Configure>",
            lambda event: disp.resize_width(event, self.pw_info, disp.window_width // 5.5, 4),
        )

        self.frame_comment = tk.Frame(self.pw_info)
        self.label_comment = tk.Label(self.frame_comment)
        self.label_comment.pack(anchor="center")

        # Widgets dictionaries for bot's data according to self.rows_list
        self.info_name = {}
        self.info_value = {}
        self.info_entry = {}
        current_font = font.nametofont(under_dev_label.cget("font"))
        spec_font = current_font.copy()
        spec_font.config(weight="bold")#, slant="italic")#, size=9)#, underline="True")
        for item in self.rows_list:
            self.info_name[item] = tk.Label(info_left, text=item, font=spec_font)
            self.info_value[item] = tk.Label(info_left, text="")
            if item == "Name":
                self.info_entry[item] = ttk.Entry(
                    info_left, width=24, style="free.TEntry", textvariable=self.name_trace
                )
                self.name_trace.trace_add("write", self.trace_callback)
        self.button_create = tk.Button(
            info_left,
            activebackground=disp.bg_active,
            text="Create Bot",
            command=lambda: self.create_bot(),
            state="disabled",
        )

        # Frame for Bot's algorithm loaded from the strategy.py file
        frame_row += 1
        self.strategy_row = frame_row
        self.strategy = tk.Frame(info_frame)
        self.strategy.grid(row=frame_row, column=0, sticky="NSWE", columnspan=2)
        self.strategy_scroll = AutoScrollbar(self.strategy, orient="vertical")
        self.strategy_text = tk.Text(
            self.strategy, highlightthickness=0, yscrollcommand=self.strategy_scroll.set
        )
        self.strategy_scroll.config(command=self.strategy_text.yview)
        self.strategy_text.grid(row=0, column=0, sticky="NSEW")
        self.strategy_scroll.grid(row=0, column=1, sticky="NS")
        self.strategy.grid_columnconfigure(0, weight=1)
        self.strategy.grid_columnconfigure(1, weight=0)
        self.strategy.grid_rowconfigure(0, weight=1)

        info_frame.grid_columnconfigure(0, weight=0)
        info_frame.grid_columnconfigure(1, weight=1)
        for i in range(frame_row):
            if i == frame_row - 1:
                # self.strategy frame
                info_frame.grid_rowconfigure(frame_row, weight=1)
            else:
                info_frame.grid_rowconfigure(i, weight=0)



# ws = Markets[var.current_market]
# for val in ws.robots:
# print(Markets)

pw_menu_robots = tk.PanedWindow(
    disp.menu_robots,
    orient=tk.HORIZONTAL,
    bd=0,
    sashwidth=0,
    height=1,
)
pw_menu_robots.pack(fill="both", expand="yes")

menu_frame = tk.Frame(pw_menu_robots, relief="sunken", borderwidth=1)
info_frame = tk.Frame(pw_menu_robots)  # , bg=disp.bg_color)

pw_menu_robots.add(menu_frame)
pw_menu_robots.add(info_frame)
pw_menu_robots.bind(
    "<Configure>",
    lambda event: disp.resize_width(event, pw_menu_robots, disp.window_width // 9.5, 6),
)

buttons_menu = SettingsApp(menu_frame)
