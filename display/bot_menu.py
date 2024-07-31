"""
1) Provide database transformations for the following operations:
- (done) New: insert (robots)
- (done) Activate: update STATE (robots)
- (done) Update: update TIMEFRAME, UPDATED (robots)
- (done) Merge: delete record (robots), update EMI (coins)
- (done) Duplicate: insert (robots)
- (done) Delete: delete record (robots), update EMI (coins)
2) Bots with 'Active' state are not allowed for the following services:
- (done) Update: the respective fields, i.g. strategy, must be disabled
- (done) Merge: bot destined to be deleted must have 'Suspended' state
- (done) Delete
3) Bots with active orders are not allowed for the following services:
- Delete: no active orders allowed
- Merge: no active orders allowed for the bot is being deleted
"""

import os
import re
import shutil
import tkinter as tk
import traceback
from datetime import datetime, timezone
from tkinter import StringVar, font, ttk
from typing import Callable

from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name
from pygments.token import Token

import services as service
from common.data import Bot

from .variables import AutoScrollbar, CustomButton, TreeTable
from .variables import Variables as disp
from common.variables import Variables as var


class SettingsApp:
    def __init__(self, root):
        self.root_frame = root
        self.button_height = 25

        self.pop_up = None
        self.selected_bot = ""
        self.algo_dir = f"{os.getcwd()}/algo/"
        self.strategy_file = "strategy.py"
        self.action = ""
        self.timeframes = ("1 min", "5 min", "60 min")
        self.timeframe_trace = StringVar(name=f"timeframe{self}")
        self.timeframe_trace.trace_add("write", self.timeframe_trace_callback)
        self.bot_entry = {}
        self.name_trace = StringVar(name="Name" + str(self))
        self.check_var = tk.IntVar()
        self.button = None

        self.button_list = {
            "Home": "The main page of the bot's menu",
            "New Bot": "Creates bot with a new unique name",
            "Syntax": "Checks whether the bot's algo code syntax is correct",
            "Backtest": "Allows to backtest the bot's trading algorithm",
            "Activate": "Activates or suspends trading according to bot's algorithm",
            "Update": f"Records algo code of selected bot into its {self.strategy_file} file",
            "Merge": "Unites two bots into one. Bot being deleted must have no active orders",
            "Duplicate": "Replicates selected bot, creating a new one with the same parameters",
            "Delete": "This operation completely removes selected bot",
            "Last Viewed": "Shows the last bot selected",
            "Back": "Returns to the main area of Tmatic",
        }
        self.rows_list = [
            "Name",
            "Created",
            "Updated",
            "Timeframe",
            "State",
        ]
        self.bot_options = {
            "State": self.activate,
            "Parameters": self.parameters,
            "Merge": self.merge,
            "Duplicate": self.dublicate,
            "Delete": self.delete,
        }
        self.padx = 10
        self.pady = 5

        self.info_value = {}

        # CustomButton array
        self.buttons_center = []

        for button in self.button_list:
            frame = CustomButton(
                self.root_frame,
                button,
                bg=disp.title_color,
                fg=disp.fg_normal,
                command=self.on_click,
                # activebackground=disp.bg_active,
            )
            self.buttons_center.append(frame)
            # self.button_height = frame.winfo_reqheight()

        # Keeps all bots' names in the array
        # self.bots_list = []
        # self.collect_bots()

        # Keeps the selected bot's algorithm derived from strategy.py file
        self.bot_algo = ""

        # If bot's algorithm is changed by user, than the value in not None
        self.algo_changed = None

        # If bot's timeframe is changed by user, than the value in not None
        self.timeframe_changed = None

        # Create initial frames
        self.bot_info_frame()

    '''def collect_bots(self):
        """Reviews all created bots in the algo directory and puts them in array"""
        self.bots_list.clear()
        for x in os.walk(self.algo_dir):
            my_dir = x[0].replace(self.algo_dir, "")
            if my_dir != "" and my_dir != "__pycache__" and my_dir.find("/") == -1:
                self.bots_list.append(my_dir)'''

    def draw_buttons(self):
        """Draws bot menu buttons accordingly"""
        # self.buttons_center.sort(key=lambda f: f.winfo_y())
        print("_______________draw_buttons")
        """y_pos = 0
        for i, button in enumerate(self.buttons_center):
            if button.name == "Home":
                if self.action != "Last Viewed":
                    button.state = "Disabled"
                else:
                    button.state = "Normal"
            elif button.name == "New Bot":
                button.state = "Normal"
            elif button.name == "Syntax":
                if self.selected_bot == "" or self.action == "Home":
                    button.state = "Disabled"
                else:
                    button.state = "Normal"
            elif button.name == "Activate":
                if self.selected_bot == "" or self.action == "Home":
                    button.state = "Disabled"
                    button.label.config(text="Activate")
                elif self.selected_bot != "":
                    if Bot[self.selected_bot].state == "Active":
                        button.state = "Active"
                        button.label.config(text="Suspend")
                        self.strategy_text.config(state="disabled")
                        self.tm_box.config(state="disabled")
                    else:
                        button.state = "Normal"
                        button.label.config(text="Activate")
                        self.strategy_text.config(state="normal")
                        self.tm_box.config(state="readonly")
            elif button.name == "Update":
                if (
                    self.selected_bot == ""
                    or self.action == "Home"
                    or (self.algo_changed is None and self.timeframe_changed is None)
                ):
                    button.state = "Disabled"
                else:
                    button.state = "Changed"
            elif button.name == "Merge":
                if (
                    self.selected_bot == ""
                    or self.action == "Home"
                    or len(Bot.keys()) < 2
                ):
                    button.state = "Disabled"
                else:
                    button.state = "Normal"
            elif button.name == "Duplicate":
                if self.selected_bot == "" or self.action == "Home":
                    button.state = "Disabled"
                else:
                    button.state = "Normal"
            elif button.name == "Delete":
                if self.selected_bot == "" or self.action == "Home":
                    button.state = "Disabled"
                else:
                    button.state = "Normal"
            elif button.name == "Last Viewed":
                if self.selected_bot == "" or self.action == "Last Viewed":
                    button.state = "Disabled"
                else:
                    button.state = "Normal"
            elif button.name == "Back":
                button.state = "Normal"
            else:
                button.state = "Disabled"
            # button.update_idletasks()
            if button.state == "Normal":
                button.bg = disp.title_color
                button.fg = disp.fg_normal
            elif button.state == "Active":
                button.bg = disp.red_color
                button.fg = disp.white_color
            elif button.state == "Changed":
                button.bg = disp.bg_changed
                button.fg = disp.black_color
            else:
                button.bg = disp.title_color
                button.fg = disp.fg_disabled
            button.label.config(bg=button.bg, fg=button.fg)
            button.pack(fill="both", pady=2)"""
        """if i == 0:
                y_pos = int(self.button_height / 1.7)
            else:
                if button.name == "Syntax" or button.name == "Update" or button.name == "Last Viewed":
                    y_pos += int(self.button_height / 2)
            button.place_configure(
                x=0, y=y_pos, height=self.button_height, relwidth=1.0
            )
            y_pos += int(self.button_height) + 1"""

    def name_trace_callback(self, var, index, mode):
        name = var.replace(str(self), "")
        bot_name = re.sub("[\W]+", "", self.name_trace.get())
        if (
            bot_name in Bot.keys()
            or bot_name != self.name_trace.get()
            or bot_name == ""
        ):
            self.bot_entry[name].config(style="used.TEntry")
            self.button.config(state="disabled")
        else:
            self.bot_entry[name].config(style="free.TEntry")
            self.button.config(state="normal")

    def open_popup(self, action, bot_name):
        if self.pop_up:
            self.pop_up.destroy()
        self.pop_up = tk.Toplevel()
        win_height = 350
        self.pop_up.geometry(f"750x{win_height}")

        if action == "New Bot":
            self.pop_up.title(action)
            tk.Label(
                self.pop_up, text="\n\n\nCreate a new bot\nwith a unique name:"
            ).pack(anchor="n")
            self.bot_entry["Name"] = ttk.Entry(
                self.pop_up,
                width=20,
                style="free.TEntry",
                textvariable=self.name_trace,
            )
            self.bot_entry["Name"].pack(anchor="n")
            self.name_trace.trace_add("write", self.name_trace_callback)
            tk.Label(self.pop_up, text="Select timeframe:").pack(anchor="n")

            timeframe = ttk.Combobox(self.pop_up, width=7, state="readonly")
            timeframe["values"] = self.timeframes
            timeframe.current(1)
            timeframe.pack(anchor="n")

            self.button = tk.Button(
                self.pop_up,
                activebackground=disp.bg_active,
                text="Create Bot",
                command=lambda: self.create_bot(
                    self.name_trace.get(), timeframe["values"][timeframe.current()]
                ),
                state="disabled",
            )
            self.bot_entry["Name"].delete(0, tk.END)
            self.button.pack(anchor="n", pady=25)
        elif action == "Syntax":
            self.pop_up.title(f"Check syntax for: {bot_name}")
            content = self.strategy_text.get("1.0", tk.END)
            is_syntax_correct, error_message = self.check_syntax(content)
            if is_syntax_correct:
                tk.Label(self.pop_up, text="The bot's code syntax is correct").pack(
                    anchor="n", pady=100
                )
                self.insert_code(self.strategy_text, content, bot_name)
            else:
                scroll = AutoScrollbar(self.pop_up, orient="vertical")
                text = tk.Text(
                    self.pop_up,
                    highlightthickness=0,
                    yscrollcommand=scroll.set,
                    bg=disp.title_color,
                )
                scroll.config(command=text.yview)
                text.grid(row=0, column=0, sticky="NSEW")
                scroll.grid(row=0, column=1, sticky="NS")
                self.pop_up.grid_columnconfigure(0, weight=1)
                self.pop_up.grid_columnconfigure(1, weight=0)
                self.pop_up.grid_rowconfigure(0, weight=1)
                text.insert(tk.END, error_message)
                text.config(state="disabled")
        elif action == "Merge":
            self.pop_up.title(f"{action}: {bot_name}")
            bots = []
            for item in Bot.keys():
                if item != self.selected_bot and Bot[item].state == "Suspended":
                    bots.append(item)
            if len(bots) < 1:
                tk.Label(
                    self.pop_up,
                    text=f"\n\n\n\n\nNo available bots to be merged with.\nOnly bots with state 'Suspended' allowed.",
                ).pack(anchor="center")
            else:
                content = f"\n\nTo merge bot named '{self.selected_bot}'\nplease select one of the bots below\navailable to be merged with:"
                tk.Label(self.pop_up, text=content).pack(anchor="n")
                cbox = ttk.Combobox(
                    self.pop_up, width=15, textvariable="", state="readonly"
                )
                cbox["values"] = tuple(bots)
                cbox.current(0)
                cbox.pack(anchor="n")
                tk.Label(
                    self.pop_up,
                    text=f"\nAs a result of merge operation\nthe selected bot will be deleted.\nAll its records in the database\nwill move on to bot '{self.selected_bot}'",
                ).pack(anchor="center")
                self.check_var.set(0)
                confirm = tk.Checkbutton(
                    self.pop_up,
                    text="Confirm operation",
                    variable=self.check_var,
                    command=self.check_button,
                )
                confirm.pack(anchor="n")
                self.button = tk.Button(
                    self.pop_up,
                    activebackground=disp.bg_active,
                    text="Merge Bot",
                    command=lambda: self.merge_bot(
                        bot_name, cbox["values"][cbox.current()]
                    ),
                    state="disabled",
                )
                self.button.pack(anchor="n")
        elif action == "Duplicate":
            self.pop_up.title(f"{action}: {bot_name}")
            content = f"\nYou are about to duplicate bot named '{self.selected_bot}'.\nThe newly created bot will get the same set\nof parameters as '{self.selected_bot}' currently has."
            tk.Label(self.pop_up, text=content).pack(anchor="n", pady=25)
            tk.Label(self.pop_up, text="Enter a unique name").pack(anchor="n")
            self.bot_entry["Name"] = ttk.Entry(
                self.pop_up,
                width=20,
                style="free.TEntry",
                textvariable=self.name_trace,
            )
            self.bot_entry["Name"].pack(anchor="n")
            self.name_trace.trace_add("write", self.name_trace_callback)
            self.button = tk.Button(
                self.pop_up,
                activebackground=disp.bg_active,
                text="Duplicate Bot",
                command=lambda: self.duplicate_bot(bot_name, self.name_trace.get()),
                state="disabled",
            )
            self.bot_entry["Name"].delete(0, tk.END)
            self.bot_entry["Name"].insert(0, bot_name)
            self.button.pack(anchor="n")
        elif action == "Delete":
            self.pop_up.title(f"Delete: {bot_name}")
            if Bot[bot_name].state == "Active":
                tk.Label(
                    self.pop_up,
                    text=f"\n\n\n\n\nThe delete operation is not allowed\nif the bot is in the 'Active' state.\n\nClick the 'Suspend' button before deleting.",
                ).pack(anchor="center")
            else:
                content = f"\n\nAfter you press the 'Delete Bot' button,\nthe '/algo/{self.selected_bot}/' subdirectory will be erased\nand this bot will no longer exist.\n\nThe 'EMI' fields in the database for this bot\nwill take the 'SYMBOL' fields values."
                tk.Label(self.pop_up, text=content).pack(anchor="n")
                self.check_var.set(0)
                confirm = tk.Checkbutton(
                    self.pop_up,
                    text="Confirm operation",
                    variable=self.check_var,
                    command=self.check_button,
                )
                confirm.pack(anchor="n")
                self.button = tk.Button(
                    self.pop_up,
                    activebackground=disp.bg_active,
                    text="Delete Bot",
                    command=lambda: self.delete_bot(bot_name),
                    state="disabled",
                )
                self.button.pack(anchor="n")

    def check_button(self):
        if self.check_var.get() == 1:
            self.button.config(state="normal")
        else:
            self.button.config(state="disabled")

    def check_syntax(self, code):
        try:
            # Compile the code to check for syntax errors
            compiled_code = compile(code, "<string>", "exec")
            # Execute the compiled code to check for runtime errors
            # exec(compiled_code, {})
            return True, None
        except (SyntaxError, Exception) as e:
            return False, traceback.format_exc()

    def on_click(self, name):
        if name == "Home":
            self.action = "Home"
            self.show_bot()
        elif name == "New Bot":
            self.open_popup(name, "")
        elif name == "Syntax":
            self.open_popup(name, self.selected_bot)
        elif name == "Activate":
            if Bot[self.selected_bot].state == "Suspended":
                new_state = "Active"
            else:
                new_state = "Suspended"
            err = service.update_database(
                query=f"UPDATE robots SET STATE = '{new_state}' WHERE EMI = '{self.selected_bot}'"
            )
            if err is None:
                Bot[self.selected_bot].state = new_state
                self.show_bot()
        elif name == "Update":
            tf_value = self.timeframe_trace.get().split(" ")
            err = service.update_database(
                query=f"UPDATE robots SET TIMEFR = {tf_value[0]}, UPDATED = CURRENT_TIMESTAMP WHERE EMI = '{self.selected_bot}'"
            )
            if err is None:
                self.write_file(
                    f"{self.get_bot_path(self.selected_bot)}/{self.strategy_file}",
                    self.strategy_text.get("1.0", tk.END),
                )
                Bot[self.selected_bot].timefr = int(tf_value[0])
                Bot[self.selected_bot].updated = self.get_time()
                self.algo_changed = None
                self.timeframe_changed = None
                self.draw_buttons()
                self.tm_box.config(style=f"default.TCombobox")
                self.strategy_text.config(
                    highlightbackground=disp.title_color,
                    highlightcolor=disp.title_color,
                )
        elif name == "Merge":
            self.open_popup(name, self.selected_bot)
        elif name == "Duplicate":
            self.open_popup(name, self.selected_bot)
        elif name == "Delete":
            self.open_popup(name, self.selected_bot)
        elif name == "Last Viewed":
            self.action = name
            self.show_bot()
        elif name == "Back":
            disp.menu_robots.pack_forget()
            disp.pw_rest1.pack(fill="both", expand="yes")

    def timeframe_trace_callback(self, name, index, mode):
        value = self.timeframe_trace.get().split(" ")
        if (
            self.selected_bot in Bot.keys()
            and int(value[0]) != Bot[self.selected_bot].timefr
        ):
            if self.timeframe_changed is None:
                self.timeframe_changed = "changed"
                self.tm_box.config(style=f"changed.TCombobox")
                self.draw_buttons()
        else:
            if self.timeframe_changed is not None:
                self.timeframe_changed = None
                self.tm_box.config(style=f"default.TCombobox")
                self.draw_buttons()

    def show_bot(self):
        """Shows the bot's info when bot is selected. Otherwise hides"""
        print("______________show_bot")
        if self.selected_bot != "" and self.action != "Home":
            # d self.menu_usage.pack_forget()
            # d self.bots_button.pack_forget()
            # d self.bots_label.pack_forget()
            self.brief_frame.pack_forget()
            # d self.main_frame.pack(fill="both", expand="yes")
            bot_path = self.get_bot_path(self.selected_bot)
            bot = Bot[self.selected_bot]
            for item in self.rows_list:
                if item == "Name":
                    self.info_value[item].config(text=self.selected_bot)
                    self.bot_algo = self.read_file(f"{bot_path}/{self.strategy_file}")
                    self.insert_code(
                        self.strategy_text, self.bot_algo, self.selected_bot
                    )
                elif item == "Created":
                    self.info_value[item].config(text=bot.created)
                elif item == "Updated":
                    self.info_value[item].config(text=bot.updated)
                elif item == "Timeframe":
                    self.tm_box.current(
                        self.tm_box["values"].index(f"{bot.timefr} min")
                    )
                elif item == "State":
                    self.info_value[item].config(text=bot.state)
        else:
            # d self.main_frame.pack_forget()
            self.brief_frame.pack(fill="both", expand="yes", anchor="n")
            """if len(Bot.keys()) != 0:
                self.bots_label.pack(anchor="n")
                #d self.bots_button.pack(anchor="n")
                self.menu_usage.pack(anchor="n", pady=50)
            else:
                self.menu_usage.pack(anchor="n", pady=50)"""
        self.algo_changed = None
        self.draw_buttons()

    def create_file(self, file_name):
        # os.mknod(file_name)
        open(
            file_name,
            "w",
        ).close()

    def read_file(self, file_name):
        file = open(file_name, "r")
        content = file.read()
        file.close()
        return content

    def write_file(self, file_name, content):
        file = open(file_name, "w")
        file.write(content)
        file.close()

    def get_bot_path(self, bot_name):
        return os.path.join(self.algo_dir, bot_name)

    def get_time(self):
        my_time = str(datetime.now(tz=timezone.utc)).split(".")
        return my_time[0]

    def create_bot(self, bot_name, timeframe):
        tf = timeframe.split(" ")
        err = service.insert_database(
            values=[bot_name, "Suspended", tf[0]], table="robots"
        )
        if err is None:
            bot_path = self.get_bot_path(bot_name)
            # Create a new directory with the name as the new bot's name
            os.mkdir(bot_path)
            # Create the '__init__.py' file in the new directory. This file is empty
            self.create_file(f"{str(bot_path)}/__init__.py")
            # Load the content of 'init.py' file
            content = self.read_file(f"{self.algo_dir}init.py")
            # Create new 'init.py' file in the new directory
            self.create_file(f"{str(bot_path)}/init.py")
            # Write the initial content into the new 'init.py' file
            self.write_file(f"{str(bot_path)}/init.py", content)
            # Create new 'strategy.py' file in the new directory
            self.create_file(f"{str(bot_path)}/{self.strategy_file}")
            # Write the initial content into the new 'strategy.py' file
            self.write_file(
                f"{str(bot_path)}/{self.strategy_file}",
                "import services as service\nfrom api.api import Markets\nfrom common.data import Instrument\nfrom functions import Function\n",
            )
            # Create new '.gitignore' file in the new directory
            self.create_file(f"{str(bot_path)}/.gitignore")
            # Write the initial content into the new '.gitignore' file
            self.write_file(
                f"{str(bot_path)}/.gitignore",
                f"*\n!__init__.py\n!.gitignore\n!init.py\n!{self.strategy_file}\n",
            )
            time_now = self.get_time()
            Bot[bot_name].state = "Suspended"
            Bot[bot_name].timefr = int(tf[0])
            Bot[bot_name].created = time_now
            Bot[bot_name].updated = time_now
            self.after_popup(bot_name)

    def merge_bot(self, bot_name, bot_to_delete):
        err = service.update_database(
            query=f"UPDATE coins SET EMI = '{bot_name}' WHERE EMI = '{bot_to_delete}'"
        )
        if err is None:
            err = service.update_database(
                query=f"DELETE FROM robots WHERE EMI = '{bot_to_delete}'"
            )
            if err is None:
                bot_path = self.get_bot_path(bot_to_delete)
                shutil.rmtree(str(bot_path))
                Bot.remove(bot_to_delete)
                self.after_popup(bot_name)

    def delete_bot(self, bot_name):
        err = service.update_database(
            query=f"UPDATE coins SET EMI = SYMBOL WHERE EMI = '{bot_name}'"
        )
        if err is None:
            err = service.update_database(
                query=f"DELETE FROM robots WHERE EMI = '{bot_name}'"
            )
            if err is None:
                bot_path = self.get_bot_path(bot_name)
                shutil.rmtree(str(bot_path))
                Bot.remove(bot_name)
                self.after_popup("")

    def duplicate_bot(self, bot_name, copy_bot):
        err = service.insert_database(
            values=[copy_bot, "Suspended", Bot[bot_name].timefr], table="robots"
        )
        if err is None:
            shutil.copytree(self.get_bot_path(bot_name), self.get_bot_path(copy_bot))
            time_now = self.get_time()
            Bot[copy_bot].state = "Suspended"
            Bot[copy_bot].timefr = Bot[bot_name].timefr
            Bot[copy_bot].created = time_now
            Bot[copy_bot].updated = time_now
            self.after_popup(copy_bot)

    def after_popup(self, bot_name):
        if bot_name != "":
            self.selected_bot = bot_name
            self.action = "Last Viewed"
        else:
            self.selected_bot = ""
            self.action = ""
        self.menu_usage.pack_forget()
        self.bots_button.pack_forget()
        self.bots_label.pack_forget()
        self.create_bots_menu()
        self.show_bot()
        self.pop_up.destroy()

    def insert_code(self, text_widget, code, bot_name):
        """Function to insert Python code into a Tkinter Text widget with syntax highlighting"""
        self.strategy_text.config(state="normal")
        text_widget.delete(1.0, tk.END)
        lexer = PythonLexer()
        # You can change the style if desired. More info at https://pygments.org/styles/
        style = get_style_by_name("default")
        for token, content in lex(code, lexer):
            tag_name = str(token)
            text_widget.insert(tk.END, content, tag_name)
            # Configure the tag if it hasn't been already
            if not text_widget.tag_cget(tag_name, "foreground"):
                color = style.style_for_token(token).get("color")
                if color:
                    text_widget.tag_configure(tag_name, foreground="#" + color)
        if Bot[bot_name] == "Active":
            self.strategy_text.config(state="disabled")

    def on_menu_select(self, value):
        self.selected_bot = value
        self.action = "Last Viewed"
        self.show_bot()

    def create_bots_menu(self):
        # Menu to choose one of the created bots
        print("_________________create_bots_menu")
        """self.bots_button = tk.Menubutton(
            self.brief_frame,
            text=" LIST OF CREATED BOTS ",
            relief=tk.GROOVE,
            padx=0,
            pady=0,
            activebackground=disp.bg_active,
            # bg=disp.bg_select_color,
        )
        main_menu = tk.Menu(self.bots_button, tearoff=0)
        self.bots_button.config(menu=main_menu)
        for option in Bot.keys():
            main_menu.add_command(
                label=option,
                command=lambda value=option: self.on_menu_select(value),
            )"""

        # new

        tree = TreeTable.bot_menu
        for name in Bot.keys():
            tree.insert_hierarchical(parent="", iid=name, text=name, configure="Gray")
            for option in self.bot_options.keys():
                iid = f"{name}!{option}"
                tree.insert_hierarchical(
                    parent=name, iid=iid, text=option, configure="White"
                )
        tree.insert_hierarchical(parent="", iid="New_bot!", text="Add new bot")
        tree.insert_hierarchical(parent="", iid="Back!", text="Back")

        # Init option frames

        self.brief_frame = tk.Frame(info_right, bg=disp.bg_color)
        self.brief_frame.bind('<Configure>', self.wrap)
        """self.frame_activate = tk.Frame(self.brief_frame)
        self.frame_parameters = tk.Frame(self.brief_frame)
        self.frame_merge = tk.Frame(self.brief_frame)
        self.frame_dublicate = tk.Frame(self.brief_frame)
        self.frame_delete = tk.Frame(self.brief_frame)

        self.label_activate = tk.Label(self.frame_activate, text="Activate")
        self.label_parameters = tk.Label(self.frame_parameters, text="Parameters")
        self.label_merge = tk.Label(self.frame_merge, text="Merge")
        self.label_dublicate = tk.Label(self.frame_dublicate, text="Dublicate")
        self.label_delete = tk.Label(self.frame_delete, text="Delete")

        self.label_activate.pack()
        self.label_parameters.pack()
        self.label_merge.pack()
        self.label_dublicate.pack()
        self.label_delete.pack()"""

    def on_modify_strategy(self, event):
        value = self.strategy_text.get("1.0", tk.END)
        if value != self.bot_algo:
            if self.algo_changed is None:
                self.algo_changed = "changed"
                self.strategy_text.config(
                    highlightbackground=disp.bg_changed, highlightcolor=disp.bg_changed
                )
                self.draw_buttons()
        else:
            if self.algo_changed is not None:
                self.algo_changed = None
                self.strategy_text.config(
                    highlightbackground=disp.title_color,
                    highlightcolor=disp.title_color,
                )
                self.draw_buttons()

    def ignore_text_input(self, event):
        return "break"

    def bot_info_frame(self):
        """Frames, grids, widgets are here"""
        label_example = tk.Label(text="")
        current_font = font.nametofont(label_example.cget("font"))
        spec_font = current_font.copy()
        spec_font.config(
            weight="bold"
        )  # , slant="italic")#, size=9)#, underline="True")

        # Frame to depict menu page after Home button pressing

        """ self.bots_label = tk.Label(
             self.brief_frame, text="\n\nSelect bot from:", font=spec_font
         )
        self.menu_usage = tk.Frame(self.brief_frame)

        # This block draws the bots' menu titles with its description
        row_num = 0
        col_num = 0
        usage = {}
        for key, value in self.button_list.items():
            usage[key] = tk.Frame(self.menu_usage)
            usage[key].grid(row=row_num, column=col_num, padx=5)
            tk.Label(usage[key], text=key, font=spec_font).pack(anchor="w")
            text = tk.Text(
                usage[key],
                width=20,
                height=5,
                bg=disp.title_color,
                wrap=tk.WORD,
                bd=0,
                highlightthickness=0,
            )
            text.pack(anchor="w")
            text.bind("<Key>", self.ignore_text_input)
            text.insert(tk.END, value)
            col_num += 1
            if row_num == 0:
                self.menu_usage.grid_columnconfigure(col_num, weight=0)
            if col_num == 4:
                self.menu_usage.grid_rowconfigure(row_num, weight=0)
                col_num = 0
                row_num += 1"""

        """for key, value in self.button_list.items():
            if key == "Home":
                tk.Label(self.menu_usage, text="USE ONE OF THE MENU BUTTONS:").pack(
                    anchor="w"
                )
            else:
                if row_num % 2 == 0:
                    tk.Label(self.menu_usage, text=f"'{key}' {value}").pack(
                        anchor="w", padx=25, pady=10
                    )
                else:
                    tk.Label(self.menu_usage, text=f"'{key}' {value}").pack(
                        anchor="w", padx=25
                    )
                row_num += 1"""

        # Frame to depict selected bot info
        # d self.main_frame = tk.Frame(info_frame)
        """frame_row = 0
        top_frame = tk.Frame(self.main_frame)
        top_frame.grid(row=frame_row, column=0, sticky="NSEW", columnspan=2)
        under_dev_label = tk.Label(
            top_frame, text="This page is under development", fg=disp.red_color
        )
        under_dev_label.pack(anchor="center")

        empty_frame = []
        empty_frame_label = []
        for i in range(10):
            frame_row += 1
            empty_frame.append(tk.Frame(self.main_frame))
            empty_frame[i].grid(row=frame_row, column=0, sticky="NSEW")
            empty_frame_label.append(tk.Label(empty_frame[i], text=" "))
            empty_frame_label[i].pack(anchor="w")

        filled_frame = tk.Frame(self.main_frame)
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
            bot_note = ttk.Notebook(self.pw_info, padding=(-9, 0, -9, -9))
        else:
            bot_note = ttk.Notebook(self.pw_info, padding=0)
        bot_positions = tk.Frame(bot_note)
        bot_orders = tk.Frame(bot_note)
        bot_trades = tk.Frame(bot_note)
        bot_results = tk.Frame(bot_note)
        bot_note.add(bot_positions, text="Positions")
        bot_note.add(bot_orders, text="Orders")
        bot_note.add(bot_trades, text="Trades")
        bot_note.add(bot_results, text="Results")

        self.pw_info.add(info_left)
        self.pw_info.add(bot_note)
        self.pw_info.bind(
            "<Configure>",
            lambda event: disp.resize_width(
                event, self.pw_info, disp.window_width // 5.5, 4
            ),
        )

        # Widgets dictionaries for bot's data according to self.rows_list
        self.info_name = {}
        self.info_value = {}
        for item in self.rows_list:
            self.info_name[item] = tk.Label(info_left, text=item, font=spec_font)
            self.info_name[item].pack(anchor="w")
            if item == "Timeframe":
                self.tm_box = ttk.Combobox(
                    info_left,
                    width=7,
                    textvariable=self.timeframe_trace,
                    state="readonly",
                    style="default.TCombobox",
                )
                self.tm_box["values"] = self.timeframes
                self.tm_box.pack(anchor="w")
            else:
                self.info_value[item] = tk.Label(info_left, text="")
                self.info_value[item].pack(anchor="w")

        # Frame for Bot's algorithm loaded from the strategy.py file
        frame_row += 1
        self.strategy = tk.Frame(self.main_frame)
        self.strategy.grid(row=frame_row, column=0, sticky="NSWE", columnspan=2)
        self.strategy_scroll = AutoScrollbar(self.strategy, orient="vertical")
        self.strategy_text = tk.Text(
            self.strategy,
            highlightthickness=3,
            highlightbackground=disp.title_color,
            highlightcolor=disp.title_color,
            yscrollcommand=self.strategy_scroll.set,
        )
        self.strategy_text.bind("<KeyRelease>", self.on_modify_strategy)
        self.strategy_scroll.config(command=self.strategy_text.yview)
        self.strategy_text.grid(row=0, column=0, sticky="NSEW")
        self.strategy_scroll.grid(row=0, column=1, sticky="NS")
        self.strategy.grid_columnconfigure(0, weight=1)
        self.strategy.grid_columnconfigure(1, weight=0)
        self.strategy.grid_rowconfigure(0, weight=1)

        self.main_frame.grid_columnconfigure(0, weight=0)
        self.main_frame.grid_columnconfigure(1, weight=1)
        for i in range(frame_row):
            self.main_frame.grid_rowconfigure(i, weight=0)
        self.main_frame.grid_rowconfigure(frame_row, weight=1)"""

    def activate(self, bot_name: str) -> str:
        def return_text():
            nonlocal new_state
            if bot.state == "Active":
                new_state = "Suspended"
            else:
                new_state = "Active"
            TEXT = "The bot {NAME} has the state <{STATE}>. You are about to change the state to <{CHANGE}>."
            return TEXT.format(NAME=bot_name, STATE=bot.state, CHANGE=new_state)
        
        def change_state() -> None:
            nonlocal new_state
            print("___change state")
            err = service.update_database(
                query=f"UPDATE robots SET STATE = '{new_state}' WHERE EMI = '{self.selected_bot}'"
            )
            if err is None:
                bot.state = new_state
                values = [bot_name, bot.timefr, bot.state, bot.created, bot.updated]
                TreeTable.bot_info.update(row=0, values=values)
                text_label["text"] = return_text()

        new_state = ""
        bot = Bot[bot_name]        
        #tk.Label(self.brief_frame, text="", bg=disp.bg_color).pack(anchor="nw", padx=self.padx, pady=self.pady)
        text_label = tk.Label(
            self.brief_frame,
            text=return_text(), 
            bg=disp.bg_color,
            justify=tk.LEFT, 
        )
        text_label.pack(anchor="nw", padx=self.padx, pady=self.pady)
        self.button = tk.Button(
            self.brief_frame,
            activebackground=disp.bg_active,
            text="Update",
            command=lambda: change_state(),
            #state="disabled",
        )
        self.button.pack(anchor="nw", padx=50, pady=10)
        '''err = service.update_database(
                        query=f"UPDATE robots SET STATE = '{new_state}' WHERE EMI = '{self.selected_bot}'"
                    )
                    if err is None:
                        Bot[self.selected_bot].state = new_state
                        self.show_bot()'''

    def parameters(self, bot_name: str):
        print("_______parameters_______", bot_name)

    def merge(self, bot_name: str):
        print("_______merge_______", bot_name)

    def dublicate(self, bot_name: str):
        print("_______dublicate_______", bot_name)

    def delete(self, bot_name: str):
        print("_______delete_______", bot_name)

    def new_bot(self):
        values = ["" for _ in var.name_bot]
        TreeTable.bot_info.update(row=0, values=values)
        tk.Label(
            self.brief_frame,
            text="Create a new bot with a unique name:",
            bg=disp.bg_color,
            justify=tk.LEFT, 
        ).pack(anchor="nw", padx=self.padx, pady=self.pady)
        self.bot_entry["Name"] = ttk.Entry(
            self.brief_frame,
            width=20,
            style="free.TEntry",
            textvariable=self.name_trace,
        )
        self.bot_entry["Name"].pack(anchor="nw", padx=50, pady=0)
        self.name_trace.trace_add("write", self.name_trace_callback)
        tk.Label(self.brief_frame, text="Select timeframe:", bg=disp.bg_color, justify=tk.LEFT).pack(
            anchor="nw", padx=self.padx, pady=self.pady
        )
        timeframe = ttk.Combobox(self.brief_frame, width=7, state="readonly")
        timeframe["values"] = self.timeframes
        timeframe.current(1)
        timeframe.pack(anchor="nw", padx=50, pady=0)
        self.button = tk.Button(
            self.brief_frame,
            activebackground=disp.bg_active,
            text="Create Bot",
            command=lambda: self.create_bot(
                self.name_trace.get(), timeframe["values"][timeframe.current()]
            ),
            state="disabled",
        )
        self.bot_entry["Name"].delete(0, tk.END)
        self.button.pack(anchor="nw", padx=50, pady=20)

    def show(self, bot_name):
        bot = Bot[bot_name]
        values = [bot_name, bot.timefr, bot.state, bot.created, bot.updated]
        TreeTable.bot_info.update(row=0, values=values)

    def wrap(self, event):
        for child in buttons_menu.brief_frame.winfo_children():
            if type(child) is tk.Label:
                child.config(wraplength=self.brief_frame.winfo_width() - self.padx * 2)


def handler_bot_menu(event) -> None:
    tree = event.widget
    iid = tree.selection()[0]
    TreeTable.bot_menu.on_rollup(iid)
    option = iid.split("!")
    parent = option[0]
    if len(option) == 1:
        option = ""
    else:
        option = option[1]
    for child in buttons_menu.brief_frame.winfo_children():
        child.destroy()
    if parent == "Back":
        disp.menu_robots.pack_forget()
        disp.pw_rest1.pack(fill="both", expand="yes")
    elif parent == "New_bot":
        buttons_menu.new_bot()
    elif not option:
        buttons_menu.show(parent)
    else:
        buttons_menu.bot_options[option](bot_name=parent)


pw_menu_robots = tk.PanedWindow(
    disp.menu_robots,
    orient=tk.HORIZONTAL,
    bd=0,
    sashwidth=0,
    height=1,
)
pw_menu_robots.pack(fill="both", expand="yes")

menu_frame = tk.Frame(pw_menu_robots)
info_frame = tk.Frame(pw_menu_robots, bg=disp.bg_color)  # , bg=disp.bg_color)
frame_bot_info = tk.Frame(info_frame)  # , bg=disp.bg_color)
frame_bot_info.pack(fill="both", anchor="n")
info_left = tk.Frame(info_frame, bg="#999999")
info_right = tk.Frame(info_frame, bg="#999999")
info_left.pack(fill="both", side="left")
info_right.pack(fill="both", expand=True, side="left")

pw_menu_robots.add(menu_frame)
pw_menu_robots.add(info_frame)
pw_menu_robots.bind(
    "<Configure>",
    lambda event: disp.resize_width(event, pw_menu_robots, disp.window_width // 7, 6),
)

buttons_menu = SettingsApp(menu_frame)
