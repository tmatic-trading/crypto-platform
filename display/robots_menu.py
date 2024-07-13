import tkinter as tk
from tkinter import ttk, StringVar
import os
import shutil
import re
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name
#from pygments.token import Token
import traceback

from .variables import Variables as disp, AutoScrollbar
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


    def check_syntax(self, code):
        try:
            # Compile the code to check for syntax errors
            compiled_code = compile(code, '<string>', 'exec')
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
        text = tk.Text(self.app.pop_up, highlightthickness=0, yscrollcommand=scroll.set, bg=disp.title_color)
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
            if self.name == "Back":
                self.app.selected_bot = ""
                disp.menu_robots.pack_forget()
                disp.pw_rest1.pack(fill="both", expand="yes")
            elif self.name == "Delete":
                self.app.delete_bot()
            elif self.name == "Syntax":
                bot_name = self.app.selected_bot
                #path = os.path.join(self.app.algo_dir, bot_name)
                #content = self.app.read_file(f"{str(path)}/strategy.py")
                content = self.app.strategy_text.get("1.0", tk.END)
                self.open_popup(bot_name, content)
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
        self.button_list = ["Syntax", "Backtest", "Activate", "Update", "Duplicate", "Delete", "Back"]
        self.rows_list = ["Name", "Currency", "Created", "Updated", "Status", "Timeframe", "Capital", "Leverage", "PNL"]
        self.selected_bot = ""#"112"
        self.algo_dir = f"{os.getcwd()}/algo/"
        self.bots_list = [x[0].replace(self.algo_dir, "") for x in os.walk(self.algo_dir)]
        self.pop_up = None

        # Keeps the bot's algorithm derived from strategy.py file
        self.bot_algo = ""

        # To trace whether a new bot's name is unique
        self.name_trace = StringVar(name="Name" + str(self))

        # Create initial frames
        self.create_right_frames()
        self.show_bot()

        # CustomButton array
        self.buttons_center = []

        for button in self.button_list:
            frame = CustomButton(self.root_frame, self, button, bg=disp.bg_select_color, text=button, bd=0, activebackground=disp.bg_active)
            self.buttons_center.append(frame)

        self.draw_buttons()

    def draw_buttons(self):
        #self.buttons_center.sort(key=lambda f: f.winfo_y())
        total_height = 0
        for i, button in enumerate(self.buttons_center):
            if button.name == "Back":
                button.configure(state="normal")
            elif button.name == "Delete":
                if self.selected_bot != "":
                    button.configure(state="normal")
                else:
                    button.configure(state="disabled")
            elif button.name == "Syntax":
                if self.selected_bot != "":
                    button.configure(state="normal")
                else:
                    button.configure(state="disabled")
            else:
                button.configure(state="disabled")
            #button.update_idletasks()#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
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

    def show_bot(self):
        '''Shows the bot's info when self.selected_bot != "". Otherwise hides'''
        for i, row in enumerate(self.rows_list):
            if self.selected_bot != "":
                self.col_0_label[row].pack(anchor="w", padx=10)
                self.col_1_entry[row].pack_forget()
                self.col_1_label[row].pack(anchor="w", padx=10)
            else:
                if i < 2:# Only bot's Name and Currency
                    self.col_0_label[row].pack(anchor="w", padx=10)
                    self.col_1_entry[row].pack(anchor="w")
                    self.col_1_label[row].pack_forget()
                else:
                    self.col_0_label[row].pack_forget()
                    self.col_1_entry[row].pack_forget()
                    self.col_1_label[row].pack_forget()
        if self.selected_bot != "":
            self.col_1_label["Name"].config(text=self.selected_bot)
            self.button_create.pack_forget()
            self.strategy_text.grid(row=0, column=0, sticky="NSEW")
            self.strategy_scroll.grid(row=0, column=1, sticky="NS")

            path = os.path.join(self.algo_dir, self.selected_bot)
            file = open(f"{path}/strategy.py", 'r')
            self.bot_algo = file.read()
            file.close()
            self.insert_code(self.strategy_text, self.bot_algo)
        else:
            self.button_create.pack()
            self.button_create.config(state="disabled")
            self.strategy_text.grid_forget()
            self.strategy_scroll.grid_forget()
            self.bot_algo = ""

    def delete_bot(self):
        path = os.path.join(self.algo_dir, self.selected_bot)
        #files = os.listdir(path)
        shutil.rmtree(str(path))
        self.selected_bot = ""
        self.show_bot()
        self.draw_buttons()

    def insert_code(self, text_widget, code):
        '''Function to insert Python code into a Tkinter Text widget with syntax highlighting'''
        text_widget.delete(1.0, tk.END)
        lexer = PythonLexer()
        style = get_style_by_name("default")# You can change the style if desired
    
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
        file = open(file_name, 'r')
        content = file.read()
        file.close()
        return content
    
    def write_file(self, file_name, content):
        file = open(file_name, 'a')
        file.write(content)
        file.close()

    def create_bot(self):
        bot_name = self.name_trace.get()
        path = os.path.join(self.algo_dir, bot_name)
        # Create a new directory with the name as the new bot's name
        os.mkdir(path)
        # Create the '__init__.py' file in the new directory. This file is empty
        self.create_file(f"{str(path)}/__init__.py")
        # Load the content of 'init.py' file
        content = self.read_file(f"{self.algo_dir}init.py")
        # Create new 'init.py' file in the new directory
        self.create_file(f"{str(path)}/init.py")
        # Write the initial content into the new 'init.py' file
        self.write_file(f"{str(path)}/init.py", content)
        # Create new 'strategy.py' file in the new directory
        self.create_file(f"{str(path)}/strategy.py")
        # Write the initial content into the new 'strategy.py' file
        self.write_file(f"{str(path)}/strategy.py", "import services as service\nfrom api.api import Markets\nfrom common.data import Instrument\nfrom functions import Function\n")
        # Create new '.gitignore' file in the new directory
        self.create_file(f"{str(path)}/.gitignore")
        # Write the initial content into the new '.gitignore' file
        self.write_file(f"{str(path)}/.gitignore", "*\n!__init__.py\n!.gitignore\n!init.py\n!strategy.py\n")

        self.selected_bot = bot_name
        self.col_1_entry["Name"].delete(0, tk.END)
        self.show_bot()
        self.draw_buttons()

    def trace_callback(self, var, index, mode):
        name = var.replace(str(self), "")
        bot_name = re.sub('[\W]+', '', self.name_trace.get())
        if bot_name in self.bots_list or bot_name != self.name_trace.get():
            self.col_1_entry[name].config(style=f"used.TEntry")
            self.button_create.config(state="disabled")
        else:
            self.col_1_entry[name].config(style=f"free.TEntry")
            self.button_create.config(state="normal")

    def create_right_frames(self):
        target_frame = robots_right
        widget_row = 0
        self.bot_top = tk.Frame(target_frame)
        self.bot_top.grid(row=widget_row, column=0, sticky="EW", columnspan=2)
        self.setting_label = tk.Label(self.bot_top, text="This page is under development", fg="red")
        self.setting_label.pack(side="left", padx=10)

        widget_row += 1
        self.col_0 = tk.Frame(target_frame)
        self.col_0.grid(row=widget_row, column=0, sticky="W")
        self.col_1 = tk.Frame(target_frame)
        self.col_1.grid(row=widget_row, column=1, sticky="W")

        # Widgets dictionaries for bot's data according to self.rows_list
        self.col_0_label = {}
        self.col_1_entry = {}
        self.col_1_label = {}

        for i, row in enumerate(self.rows_list):
            self.col_0_label[row] = tk.Label(self.col_0, text=row)
            self.col_1_entry[row] = ttk.Entry(self.col_1, width=30, style="default.TEntry")
            if row == "Name":
                self.col_1_entry[row].config(textvariable=self.name_trace)
                self.name_trace.trace_add('write', self.trace_callback)
            self.col_1_label[row] = tk.Label(self.col_1)
        self.button_create = tk.Button(self.col_1, activebackground=disp.bg_active, text="Create Bot", command=lambda: self.create_bot(), state="disabled")

        widget_row += 1
        self.strategy = tk.Frame(target_frame)
        self.strategy.grid(row=widget_row, column=0, sticky="NSWE", columnspan=2)

        self.strategy_scroll = AutoScrollbar(self.strategy, orient="vertical")
        self.strategy_text = tk.Text(self.strategy, highlightthickness=0, yscrollcommand=self.strategy_scroll.set)
        self.strategy_scroll.config(command=self.strategy_text.yview)
        self.strategy_text.grid(row=0, column=0, sticky="NSEW")
        self.strategy_scroll.grid(row=0, column=1, sticky="NS")
        self.strategy.grid_columnconfigure(0, weight=1)
        self.strategy.grid_columnconfigure(1, weight=0)
        self.strategy.grid_rowconfigure(0, weight=1)

        target_frame.grid_columnconfigure(0, weight=1)
        target_frame.grid_columnconfigure(1, weight=10)
        for i in range(widget_row):
            target_frame.grid_rowconfigure(i, weight=0)
            if i == widget_row - 1:
                # The following row is for self.strategy widget
                target_frame.grid_rowconfigure(widget_row, weight=1)

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