"""
1) Provide database transformations for the following operations:
- New: insert (robots)
- Activate: update STATUS (robots)
- Update: update TIMEFRAME, UPDATED (robots)
- Merge: delete record (robots), update EMI (coins)
- Duplicate: insert (robots)
- Delete: delete record (robots), update EMI (coins)
2) When bot is active, the following services must be disabled:
- Update (the respective fields, i.g. strategy, must be disabled)
- Merge
- Delete (no active orders allowed)
3) Merge operation is capable only with inactive bots. No active orders are allowed for the bot being deleted.
"""

import os
import re
import shutil
import time
import tkinter as tk

# from pygments.token import Token
import traceback
from tkinter import StringVar, font, ttk

from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name

from .variables import AutoScrollbar
from .variables import Variables as disp
from common.data import Bot
#from functions import Function

ttk.Style().configure("free.TEntry", foreground=disp.fg_color)
ttk.Style().configure("used.TEntry", foreground="red")


class CustomButton(tk.Menubutton):
    def __init__(self, master, app, button, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.name = button
        self.var = tk.IntVar()
        self.button = None
        self.bot_entry = {}
        self.name_trace = StringVar(name="Name" + str(self))
        self.bind("<ButtonPress-1>", self.on_press)

    def trace_callback(self, var, index, mode):
        name = var.replace(str(self), "")
        bot_name = re.sub("[\W]+", "", self.name_trace.get())
        if bot_name in Bot.keys() or bot_name != self.name_trace.get():
            self.bot_entry[name].config(style=f"used.TEntry")
            self.button.config(state="disabled")
        else:
            self.bot_entry[name].config(style=f"free.TEntry")
            self.button.config(state="normal")

    def open_popup(self, action, bot_name):
        if self.app.pop_up:
            self.app.pop_up.destroy()
        self.app.pop_up = tk.Toplevel()
        self.app.pop_up.geometry("750x350")

        if action == "New Bot":
            self.app.pop_up.title(action)
            content = f"\nCreate bot. Every new bot\nmust have a unique name."
            tk.Label(self.app.pop_up, text=content).pack(anchor="n", pady=25)
            tk.Label(self.app.pop_up, text="Enter a unique name").pack(anchor="n")
            self.bot_entry["Name"] = ttk.Entry(
                self.app.pop_up,
                width=20,
                style="free.TEntry",
                textvariable=self.name_trace,
            )
            self.bot_entry["Name"].pack(anchor="n")
            self.name_trace.trace_add("write", self.trace_callback)
            self.button = tk.Button(
                self.app.pop_up,
                activebackground=disp.bg_active,
                text="Create Bot",
                command=lambda: self.app.create_bot(self.name_trace.get()),
                state="disabled",
            )
            self.bot_entry["Name"].delete(0, tk.END)
            self.button.pack(anchor="n")
        elif action == "Syntax":
            self.app.pop_up.title(f"Check syntax for: {bot_name}")
            content = self.app.strategy_text.get("1.0", tk.END)
            is_syntax_correct, error_message = self.check_syntax(content)
            if is_syntax_correct:
                tk.Label(self.app.pop_up, text="The bot's code syntax is correct").pack(
                    anchor="n", pady=100
                )
                self.app.insert_code(
                    self.app.strategy_text, self.app.strategy_text.get("1.0", tk.END)
                )
            else:
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
                text.insert(tk.END, error_message)
                text.config(state="disabled")
        elif action == "Merge":
            self.app.pop_up.title(f"{action}: {bot_name}")
            content = f"\n\nTo merge bot named '{self.app.selected_bot}'\nplease select one of the bots below\navailable to be merged with:"
            tk.Label(self.app.pop_up, text=content).pack(anchor="n")
            cbox = ttk.Combobox(
                self.app.pop_up, width=15, textvariable="", state="readonly"
            )
            bots = []
            for option in Bot.keys():
                if option != self.app.selected_bot:
                    bots.append(option)
            cbox["values"] = tuple(bots)
            cbox.current(0)
            cbox.pack(anchor="n")
            tk.Label(
                self.app.pop_up,
                text=f"\nAs a result of merge operation\nthe selected bot will be deleted.\nAll its records in the database\nwill move on to bot '{self.app.selected_bot}'",
            ).pack(anchor="center")
            self.var.set(0)
            confirm = tk.Checkbutton(
                self.app.pop_up,
                text="Confirm operation",
                variable=self.var,
                command=self.check_button,
            )
            confirm.pack(anchor="n")
            self.button = tk.Button(
                self.app.pop_up,
                activebackground=disp.bg_active,
                text="Merge Bot",
                command=lambda: self.app.merge_bot(
                    bot_name, cbox["values"][cbox.current()]
                ),
                state="disabled",
            )
            self.button.pack(anchor="n")
        elif action == "Duplicate":
            self.app.pop_up.title(f"{action}: {bot_name}")
            content = f"\nYou are about to duplicate bot named '{self.app.selected_bot}'.\nThe newly created bot will get the same set\nof parameters as '{self.app.selected_bot}' currently has."
            tk.Label(self.app.pop_up, text=content).pack(anchor="n", pady=25)
            tk.Label(self.app.pop_up, text="Enter a unique name").pack(anchor="n")
            self.bot_entry["Name"] = ttk.Entry(
                self.app.pop_up,
                width=20,
                style="free.TEntry",
                textvariable=self.name_trace,
            )
            self.bot_entry["Name"].pack(anchor="n")
            self.name_trace.trace_add("write", self.trace_callback)
            self.button = tk.Button(
                self.app.pop_up,
                activebackground=disp.bg_active,
                text="Duplicate Bot",
                command=lambda: self.app.duplicate_bot(bot_name, self.name_trace.get()),
                state="disabled",
            )
            self.bot_entry["Name"].delete(0, tk.END)
            self.bot_entry["Name"].insert(0, bot_name)
            self.button.pack(anchor="n")
        elif action == "Delete":
            self.app.pop_up.title(f"Delete: {bot_name}")
            content = f"\n\nAfter you press the 'Delete Bot' button,\nthe '/algo/{self.app.selected_bot}/' subdirectory will be erased\nand this bot will no longer exist.\n\nThe 'EMI' fields in the database for this bot\nwill take the 'SYMBOL' fields values."
            tk.Label(self.app.pop_up, text=content).pack(anchor="n")
            self.var.set(0)
            confirm = tk.Checkbutton(
                self.app.pop_up,
                text="Confirm operation",
                variable=self.var,
                command=self.check_button,
            )
            confirm.pack(anchor="n")
            self.button = tk.Button(
                self.app.pop_up,
                activebackground=disp.bg_active,
                text="Delete Bot",
                command=lambda: self.app.delete_bot(bot_name),
                state="disabled",
            )
            self.button.pack(anchor="n")

    def check_button(self):
        if self.var.get() == 1:
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

    def on_press(self, event):
        if self["state"] != "disabled":
            if self.name == "Home":
                self.app.action = "Home"
                self.app.show_bot()
                # self.app.draw_buttons()
            elif self.name == "New Bot":
                self.open_popup(self.name, "")
            elif self.name == "Syntax":
                self.open_popup(self.name, self.app.selected_bot)
            elif self.name == "Update":
                self.app.write_file(
                    f"{self.app.get_bot_path(self.app.selected_bot)}/{self.app.strategy_file}",
                    self.app.strategy_text.get("1.0", tk.END),
                )
                self.app.algo_changed = None
                self.app.draw_buttons()
            elif self.name == "Merge":
                self.open_popup(self.name, self.app.selected_bot)
            elif self.name == "Duplicate":
                self.open_popup(self.name, self.app.selected_bot)
            elif self.name == "Delete":
                self.open_popup(self.name, self.app.selected_bot)
            elif self.name == "Last Viewed":
                self.app.action = self.name
                self.app.show_bot()
                # self.app.draw_buttons()
            elif self.name == "Back":
                disp.menu_robots.pack_forget()
                disp.pw_rest1.pack(fill="both", expand="yes")
            else:
                print(self.name, self["state"])

class SettingsApp:
    def __init__(self, root):
        self.root_frame = root
        self.button_height = 0

        self.pop_up = None
        self.selected_bot = ""
        self.algo_dir = f"{os.getcwd()}/algo/"
        self.strategy_file = "strategy.py"
        self.action = ""

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
            "Status",
        ]

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
            self.button_height = frame.winfo_reqheight()

        # Keeps all bots' names in the array
        #self.bots_list = []
        #self.collect_bots()

        # Keeps the selected bot's algorithm derived from strategy.py file
        self.bot_algo = ""

        # If bot's algorithm is changed by user, than the value in not None
        self.algo_changed = None

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
        y_pos = 0
        for i, button in enumerate(self.buttons_center):
            if button.name == "Home":
                if self.action != "Last Viewed":
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            elif button.name == "New Bot":
                button.configure(state="normal")
            elif button.name == "Syntax":
                if self.selected_bot == "" or self.action == "Home":
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            elif button.name == "Update":
                if (
                    self.selected_bot == ""
                    or self.action == "Home"
                    or self.algo_changed == None
                ):
                    button.configure(state="disabled", bg=disp.bg_select_color)
                else:
                    button.configure(state="normal", bg="gold")
            elif button.name == "Merge":
                if (
                    self.selected_bot == ""
                    or self.action == "Home"
                    or len(Bot.keys()) < 2
                ):
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            elif button.name == "Duplicate":
                if self.selected_bot == "" or self.action == "Home":
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            elif button.name == "Delete":
                if self.selected_bot == "" or self.action == "Home":
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            elif button.name == "Last Viewed":
                if self.selected_bot == "" or self.action == "Last Viewed":
                    button.configure(state="disabled")
                else:
                    button.configure(state="normal")
            elif button.name == "Back":
                button.configure(state="normal")
            else:
                button.configure(state="disabled")
            # button.update_idletasks()
            if i == 0:
                y_pos = int(self.button_height / 2.5)
            else:
                if button.name == "Last Viewed" or button.name == "Syntax":
                    y_pos += int(self.button_height / 2.5)
            button.place_configure(
                x=0, y=y_pos, height=self.button_height, relwidth=1.0
            )
            y_pos += int(self.button_height * 1.333)

    def show_bot(self):
        """Shows the bot's info when bot is selected. Otherwise hides"""
        if self.selected_bot != "" and self.action != "Home":
            self.menu_usage.pack_forget()
            self.bots_button.pack_forget()
            self.bots_label.pack_forget()
            self.brief_frame.pack_forget()
            self.main_frame.pack(fill="both", expand="yes")
            bot_path = self.get_bot_path(self.selected_bot)
            for item in self.rows_list:
                if item == "Name":
                    self.info_value[item].config(text=self.selected_bot)
                    self.bot_algo = self.read_file(f"{bot_path}/{self.strategy_file}")
                    self.insert_code(self.strategy_text, self.bot_algo)
                elif item == "Created":
                    my_time = time.ctime(
                        os.path.getctime(f"{bot_path}/{self.strategy_file}")
                    )
                    t_stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(my_time))
                    self.info_value[item].config(text=t_stamp)
                elif item == "Updated":
                    my_time = time.ctime(
                        os.path.getmtime(f"{bot_path}/{self.strategy_file}")
                    )
                    t_stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(my_time))
                    self.info_value[item].config(text=t_stamp)
                elif item == "Status":
                    self.info_value[item].config(text="Suspended")
        else:
            self.main_frame.pack_forget()
            self.brief_frame.pack(fill="both", expand="yes")
            if len(Bot.keys()) != 0:
                self.bots_label.pack(anchor="n")
                self.bots_button.pack(anchor="n")
                self.menu_usage.pack(anchor="n", pady=50)
            else:
                self.menu_usage.pack(anchor="n", pady=50)
        self.algo_changed = None
        self.draw_buttons()

    def create_file(self, file_name):
        os.mknod(file_name)

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

    def create_bot(self, bot_name):
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
        Bot[bot_name].status = "Suspended"
        #Function.insert_database(self, values=[bot_name, Bot[bot_name].status], table="robots")
        self.after_popup(bot_name)

    def merge_bot(self, bot_name, bot_to_delete):
        bot_path = self.get_bot_path(bot_to_delete)
        shutil.rmtree(str(bot_path))
        Bot.remove(bot_to_delete)
        self.after_popup(bot_name)

    def delete_bot(self, bot_name):
        bot_path = self.get_bot_path(bot_name)
        shutil.rmtree(str(bot_path))
        Bot.remove(bot_name)
        self.after_popup("")

    def duplicate_bot(self, bot_name, copy_bot):
        shutil.copytree(self.get_bot_path(bot_name), self.get_bot_path(copy_bot))
        Bot[bot_name].status = "Suspended"
        #Function.insert_database(self, values=[bot_name, Bot[bot_name].status], table="robots")
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

    def insert_code(self, text_widget, code):
        """Function to insert Python code into a Tkinter Text widget with syntax highlighting"""
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

    def on_menu_select(self, value):
        self.selected_bot = value
        self.action = "Last Viewed"
        self.show_bot()

    def create_bots_menu(self):
        # Menu to choose one of the created bots
        self.bots_button = tk.Menubutton(
            self.brief_frame,
            text=" LIST OF CREATED BOTS ",
            relief=tk.GROOVE,
            padx=0,
            pady=0,
            activebackground=disp.bg_active,
        )
        main_menu = tk.Menu(self.bots_button, tearoff=0)
        self.bots_button.config(menu=main_menu)
        for option in Bot.keys():
            main_menu.add_command(
                label=option,
                command=lambda value=option: self.on_menu_select(value),
            )

    def on_modify_strategy(self, event):
        value = self.strategy_text.get("1.0", tk.END)
        if value != self.bot_algo:
            if self.algo_changed == None:
                self.algo_changed = "changed"
                self.draw_buttons()
        else:
            if self.algo_changed != "":
                self.algo_changed = None
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

        self.brief_frame = tk.Frame(info_frame)
        self.bots_label = tk.Label(
            self.brief_frame, text="\n\nSelect bot from:", font=spec_font
        )
        self.menu_usage = tk.Frame(self.brief_frame)

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
                row_num += 1

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

        self.main_frame = tk.Frame(info_frame)
        frame_row = 0
        top_frame = tk.Frame(self.main_frame)
        top_frame.grid(row=frame_row, column=0, sticky="NSEW", columnspan=2)
        under_dev_label = tk.Label(
            top_frame, text="This page is under development", fg="red"
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
            self.info_value[item] = tk.Label(info_left, text="")
            self.info_name[item].pack(anchor="w")
            self.info_value[item].pack(anchor="w")

        # Frame for Bot's algorithm loaded from the strategy.py file
        frame_row += 1
        self.strategy = tk.Frame(self.main_frame)
        self.strategy.grid(row=frame_row, column=0, sticky="NSWE", columnspan=2)
        self.strategy_scroll = AutoScrollbar(self.strategy, orient="vertical")
        self.strategy_text = tk.Text(
            self.strategy, highlightthickness=0, yscrollcommand=self.strategy_scroll.set
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
        self.main_frame.grid_rowconfigure(frame_row, weight=1)


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
