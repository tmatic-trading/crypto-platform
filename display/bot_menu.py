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
import time
import tkinter as tk
import traceback
from collections import OrderedDict
from datetime import datetime, timezone
from tkinter import StringVar, font, ttk
from typing import Union

from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name
from pygments.token import Token

import functions
import services as service
from api.api import Markets
from common.data import Bots
from common.variables import Variables as var

from .variables import AutoScrollbar, TreeTable, TreeviewTable
from .variables import Variables as disp

# from display.messages import ErrorMessage


class BoldLabel(tk.Label):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        bold_font = font.Font(self, self.cget("font"))
        bold_font.configure(weight="bold")
        self.configure(font=bold_font)


class SettingsApp:
    def __init__(self, root):
        # self.root_frame = root
        # self.button_height = 25
        self.button_strategy = None

        # self.pop_up = None
        # self.selected_bot = ""
        self.algo_dir = f"{os.getcwd()}/algo/"
        self.strategy_file = "strategy.py"
        # self.action = ""
        self.timeframes = OrderedDict([("1 min", 1), ("5 min", 5), ("60 min", 60)])
        # self.timeframe_trace = StringVar(name=f"timeframe{self}")
        # self.timeframe_trace.trace_add("write", self.timeframe_trace_callback)
        self.bot_entry = {}
        self.name_trace = StringVar(name="Name" + str(self))
        self.name_trace.trace_add("write", self.name_trace_callback)
        self.check_var = tk.IntVar()
        self.button = None
        self.bot_options = {
            "State": self.activate,
            "Parameters": self.parameters,
            "Merge": self.merge,
            "Duplicate": self.dublicate,
            "Delete": self.delete,
        }
        self.padx = 10
        self.pady = 5
        with open("display/new_bot_text.txt", "r") as f:
            self.new_bot_text = f.read()
        with open("display/example_strategy.txt", "r") as f:
            self.example_strategy = f.read()

        self.info_value = {}

        # Keeps the selected bot's algorithm derived from strategy.py file
        self.bot_algo = ""

        # If bot's timeframe is changed by user, than the value in not None
        # self.timeframe_changed = None

        # Create initial frames
        # self.bot_info_frame()

    def name_trace_callback(self, var, index, mode):
        name = var.replace(str(self), "")
        bot_name = re.sub("[\W]+", "", self.name_trace.get())
        if (
            bot_name in Bots.keys()
            or bot_name != self.name_trace.get()
            or bot_name == ""
        ):
            self.bot_entry[name].config(style="used.TEntry")
            self.button.config(state="disabled")
        else:
            self.bot_entry[name].config(style="free.TEntry")
            self.button.config(state="normal")

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

    """def timeframe_trace_callback(self, name, index, mode):
        value = self.timeframe_trace.get().split(" ")
        if (
            self.selected_bot in Bots.keys()
            and int(value[0]) != Bots[self.selected_bot].timefr
        ):
            if self.timeframe_changed is None:
                self.timeframe_changed = "changed"
        else:
            if self.timeframe_changed is not None:
                self.timeframe_changed = None"""

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

    def get_bot_path(self, bot_name: str) -> str:
        return os.path.join(self.algo_dir, bot_name)

    def get_time(self) -> str:
        my_time = str(datetime.now(tz=timezone.utc)).split(".")

        return my_time[0]

    def create_bot(self, bot_name, timeframe) -> bool:
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
            # d Load the content of 'init.py' file
            # d content = self.read_file(f"{self.algo_dir}init.py")
            # Create new 'init.py' file in the new directory
            self.create_file(f"{str(bot_path)}/init.py")
            # Write the initial content into the new 'init.py' file
            # d self.write_file(f"{str(bot_path)}/init.py", content)
            # Create new 'strategy.py' file in the new directory
            self.create_file(f"{str(bot_path)}/{self.strategy_file}")
            # Write the initial content into the new 'strategy.py' file
            self.write_file(
                f"{str(bot_path)}/{self.strategy_file}",
                self.example_strategy,
            )
            # Create new '.gitignore' file in the new directory
            self.create_file(f"{str(bot_path)}/.gitignore")
            # Write the initial content into the new '.gitignore' file
            self.write_file(
                f"{str(bot_path)}/.gitignore",
                f"*\n!__init__.py\n!.gitignore\n!init.py\n!{self.strategy_file}\n",
            )
            time_now = self.get_time()
            Bots[bot_name].state = "Suspended"
            Bots[bot_name].timefr = int(tf[0])
            Bots[bot_name].created = time_now
            Bots[bot_name].updated = time_now
            self.insert_bot_menu(name=bot_name, new=True)

            return True

    def insert_code(self, text_widget: tk.Text, code: str, bot_name: str) -> None:
        """
        Function to insert Python code into a Tkinter Text widget with syntax
        highlighting.
        """
        text_widget.config(state="normal")
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
        if Bots[bot_name] == "Active":
            text_widget.config(state="disabled")

    def insert_bot_menu(self, name: str, new=False) -> None:
        tree = TreeTable.bot_menu
        tree.insert_hierarchical(
            parent="", iid=name, text=name, configure="Gray", new=new
        )
        for option in self.bot_options.keys():
            iid = f"{name}!{option}"
            tree.insert_hierarchical(
                parent=name, iid=iid, text=option, configure="White"
            )

    def create_bots_menu(self):
        """
        Menu to choose one of the created bots
        """
        tree = TreeTable.bot_menu
        for name in reversed(Bots.keys()):
            self.insert_bot_menu(name)
        tree.insert_hierarchical(parent="", iid="New_bot!", text="Add new bot")
        tree.insert_hierarchical(parent="", iid="Back!", text="Back")
        self.brief_frame = tk.Frame(info_right, bg=disp.bg_color)
        self.brief_frame.pack(fill="both", expand="yes", anchor="n")
        self.brief_frame.bind("<Configure>", self.wrap)
        self.create_strategy_widget()

    def create_strategy_widget(self) -> None:
        def update_strategy() -> None:
            content = self.strategy_text.get("1.0", tk.END)
            bot_path = self.get_bot_path(disp.bot_name)
            self.write_file(f"{str(bot_path)}/{self.strategy_file}", content)
            self.button_strategy.config(state="disabled")
            self.bot_algo = content
            self.insert_code(
                text_widget=self.strategy_text,
                code=content,
                bot_name=disp.bot_name,
            )

        def check_syntax() -> None:
            content = self.strategy_text.get("1.0", tk.END)
            is_syntax_correct, error_message = self.check_syntax(content)
            if is_syntax_correct:
                functions.warning_window(
                    "The bot's code syntax is correct", title="Syntax check"
                )
                self.insert_code(
                    text_widget=self.strategy_text,
                    code=content,
                    bot_name=disp.bot_name,
                )
            else:
                functions.warning_window(error_message, width=1000, height=300)

        frame_title = tk.Frame(frame_strategy)
        frame_title.grid(row=0, column=0, sticky="NSEW", columnspan=2)
        title = BoldLabel(frame_title, text="STRATEGY")
        title.grid(row=0, column=0, sticky="NSEW")

        self.button_strategy = tk.Button(
            frame_title,
            activebackground=disp.bg_active,
            text="Update strategy",
            command=lambda: update_strategy(),
            state="disabled",
            pady=0,
        )
        self.button_strategy.grid(row=0, column=1)

        button_syntax = tk.Button(
            frame_title,
            activebackground=disp.bg_active,
            text="Check syntax",
            command=lambda: check_syntax(),
            pady=0,
        )
        button_syntax.grid(row=0, column=2)

        button_backtest = tk.Button(
            frame_title,
            activebackground=disp.bg_active,
            text="Backtest",
            # command=lambda: update_strategy(),
            state="disabled",
            pady=0,
        )
        button_backtest.grid(row=0, column=3)

        frame_title.grid_columnconfigure(0, weight=1)

        self.strategy_scroll = AutoScrollbar(frame_strategy, orient="vertical")
        self.strategy_text = tk.Text(
            frame_strategy,
            highlightthickness=0,
            # highlightbackground=disp.title_color,
            # highlightcolor=disp.title_color,
            bg=disp.bg_color,
            yscrollcommand=self.strategy_scroll.set,
        )
        self.strategy_text.bind("<KeyRelease>", self.on_modify_strategy)
        self.strategy_scroll.config(command=self.strategy_text.yview)
        self.strategy_text.grid(row=1, column=0, sticky="NSEW")
        self.strategy_scroll.grid(row=1, column=1, sticky="NS")

        frame_strategy.grid_columnconfigure(0, weight=1)
        frame_strategy.grid_columnconfigure(1, weight=0)
        frame_strategy.grid_rowconfigure(1, weight=1)

    def on_modify_strategy(self, event):
        value = self.strategy_text.get("1.0", tk.END)
        if value != self.bot_algo:
            """self.strategy_text.config(
                highlightbackground=disp.bg_changed,
                highlightcolor=disp.bg_changed,
            )"""
            self.button_strategy.config(state="normal")
        else:
            """self.strategy_text.config(
                highlightbackground=disp.title_color,
                highlightcolor=disp.title_color,
            )"""
            self.button_strategy.config(state="disabled")

    def finish_operation(self, message):
        winfo_destroy()
        tk.Label(
            self.brief_frame,
            text=message,
            bg=disp.bg_color,
            fg=disp.gray_color,
            justify=tk.LEFT,
        ).pack(anchor="nw", padx=self.padx, pady=self.pady)
        self.wrap("None")

    def activate(self, bot_name: str) -> str:
        def return_text() -> str:
            nonlocal new_state
            if bot.state == "Active":
                new_state = "Suspended"
            else:
                new_state = "Active"
            TEXT = "You are about to change state from ``{STATE}`` to ``{CHANGE}`` for bot ``{NAME}``:"
            return TEXT.format(STATE=bot.state, CHANGE=new_state, NAME=bot_name)

        def change_state(bot_name) -> None:
            nonlocal new_state
            err = service.update_database(
                query=f"UPDATE robots SET STATE = '{new_state}' WHERE EMI = '{bot_name}'"
            )
            if err is None:
                bot.state = new_state
                values = [bot_name, bot.timefr, bot.state, bot.created, bot.updated]
                TreeTable.bot_info.update(row=0, values=values)
                text_label["text"] = return_text()
                res_label["text"] = f"State changed to ``{bot.state}``."
                self.button.config(text=button_text[Bots[bot_name].state])

        self.switch(option="option")
        if not Bots[bot_name].error_message:
            print("activate")
            new_state = ""
            bot = Bots[bot_name]
            text_label = tk.Label(
                self.brief_frame,
                text=return_text(),
                bg=disp.bg_color,
                justify=tk.LEFT,
            )
            text_label.pack(anchor="nw", padx=self.padx, pady=self.pady)
            button_text = {"Active": "Suspend", "Suspended": "Activate"}
            self.button = tk.Button(
                self.brief_frame,
                activebackground=disp.bg_active,
                text=button_text[Bots[bot_name].state],
                command=lambda: change_state(bot_name),
            )
            self.button.pack(anchor="nw", padx=50, pady=10)
            res_label = tk.Label(
                self.brief_frame,
                text="",
                bg=disp.bg_color,
                fg=disp.gray_color,
                justify=tk.LEFT,
            )
            res_label.pack(anchor="nw", padx=self.padx, pady=self.pady)
        else:
            self.display_error_message(bot_name=bot_name)

    def parameters(self, bot_name: str) -> None:
        def on_button(value: int) -> None:
            timefr = tuple(self.timeframes.values())[value]
            err = service.update_database(
                query=f"UPDATE robots SET TIMEFR = {timefr}"
                + f", UPDATED = CURRENT_TIMESTAMP WHERE EMI = '{bot_name}'"
            )
            if err is None:
                bot.timefr = timefr
                bot.updated = self.get_time()
                # self.timeframe_changed = None
                values = [bot_name, bot.timefr, bot.state, bot.updated, bot.created]
                TreeTable.bot_info.update(row=0, values=values)
                res_label[
                    "text"
                ] = f"Timeframe value changed to {tuple(self.timeframes.keys())[value]}."

        self.switch(option="option")
        if not Bots[bot_name].error_message:
            bot = Bots[bot_name]
            tk.Label(
                self.brief_frame,
                text=f"Select new timeframe for bot ``{bot_name}``:",
                bg=disp.bg_color,
                justify=tk.LEFT,
            ).pack(anchor="nw", padx=self.padx, pady=self.pady)
            timeframe = ttk.Combobox(self.brief_frame, width=7, state="readonly")
            timeframe["values"] = tuple(self.timeframes.keys())
            timeframe.set(Bots[bot_name].timefr)
            timeframe.pack(anchor="nw", padx=50, pady=0)
            self.button = tk.Button(
                self.brief_frame,
                activebackground=disp.bg_active,
                text="Update",
                command=lambda: on_button(timeframe.current()),
            )
            self.button.pack(anchor="nw", padx=50, pady=10)
            res_label = tk.Label(
                self.brief_frame,
                text="",
                bg=disp.bg_color,
                fg=disp.gray_color,
                justify=tk.LEFT,
            )
            res_label.pack(anchor="nw", padx=self.padx, pady=self.pady)
        else:
            self.display_error_message(bot_name=bot_name)

    def merge(self, bot_name: str) -> None:
        def bot_list() -> list:
            bots = []
            for item in Bots.keys():
                if item != bot_name and Bots[item].state == "Suspended":
                    bots.append(item)
            if not bots:
                text = (
                    f"No available bots to be merged with. "
                    + f"Only bots with state ``Suspended`` allowed."
                )
                self.finish_operation(text)
            return bots

        def merge_bot(bot_name: str, bot_to_delete: str) -> None:
            query = f"UPDATE coins SET EMI = '{bot_name}' WHERE EMI = '{bot_to_delete}'"
            message = self.delete_all_bot_info(bot_to_delete, query, "Merge")
            if message[0] is None:
                message[1] = "The merge operation completed successfully."
            else:
                if message[1] == "":
                    message[1] = f"{message[0]}\n\nThe merge operation failed."
                else:
                    message[
                        1
                    ] += f"\n{message[0]}\n\nThe merge operation completed with errors."
            self.finish_operation(message[1])

        self.switch(option="option")

        if not Bots[bot_name].error_message:
            bots = bot_list()
            if bots:
                content = (
                    f"To merge bot named ``{bot_name}`` "
                    + f"please select one of the bots below available to be "
                    + f"merged with:"
                )
                label_first = tk.Label(
                    self.brief_frame,
                    text=content,
                    bg=disp.bg_color,
                    justify=tk.LEFT,
                )
                label_first.pack(anchor="nw", padx=self.padx, pady=self.pady)
                cbox = ttk.Combobox(
                    self.brief_frame, width=15, textvariable="", state="readonly"
                )
                cbox["values"] = tuple(bots)
                cbox.current(0)
                cbox.pack(anchor="nw", padx=50, pady=0)
                label_second = tk.Label(
                    self.brief_frame,
                    text=(
                        f"As a result of merge operation the selected bot will be "
                        + f"deleted. All its records in the database will move on "
                        + f"to bot ``{bot_name}``."
                    ),
                    bg=disp.bg_color,
                    justify=tk.LEFT,
                )
                label_second.pack(anchor="nw", padx=self.padx, pady=self.pady)
                self.check_var.set(0)
                confirm = tk.Checkbutton(
                    self.brief_frame,
                    text="Confirm operation",
                    variable=self.check_var,
                    bg=disp.bg_color,
                    justify=tk.LEFT,
                    highlightthickness=0,
                    command=self.check_button,
                )
                confirm.pack(anchor="nw")
                self.button = tk.Button(
                    self.brief_frame,
                    activebackground=disp.bg_active,
                    text="Merge Bot",
                    command=lambda: merge_bot(bot_name, cbox["values"][cbox.current()]),
                    state="disabled",
                )
                self.button.pack(anchor="nw", padx=50, pady=10)
        else:
            self.display_error_message(bot_name=bot_name)

    def dublicate(self, bot_name: str):
        def add_copy_bot(bot_name: str) -> None:
            copy_bot = self.name_trace.get()
            message = ""
            try:
                shutil.copytree(
                    self.get_bot_path(bot_name), self.get_bot_path(copy_bot)
                )
                message = f"The ``/{copy_bot}/`` subdirectory created."
                time_now = self.get_time()
                bot = Bots[copy_bot]
                bot.state = "Suspended"
                bot.timefr = Bots[bot_name].timefr
                bot.created = time_now
                bot.updated = time_now
                self.insert_bot_menu(name=copy_bot, new=True)
                message += f"\nNew bot ``{copy_bot}`` added to the bots' list."
                err = service.insert_database(
                    values=[copy_bot, "Suspended", Bots[bot_name].timefr],
                    table="robots",
                )
                if err is None:
                    message += f"\nBot named ``{copy_bot}`` inserted into database."
                else:
                    message += (
                        f"\n{err}\n\nThe duplicate operation completed with errors."
                    )
                    Bots[copy_bot].error_message = err
            except Exception as e:
                err = str(e)
                if message == "":
                    message = f"{err}\n\nThe duplicate operation failed."
                else:
                    message += (
                        f"\n{err}\n\nThe duplicate operation completed with errors."
                    )
            if err is None:
                message = "The duplicate operation completed successfully"
            self.finish_operation(message)

        self.switch(option="option")
        if not Bots[bot_name].error_message:
            tk.Label(
                self.brief_frame,
                text=(
                    f"You are about to duplicate ``{bot_name}``. The newly "
                    + f"created bot will get the same set of parameters as "
                    + f"``{bot_name}`` currently has."
                ),
                bg=disp.bg_color,
                justify=tk.LEFT,
            ).pack(anchor="nw", padx=self.padx, pady=self.pady)
            tk.Label(
                self.brief_frame,
                text="Enter a unique name",
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
            self.button = tk.Button(
                self.brief_frame,
                activebackground=disp.bg_active,
                text="Duplicate Bot",
                command=lambda: add_copy_bot(bot_name),
                state="disabled",
            )
            self.bot_entry["Name"].delete(0, tk.END)
            self.bot_entry["Name"].insert(0, bot_name)
            self.button.pack(anchor="nw", padx=50, pady=20)
            self.wrap("None")
        else:
            self.display_error_message(bot_name=bot_name)

    def delete(self, bot_name: str):
        def delete_bot(bot_name: str) -> None:
            query = f"UPDATE coins SET EMI = SYMBOL WHERE EMI = '{bot_name}'"
            message = self.delete_all_bot_info(bot_name, query, "Delete")
            if message[0] is None:
                message[1] = "The delete operation completed successfully."
                values = ["" for _ in var.name_bot]
                TreeTable.bot_info.update(row=0, values=values)
            else:
                if message[1] == "":
                    message[1] = f"{message[0]}\n\nThe delete operation failed."
                else:
                    message[
                        1
                    ] += (
                        f"\n{message[0]}\n\nThe delete operation completed with errors."
                    )
                    values = ["" for _ in var.name_bot]
                    TreeTable.bot_info.update(row=0, values=values)
            self.finish_operation(message[1])

        self.switch(option="option")

        tk.Label(
            self.brief_frame,
            text=(
                f"After you press the ``Delete bot`` button, the "
                + f"``/{bot_name}/`` subdirectory will be "
                + f"erased and this bot will no longer exist. Each database "
                + f"record belonging to the ``{bot_name}`` will change its ``EMI`` "
                + f"field value to the default one taken from the field ``SYMBOL``."
            ),
            bg=disp.bg_color,
            justify=tk.LEFT,
        ).pack(anchor="nw", padx=self.padx, pady=self.pady)
        self.check_var.set(0)
        confirm = tk.Checkbutton(
            self.brief_frame,
            text="Confirm operation",
            variable=self.check_var,
            bg=disp.bg_color,
            justify=tk.LEFT,
            highlightthickness=0,
            command=self.check_button,
        )
        confirm.pack(anchor="nw")
        self.button = tk.Button(
            self.brief_frame,
            activebackground=disp.bg_active,
            text="Delete bot",
            command=lambda: delete_bot(bot_name),
            state="disabled",
        )
        self.button.pack(anchor="nw", padx=50, pady=10)
        self.wrap("None")

    def new(self):
        if disp.bot_name:
            TreeTable.bot_menu.tree.item(disp.bot_name, open=False)

        def add(bot_name: str, timeframe: str) -> None:
            res = self.create_bot(bot_name=bot_name, timeframe=timeframe)
            if res:
                TreeTable.bot_menu.set_selection(index=bot_name)
                self.show(bot_name)

        self.switch(option="option")
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
        tk.Label(
            self.brief_frame,
            text="Select timeframe:",
            bg=disp.bg_color,
            justify=tk.LEFT,
        ).pack(anchor="nw", padx=self.padx, pady=self.pady)
        timeframe = ttk.Combobox(self.brief_frame, width=7, state="readonly")
        timeframe["values"] = tuple(self.timeframes.keys())
        timeframe.current(1)
        timeframe.pack(anchor="nw", padx=50, pady=0)
        self.button = tk.Button(
            self.brief_frame,
            activebackground=disp.bg_active,
            text="Create Bot",
            command=lambda: add(
                self.name_trace.get(), timeframe["values"][timeframe.current()]
            ),
            state="disabled",
        )
        self.bot_entry["Name"].delete(0, tk.END)
        self.button.pack(anchor="nw", padx=50, pady=20)
        res_label = tk.Label(
            self.brief_frame,
            text=self.new_bot_text,
            bg=disp.bg_color,
            fg=disp.gray_color,
            justify=tk.LEFT,
        )
        res_label.pack(anchor="nw", padx=self.padx, pady=self.pady)
        self.wrap("None")

    def show(self, bot_name):
        if bot_name != disp.bot_event_prev:
            TreeTable.bot_menu.on_rollup(iid=bot_name)
        disp.bot_name = bot_name
        disp.refresh_bot_info = True
        bot = Bots[bot_name]
        values = [bot_name, bot.timefr, bot.state, bot.updated, bot.created]
        TreeTable.bot_info.update(row=0, values=values)
        if not bot.error_message:
            if bot_name != disp.bot_event_prev:
                try:
                    bot_path = self.get_bot_path(bot_name=bot_name)
                    self.bot_algo = self.read_file(f"{bot_path}/{self.strategy_file}")
                    self.insert_code(
                        text_widget=self.strategy_text,
                        code=self.bot_algo,
                        bot_name=bot_name,
                    )
                    if disp.bot_name and bot_name != disp.bot_name:
                        bot_trades_sub[disp.bot_name].pack_forget()
                    init_bot_trades(bot_name=bot_name)
                    bot_trades_sub[bot_name].pack(fill="both", expand="yes")
                    refresh_bot_orders()
                    self.switch(option="table")
                    if bot.state == "Active":
                        self.strategy_text.config(state="disabled")
                    else:
                        self.strategy_text.config(state="normal")
                    disp.bot_event_prev = bot_name
                except Exception as e:
                    Bots[bot_name].error_message = str(e)
        if Bots[bot_name].error_message:
            self.display_error_message(bot_name=bot_name)
        else:
            try:
                self.button.config(state="disabled")
            except Exception:
                pass

    def wrap(self, event):
        for child in self.brief_frame.winfo_children():
            if type(child) is tk.Label:
                child.config(wraplength=self.brief_frame.winfo_width() - self.padx * 2)

    def switch(self, option: str) -> None:
        if option == "table":
            info_left.pack_forget()
            info_right.pack_forget()
            disp.pw_bot_info.pack(fill="both", expand="yes")
        else:
            disp.pw_bot_info.pack_forget()
            info_left.pack(fill="both", side="left")
            info_right.pack(fill="both", expand=True, side="left")

    def delete_all_bot_info(self, bot_name, query_0, type) -> Union[bool, None]:
        message = ""
        err = None
        try:
            Bots.remove(bot_name)
            TreeTable.bot_menu.delete(iid=bot_name)
            bot_trades_sub[bot_name].destroy()
            del trade_treeTable[bot_name]
            if type == "Delete":
                disp.bot_name = None
            message = f"Bot ``{bot_name}`` removed from Tmatic's memory."
            err = service.update_database(query=query_0)
            if err is None:
                message += "\nDatabase table ``coins`` updated."
                err = service.update_database(
                    query=f"DELETE FROM robots WHERE EMI = '{bot_name}'"
                )
                if err is None:
                    message += f"\nBot ``{bot_name}`` deleted from the database."
            bot_path = self.get_bot_path(bot_name)
            shutil.rmtree(str(bot_path))
            message += f"\nThe ``/{bot_name}/`` subdirectory erased."
            TreeTable.bots.delete(iid=bot_name)
            disp.bot_event_prev = ""
        except Exception as e:
            if err is None:
                err = str(e)
            else:
                err += f"\n{str(e)}"
        return [err, message]

    def display_error_message(self, bot_name: str) -> None:
        self.switch(option="option")
        self.finish_operation(Bots[bot_name].error_message)


def init_bot_trades(bot_name: str) -> None:
    if bot_name not in trade_treeTable:
        bot_trades_sub[bot_name] = tk.Frame(disp.bot_trades)
        trade_treeTable[bot_name] = TreeviewTable(
            frame=bot_trades_sub[bot_name],
            name="bot trades",
            size=0,
            title=var.name_bot_trade,
        )
        sql = (
            "select ID, EMI, SYMBOL, TICKER, CATEGORY, MARKET, SIDE, ABS(QTY) "
            + "as QTY, TRADE_PRICE, TTIME from coins where EMI == '"
            + bot_name
            + "' and SIDE <> 'Fund' order by TTIME limit "
            + str(disp.table_limit)
        )
        data = service.select_database(sql)
        indx_side = trade_treeTable[bot_name].title.index("SIDE")
        indx_market = trade_treeTable[bot_name].title.index("MARKET")
        for val in data:
            val["SYMBOL"] = (val["SYMBOL"], val["MARKET"])
            # Displays trades only if you have a subscription to this market in the .env file
            if val["MARKET"] in var.market_list:
                row = functions.Function.trades_display(
                    Markets[val["MARKET"]],
                    val=val,
                    table=trade_treeTable[bot_name],
                    init=True,
                )
                trade_treeTable[bot_name].insert(
                    values=row,
                    market=row[indx_market],
                    configure=row[indx_side],
                )


def refresh_bot_orders():
    tree = TreeTable.orders
    bot_tree = TreeTable.bot_orders
    indx_side = bot_tree.title.index("SIDE")
    bot_tree.clear_all()
    for child in tree.children:
        if child.split(".")[1] == disp.bot_name:
            row = tree.tree.item(child)["values"]
            bot_tree.insert(values=row, iid=child, configure=row[indx_side])


def winfo_destroy() -> None:
    for child in bot_manager.brief_frame.winfo_children():
        child.destroy()


def handler_bot_menu(event) -> None:
    tree = event.widget
    selection = tree.selection()
    if selection:
        iid = tree.selection()[0]
        option = iid.split("!")
        parent = option[0]
        if len(option) == 1:
            option = ""
        else:
            option = option[1]
        if parent == "Back":
            disp.menu_robots.pack_forget()
            disp.pw_rest1.pack(fill="both", expand="yes")
            disp.refresh_bot_info = False
            TreeTable.bot_menu.tree.selection_set(disp.bot_event_prev)
        elif parent == "New_bot":
            winfo_destroy()
            disp.refresh_bot_info = False
            bot_manager.new()
        elif not option:
            bot_manager.show(parent)
        else:
            winfo_destroy()
            disp.refresh_bot_info = False
            bot_manager.bot_options[option](bot_name=parent)
        if parent != "Back":
            disp.bot_event_prev = iid

trade_treeTable = dict()
bot_trades_sub = dict()
frame_strategy = tk.Frame(disp.pw_bot_info)
frame_strategy.pack(fill="both", expand="yes")
menu_frame = tk.Frame(disp.pw_menu_robots)
info_left = tk.Frame(disp.frame_bot_info, bg="#999999")
info_right = tk.Frame(disp.frame_bot_info, bg="#999999")
info_left.pack(fill="both", side="left")
info_right.pack(fill="both", expand=True, side="left")
disp.pw_bot_info.add(disp.bot_note)
disp.pw_bot_info.add(frame_strategy)
disp.pw_ratios[disp.pw_bot_info] = 3
disp.pw_bot_info.bind(
    "<Configure>",
    lambda event: disp.resize_height(event, disp.pw_bot_info, disp.pw_ratios[disp.pw_bot_info]),
)
disp.pw_bot_info.bind(
    "<ButtonRelease-1>", lambda event: disp.on_sash_move(event, disp.pw_bot_info)
)
disp.pw_menu_robots.add(menu_frame)
disp.pw_menu_robots.add(disp.info_frame)
disp.pw_menu_robots.bind(
    "<Configure>",
    lambda event: disp.resize_width(event, disp.pw_menu_robots, disp.window_width // 7, 6),
)
bot_manager = SettingsApp(menu_frame)
