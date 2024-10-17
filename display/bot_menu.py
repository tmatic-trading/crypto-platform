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
import importlib
import os
import re
import shutil
import sys
import tkinter as tk
import traceback
from collections import OrderedDict
from datetime import datetime, timezone
from tkinter import StringVar, font, ttk
from typing import Union

from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name

import functions
import services as service
from api.api import Markets
from botinit.variables import Variables as robo
from common.data import BotData, Bots
from common.variables import Variables as var
from display.messages import ErrorMessage

from .headers import Header
from .variables import AutoScrollbar, ScrollFrame, TreeTable, TreeviewTable
from .variables import Variables as disp


class BoldLabel(tk.Label):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        bold_font = font.Font(self, self.cget("font"))
        bold_font.configure(weight="bold")
        self.configure(font=bold_font)


class SettingsApp:
    def __init__(self):
        self.button_strategy = None
        self.algo_dir = f"{os.getcwd()}/algo/"
        self.strategy_file = "strategy.py"
        self.timeframes = var.timeframe_human_format
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
        self.padx = 0
        self.pady = 5
        with open("display/new_bot_text.txt", "r") as f:
            self.new_bot_text = f.read()
        with open("display/instructions.py", "r") as f:
            self.example_strategy = f.read()

        self.info_value = {}

        # Keeps the selected bot's algorithm derived from strategy.py file
        self.bot_algo = ""

        # Create initial frames

        self.brief_frame = ScrollFrame(info_right, bg=disp.bg_color, bd=5)
        self.modules = dict()
        self.create_strategy_widget()

    def onFrameConfigure(self, event):
        """
        Reset the scroll region to encompass the inner frame
        """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        service.wrap(self.brief_frame, padx=self.padx)

    def name_trace_callback(self, item, index, mode):
        name = item.replace(str(self), "")
        bot_name = re.sub("[\W]+", "", self.name_trace.get())
        if (
            bot_name in Bots.keys()
            # or bot_name != self.name_trace.get()
            or bot_name == ""
        ):
            self.bot_entry[name].config(style="used.TEntry")
            self.button.config(state="disabled")
        else:
            self.bot_entry[name].config(style="free.TEntry")
            self.button.config(state="normal")
        cursor = self.bot_entry[name].index(tk.INSERT)
        self.bot_entry[name].delete(0, tk.END)
        self.bot_entry[name].insert(0, bot_name)
        self.bot_entry[name].icursor(cursor)

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

    def init_bot(self, bot_name: str, timeframe: str) -> None:
        """
        Initializes bot variables when a new bot is created.
        """
        time_now = self.get_time()
        var.orders[bot_name] = OrderedDict()
        Bots[bot_name].name = bot_name
        Bots[bot_name].state = "Suspended"
        Bots[bot_name].timefr = timeframe
        Bots[bot_name].timefr_sec = service.timeframe_seconds(timeframe)
        Bots[bot_name].timefr_current = timeframe
        Bots[bot_name].created = time_now
        Bots[bot_name].updated = time_now
        Bots[bot_name].bot_positions = dict()
        Bots[bot_name].bot_orders = var.orders[bot_name]
        import_bot_module(bot_name)
        functions.activate_bot_thread(bot_name=bot_name)
        self.insert_bot_menu(name=bot_name, new=True)
        Bots[bot_name].log = list()

    def create_bot(self, bot_name, timeframe) -> bool:
        """
        Creates and initializes a new bot.
        """
        err = service.insert_database(
            values=[bot_name, "Suspended", timeframe], table="robots"
        )
        if err is None:
            bot_path = self.get_bot_path(bot_name)
            # Create a new directory with the name as the new bot's name
            os.mkdir(bot_path)
            # Create the '__init__.py' file in the new directory. This file is empty
            self.create_file(f"{str(bot_path)}/__init__.py")
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
                f"*\n!__init__.py\n!.gitignore\n!{self.strategy_file}\n",
            )
            self.init_bot(bot_name=bot_name, timeframe=timeframe)

            return True

    def insert_code(self, text_widget: tk.Text, code: str) -> None:
        """
        Function to insert Python code into a Tkinter Text widget with syntax
        highlighting.

        Parameters
        ----------
        text_widget: tk.Text
            Widget that contains the bot strategy code.
        code: str
            Code to insert into widget.
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

    def insert_bot_menu(self, name: str, new=False) -> None:
        tree = TreeTable.bot_menu
        if new:
            if "New_bot!" in tree.children:
                indx = tree.children.index("New_bot!")
        else:
            indx = "end"
        tree.insert_hierarchical(
            parent="", iid=name, text=name, configure="Gray", indx=indx
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
        for name in Bots.keys():
            self.insert_bot_menu(name)
        tree.insert_hierarchical(parent="", iid="New_bot!", text="Add new bot")
        tree.insert_hierarchical(parent="", iid="Back!", text="Back")

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
            )
            import_bot_module(disp.bot_name, update=True)
            qwr = (
                "UPDATE robots SET"
                + f" UPDATED = CURRENT_TIMESTAMP WHERE EMI = '{disp.bot_name}'"
            )
            err = service.update_database(query=qwr)
            if err is None:
                bot = Bots[disp.bot_name]
                bot.updated = self.get_time()
                update_bot_info(bot_name=disp.bot_name)

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
                )
            else:
                functions.warning_window(error_message, width=1000, height=300)

        frame_title = tk.Frame(disp.frame_strategy)
        frame_title.grid(row=0, column=0, sticky="NSEW", columnspan=2)
        blank = tk.Label(frame_title, text=" ")
        blank.grid(row=0, column=0, sticky="NSEW")
        title = BoldLabel(frame_title, text="STRATEGY")
        title.grid(row=0, column=1, sticky="NSEW")
        frame_title_sub = tk.Frame(frame_title)
        frame_title_sub.grid(row=0, column=2)
        self.button_strategy = tk.Button(
            frame_title_sub,
            activebackground=disp.bg_active,
            text="Update strategy",
            command=lambda: update_strategy(),
            state="disabled",
            pady=1,
        )
        self.button_strategy.pack(fill="both", side="left")
        button_syntax = tk.Button(
            frame_title_sub,
            activebackground=disp.bg_active,
            text="Check syntax",
            command=lambda: check_syntax(),
            pady=1,
        )
        button_syntax.pack(fill="both", side="left")

        button_backtest = tk.Button(
            frame_title_sub,
            activebackground=disp.bg_active,
            text="Backtest",
            # command=lambda: update_strategy(),
            state="disabled",
            pady=1,
        )
        button_backtest.pack(fill="both", side="left")
        frame_title.grid_columnconfigure(0, weight=1)
        frame_title.grid_columnconfigure(1, weight=2)
        frame_title.grid_columnconfigure(2, weight=2)

        self.strategy_scroll = AutoScrollbar(disp.frame_strategy, orient="vertical")
        self.strategy_text = tk.Text(
            disp.frame_strategy,
            highlightthickness=0,
            bg=disp.text_info["background"],
            yscrollcommand=self.strategy_scroll.set,
        )
        self.strategy_text.bind("<KeyRelease>", self.on_modify_strategy)
        self.strategy_scroll.config(command=self.strategy_text.yview)
        self.strategy_text.grid(row=1, column=0, sticky="NSEW")
        self.strategy_scroll.grid(row=1, column=1, sticky="NS")

        disp.frame_strategy.grid_columnconfigure(0, weight=1)
        disp.frame_strategy.grid_columnconfigure(1, weight=0)
        disp.frame_strategy.grid_rowconfigure(1, weight=1)

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
        service.wrap(self.brief_frame, padx=self.padx)

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
            err = update_bot_state(new_state=new_state, bot=bot)
            if err is None:
                text_label["text"] = return_text()
                res_label["text"] = f"State changed to ``{bot.state}``."
                self.button.config(text=button_text[Bots[bot_name].state])

        bot = Bots[bot_name]
        self.check_bot_file(bot_name=bot_name)
        self.switch(option="option")
        disp.bot_menu_option = "activate"
        if not bot.error_message or (bot.error_message and bot.state == "Active"):
            if bot.error_message:
                tk.Label(
                    self.brief_frame,
                    text=bot.error_message["message"],
                    bg=disp.bg_color,
                    fg=disp.gray_color,
                    justify=tk.LEFT,
                ).pack(anchor="nw", padx=self.padx, pady=self.pady)
            new_state = ""
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
                text=button_text[bot.state],
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
            service.wrap(self.brief_frame, padx=self.padx)
        else:
            self.display_error_message(bot_name=bot_name)

    def parameters(self, bot_name: str) -> None:
        def on_button(value: int) -> None:
            timefr = tuple(self.timeframes.keys())[value]
            qwr = (
                f"UPDATE robots SET TIMEFR = '{timefr}'"
                + f", UPDATED = CURRENT_TIMESTAMP WHERE EMI = '{bot_name}'"
            )
            err = service.update_database(query=qwr)
            if err is None:
                bot.timefr = timefr
                bot.updated = self.get_time()
                bot.timefr_sec = service.timeframe_seconds(timefr)
                update_bot_info(bot_name=bot_name)
                res_label["text"] = (
                    "Timeframe value changed to "
                    + timefr
                    + ". The changes will take effect when the current "
                    + bot.timefr_current
                    + " period ends."
                )
                import_bot_module(bot_name=bot_name, update=True)

        self.check_bot_file(bot_name=bot_name)
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
                    "No available bots to be merged with. "
                    + "Only bots with state ``Suspended`` allowed."
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

        self.check_bot_file(bot_name=bot_name)
        self.switch(option="option")
        if not Bots[bot_name].error_message:
            bots = bot_list()
            if bots:
                content = (
                    f"To merge bot named ``{bot_name}`` "
                    + "please select one of the bots below available to be "
                    + "merged with:"
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
                        "As a result of merge operation the selected bot will be "
                        + "deleted. All its records in the database will move on "
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
                self.init_bot(bot_name=copy_bot, timeframe=Bots[bot_name].timefr)
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
                    Bots[copy_bot].error_message = {
                        "error_type": "sqliteError",
                        "message": err,
                    }

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

        self.check_bot_file(bot_name=bot_name)
        self.switch(option="option")
        if not Bots[bot_name].error_message:
            tk.Label(
                self.brief_frame,
                text=(
                    f"You are about to duplicate ``{bot_name}``. The newly "
                    + "created bot will get the same set of parameters as "
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
            service.wrap(self.brief_frame, padx=self.padx)
        else:
            self.display_error_message(bot_name=bot_name)

    def delete(self, bot_name: str):
        def delete_bot(bot_name: str) -> None:
            if bot_name in var.orders:
                num = len(var.orders[bot_name])
                if num > 0:
                    if num > 1:
                        s = "s"
                    else:
                        s = ""
                    message = (
                        "The `" + bot_name + "` has " + str(num) + " open "
                        + "order" + s + ". Before deleting the bot, you "
                        + "need to cancel the orders."
                    )
                    functions.warning_window(message=message)
                    return
            query = f"UPDATE coins SET EMI = '' WHERE EMI = '{bot_name}'"
            message = self.delete_all_bot_info(bot_name, query, "Delete")
            if message[0] is None:
                message[1] = "The delete operation completed successfully."
                values = ["" for _ in Header.name_bot]
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
                    values = ["" for _ in Header.name_bot]
                    TreeTable.bot_info.update(row=0, values=values)
            self.finish_operation(message[1])

        self.switch(option="option")

        tk.Label(
            self.brief_frame,
            text=(
                "After you press the `Delete bot` button, the "
                + f"`/{bot_name}/` subdirectory will be "
                + "erased and this bot will no longer exist. Every database "
                + f"record belonging to the `{bot_name}` will change the "
                + "value of the `EMI` column to empty"
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
        service.wrap(self.brief_frame, padx=self.padx)

    def new(self):
        if disp.bot_name:
            TreeTable.bot_menu.tree.item(disp.bot_name, open=False)

        def add(bot_name: str, timeframe: str) -> None:
            res = self.create_bot(bot_name=bot_name, timeframe=timeframe)
            if res:
                TreeTable.bot_menu.set_selection(index=bot_name)
                self.show(bot_name)
                functions.update_order_form()

        self.switch(option="option")
        values = ["" for _ in Header.name_bot]
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
        res_label.pack(
            anchor="nw", padx=self.padx, pady=self.pady, fill="both", expand=True
        )
        service.wrap(self.brief_frame, padx=self.padx)

    def show(self, bot_name):
        if bot_name != disp.bot_event_prev:
            TreeTable.bot_menu.on_rollup(iid=bot_name)

        disp.refresh_bot_info = True
        bot = Bots[bot_name]
        self.check_bot_file(bot_name=bot_name)
        update_bot_info(bot_name=bot_name)
        condition = True
        if bot.error_message:
            if bot.error_message["error_type"] in [
                "ModuleNotFoundError",
                "FileNotFoundError",
            ]:
                condition = False
        if condition is True:
            if bot_name != disp.bot_event_prev:
                try:
                    self.insert_code(
                        text_widget=self.strategy_text,
                        code=self.bot_algo,
                    )
                    if disp.bot_name and bot_name != disp.bot_name:
                        bot_trades_sub[disp.bot_name].pack_forget()
                    disp.bot_name = bot_name
                    init_bot_trades(bot_name=bot_name)
                    bot_trades_sub[bot_name].pack(fill="both", expand="yes")
                    refresh_bot_orders()
                    self.switch(option="table")
                    disp.bot_event_prev = bot_name
                    fill_bot_log(bot_name=bot_name)
                except Exception as ex:
                    Bots[bot_name].error_message = {
                        "error_type": ex.__class__.__name__,
                        "message": {str(ex)},
                    }
            try:
                self.button.config(state="disabled")
            except Exception:
                pass
        else:
            self.display_error_message(bot_name=bot_name)

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
            if bot_name in TreeTable.bots.children:
                TreeTable.bots.delete(iid=bot_name)
            disp.bot_event_prev = ""
            var.bot_thread_active[bot_name] = False
            del robo.run[bot_name]
            del self.modules[bot_name]
            del var.orders[bot_name]
            functions.remove_bot_klines(bot_name)
            functions.update_order_form()
        except Exception as e:
            if err is None:
                err = str(e)
            else:
                err += f"\n{str(e)}"
        return [err, message]

    def display_error_message(self, bot_name: str) -> None:
        self.switch(option="option")
        self.finish_operation(Bots[bot_name].error_message["message"])

    def check_bot_file(self, bot_name: str) -> None:
        """
        Checks for the existence of the strategy.py file or the bot folder.

        Parameters
        ----------
        bot_name: str
            Bot name.
        """
        bot = Bots[bot_name]
        try:
            bot_path = self.get_bot_path(bot_name=bot_name)
            self.bot_algo = self.read_file(f"{bot_path}/{self.strategy_file}")
        except FileNotFoundError as ex:
            bot.error_message = {
                "error_type": ex.__class__.__name__,
                "message": {str(ex)},
            }
        else:
            if bot.error_message:
                if bot.error_message["error_type"] in [
                    "ModuleNotFoundError",
                    "FileNotFoundError",
                ]:
                    bot.error_message = {}


def update_bot_state(new_state: str, bot: BotData) -> Union[str, None]:
    """
    Updates the database entry when the bot's state changes.

    Parameters
    ----------
    new_state: str
        New state to save to the database.
    bot: str
        Bot instance.

    Returns
    -------
    str | None
        Description of the error, or None if successful.
    """
    err = service.update_database(
        query=f"UPDATE robots SET STATE = '{new_state}' WHERE EMI = '{bot.name}'"
    )
    if err is None:
        bot.state = new_state
        update_bot_info(bot_name=bot.name)
        return

    return err


def handler_bot_info(event) -> None:
    """
    Called when the bot table TreeTable.bot_info is clicked.
    """

    def callback():
        if bot.state == "Active":
            new_state = "Suspended"
        else:
            new_state = "Active"
        err = update_bot_state(new_state=new_state, bot=bot)
        if err:
            functions.warning_window(message=err, width=1000, height=300)
        on_closing()

    def on_closing():
        disp.robots_window_trigger = "off"
        robot_window.destroy()

    def leave(event):
        on_closing()

    tree = event.widget
    selection = tree.selection()
    if selection:
        if not disp.bot_menu_option:
            bot_name = tree.item(selection[0])["values"][0]
            bot = Bots[bot_name]
            if bot.error_message:
                functions.warning_window(
                    bot.error_message["message"],
                    width=1000,
                    height=300,
                    title=f"{bot_name} error",
                )
            else:
                if disp.robots_window_trigger == "off":
                    disp.robots_window_trigger = "on"
                    width = max(250, int(len(bot_name) * disp.symbol_width * 1.5) + 150)
                    robot_window = tk.Toplevel(
                        disp.root, padx=10, pady=10, bg=disp.title_color
                    )
                    cx = disp.root.winfo_pointerx()
                    cy = disp.root.winfo_pointery()
                    robot_window.geometry(
                        "{}x{}+{}+{}".format(width, 70, cx - 100, cy + 20)
                    )
                    robot_window.title(bot_name)
                    robot_window.protocol("WM_DELETE_WINDOW", on_closing)
                    robot_window.bind("<FocusOut>", leave)
                    robot_window.focus()
                    text = "Suspend"
                    if bot.state == "Suspended":
                        text = "Activate"
                    status = tk.Button(robot_window, text=text, command=callback)
                    status.pack()


def update_bot_info(bot_name: str) -> None:
    """
    Updates TreeTable.bot_info.
    """
    bot = Bots[bot_name]
    values = [
        bot_name,
        bot.timefr,
        bot.state,
        service.bot_error(bot=bot),
        bot.updated,
        bot.created,
    ]
    TreeTable.bot_info.update(row=0, values=values)


def init_bot_trades(bot_name: str) -> None:
    """
    Creates a new instance of the TreeviewTable class for the specified bot
    in a custom frame. All instances are stored in the trade_treeTable
    dictionary, which is placed in the specified frame in the bot_trades_sub
    dictionary. When bots are switched, the frames are also switched.
    Finally, the specific frame is placed in the bot_note ttk notebook.

    Parameters
    ----------
    bot_name: str
        Name of the bot.
    """
    if bot_name not in trade_treeTable:
        if bot_name not in bot_trades_sub:
            bot_trades_sub[bot_name] = tk.Frame(disp.bot_trades)
            trade_treeTable[bot_name] = TreeviewTable(
                frame=bot_trades_sub[bot_name],
                name="bot trades",
                size=0,
                title=Header.name_bot_trade,
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
        line = False
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
                line = True
        if not line:
            trade_treeTable[bot_name].insert(values=["No trades"], iid="notification")


def refresh_bot_orders():
    """
    The bot's order table is updated when you enter the bot page.
    """
    tree = TreeTable.orders
    bot_tree = TreeTable.bot_orders
    indx_side = bot_tree.title.index("SIDE")
    bot_tree.clear_all()
    anyline = False
    for child in tree.children:
        if child.split(".")[1] == disp.bot_name:
            row = tree.tree.item(child)["values"]
            bot_tree.insert(values=row, iid=child, configure=row[indx_side])
            anyline = True
    if anyline:
        if "No orders" in bot_tree.children:
            bot_tree.delete(iid="No orders")
    else:
        bot_tree.insert(values=["No orders"], iid="notification")


def winfo_destroy() -> None:
    for child in bot_manager.brief_frame.winfo_children():
        child.destroy()


def handler_bot_menu(event) -> None:
    tree = event.widget
    selection = tree.selection()
    if selection:
        disp.bot_menu_option = ""
        iid = tree.selection()[0]
        option = iid.split("!")
        parent = option[0]
        if len(option) == 1:
            option = ""
        else:
            option = option[1]
        disp.refresh_bot_info = False
        if parent == "Back":
            disp.menu_robots.pack_forget()
            disp.pw_rest1.pack(fill="both", expand="yes")
            TreeTable.bot_menu.tree.selection_set(disp.bot_event_prev)
        elif parent == "New_bot":
            winfo_destroy()
            bot_manager.new()
        elif not option:
            bot_manager.show(parent)
        else:
            winfo_destroy()
            bot_manager.bot_options[option](bot_name=parent)
        if parent != "Back":
            disp.bot_event_prev = iid


def import_bot_module(bot_name: str, update=False) -> None:
    """
    This function is called when bots are initially loaded, or reloaded due
    to <F3>, or reloaded for some other reason, or when strategy.py is
    updated.

    Parameters
    ----------
    bot_name: str
        Bot name.
    update: bool
        Evaluates to True when strategy.py is updated.
    """
    module = "algo." + bot_name + "." + bot_manager.strategy_file.split(".")[0]
    Bots[bot_name].error_message = {}
    try:
        if module in sys.modules:
            del sys.modules[module]
        mod = importlib.import_module(module)
        bot_manager.modules[bot_name] = mod
    except ModuleNotFoundError as exception:
        message = ErrorMessage.BOT_FOLDER_NOT_FOUND.format(
            MODULE=module, EXCEPTION=exception, BOT_NAME=bot_name
        )
        var.logger.warning(message)
        var.queue_info.put(
            {
                "market": "",
                "message": message,
                "time": datetime.now(tz=timezone.utc),
                "warning": "warning",
                "emi": bot_name,
            }
        )
        Bots[bot_name].error_message = {
            "error_type": exception.__class__.__name__,
            "message": message,
        }
    except Exception as exception:
        # service.display_exception(exception=exception)
        message = ErrorMessage.BOT_LOADING_ERROR.format(
            MODULE=module, EXCEPTION=exception, BOT_NAME=bot_name
        )
        var.logger.warning(message)
        var.queue_info.put(
            {
                "market": "",
                "message": message,
                "time": datetime.now(tz=timezone.utc),
                "warning": "warning",
                "emi": bot_name,
            }
        )
        Bots[bot_name].error_message = {
            "error_type": exception.__class__.__name__,
            "message": message,
        }
    else:
        if update:
            var.queue_info.put(
                {
                    "market": "",
                    "message": bot_name + " updated successfully.",
                    "time": datetime.now(tz=timezone.utc),
                    "warning": None,
                    "emi": bot_name,
                }
            )
    try:
        robo.run[bot_name] = bot_manager.modules[bot_name].strategy
    except Exception:
        robo.run[bot_name] = "No strategy"
    if update:
        functions.init_bot_klines(bot_name)


def insert_bot_log(
    bot_name: str,
    message: str,
    warning: Union[str, None],
    market: str = None,
    tm: datetime = None,
    fill=False,
) -> None:
    """
    Displays information about a specific bot and saves it to bot.log.

    Parameters
    ----------
    bot_name: str
        Bot name.
    message: str
        Information to display and save.
    tm: datetime
        Time the message was created.
    warning: str | None
        Warning or error messages are displayed in red.
    market: str
        Exchange name.
    fill: bool
        True, if only it refills text_bot_log widget when switching between
        bots.
    """
    if not fill:
        message = service.format_message(market=market, message=message, tm=tm)
        Bots[bot_name].log.append((warning, message))
        path = f"{bot_manager.algo_dir}{bot_name}/bot.log"
        with open(path, "a") as f:
            f.write(message)
    if bot_name == disp.bot_name:
        num = message.count("\n")
        disp.text_bot_log.insert("1.0", message)
        if warning == "error":
            color = disp.red_color
        elif warning == "warning":
            color = disp.warning_color
        if warning:
            disp.text_bot_log.tag_add(" ", "1.0", f"{num}.1000")
            disp.text_bot_log.tag_config(" ", foreground=color)
        if len(Bots[bot_name].log) > disp.text_line_limit:
            limit = f"{disp.text_line_limit + 1}.0"
            disp.text_bot_log.delete(limit, "end")


def fill_bot_log(bot_name: str) -> None:
    """
    Refills text_bot_log widget when switching between bots.
    """
    disp.text_bot_log.delete("1.0", tk.END)
    for message in Bots[bot_name].log[-disp.text_line_limit :]:
        insert_bot_log(
            bot_name=bot_name, message=message[1], warning=message[0], fill=True
        )


trade_treeTable = dict()
bot_trades_sub = dict()
menu_frame = tk.Frame(disp.pw_menu_robots)
info_left = tk.Frame(disp.frame_bot_info, bg="#999999")
info_right = tk.Frame(disp.frame_bot_info, bg="#999999")
info_left.pack(fill="both", side="left")
info_right.pack(fill="both", expand=True, side="left")
disp.pw_bot_info.add(disp.bot_note)
disp.pw_bot_info.add(disp.frame_strategy)
disp.pw_bot_info.bind(
    "<Configure>",
    lambda event: disp.resize_height(
        event, disp.pw_bot_info, disp.pw_ratios[disp.pw_bot_info]["ratio"]
    ),
)
disp.pw_bot_info.bind(
    "<ButtonRelease-1>", lambda event: disp.on_sash_move(event, disp.pw_bot_info)
)
disp.pw_menu_robots.add(menu_frame)
disp.pw_menu_robots.add(disp.info_frame)
disp.pw_menu_robots.bind(
    "<Configure>",
    lambda event: disp.resize_width(
        event, disp.pw_menu_robots, disp.window_width // 7, 6
    ),
)
bot_manager = SettingsApp()
