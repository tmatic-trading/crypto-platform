import os
import tkinter as tk
from collections import OrderedDict
from pathlib import Path
from tkinter import StringVar, ttk

from dotenv import dotenv_values, set_key

import services as service
from display.variables import Variables as disp


class SettingsApp:
    def __init__(self, root: tk.Frame):
        self.root_frame = root
        self.root_frame.config(bg=disp.bg_color)
        self.root_frame.grid_columnconfigure(0, weight=1)
        self.root_frame.grid_rowconfigure(0, weight=1)
        self.bg_select_color = disp.bg_select_color
        self.bg_entry = disp.light_gray_color
        self.bg_active = disp.bg_select_color
        self.bg_changed = "yellow"

        self.title_color = tk.Label(root, text=" TRADING: ")["background"]

        self.common_trace_changed = {}

        self.common_settings = OrderedDict()
        self.common_settings["MARKET_LIST"] = "Bitmex,Bybit,Deribit"
        self.common_settings["SQLITE_DATABASE"] = "tmatic.db"
        self.common_settings["ORDER_BOOK_DEPTH"] = "orderBook"
        self.common_settings["BOTTOM_FRAME"] = "robots"
        self.common_settings["REFRESH_RATE"] = "5"
        for setting in self.common_settings.keys():
            self.common_trace_changed[setting] = StringVar(name=setting + str(self))
            self.common_trace_changed[setting].set(self.common_settings[setting])
        self.common_def = {}
        self.common_defaults = {}
        self.common_flag = {}

        self.market_list = self.common_settings["MARKET_LIST"].split(",")
        self.market_settings = [
            "CONNECTED",
            "HTTP_URL",
            "WS_URL",
            "API_KEY",
            "API_SECRET",
            "TESTNET_HTTP_URL",
            "TESTNET_WS_URL",
            "TESTNET_API_KEY",
            "TESTNET_API_SECRET",
            "TESTNET",
        ]
        self.market_color = {}
        self.market_defaults = {}
        self.market_trace = {}
        self.market_changed = {}
        self.market_saved = {}
        self.market_flag = {}
        for market in self.market_list:
            self.market_color[market] = self.bg_entry
            self.market_defaults[market] = {}
            self.market_changed[market] = {}
            self.market_saved[market] = {}
            self.market_flag[market] = {}
            for setting in self.market_settings:
                self.market_defaults[market][setting] = ""
                self.market_changed[market][setting] = ""
                self.market_saved[market][setting] = ""
                self.market_flag[market][setting] = 0
            if market == "Bitmex":
                self.market_defaults[market][
                    "HTTP_URL"
                ] = "https://www.bitmex.com/api/v1/"
                self.market_defaults[market]["WS_URL"] = "wss://ws.bitmex.com/realtime/"
                self.market_defaults[market][
                    "TESTNET_HTTP_URL"
                ] = "https://testnet.bitmex.com/api/v1/"
                self.market_defaults[market][
                    "TESTNET_WS_URL"
                ] = "wss://testnet.bitmex.com/realtime/"
            elif market == "Bybit":
                self.market_defaults[market]["HTTP_URL"] = "https://api.bybit.com/v5/"
                self.market_defaults[market]["WS_URL"] = "wss://api.bybit.com/v5/"
                self.market_defaults[market][
                    "TESTNET_HTTP_URL"
                ] = "https://api-testnet.bybit.com/v5/"
                self.market_defaults[market][
                    "TESTNET_WS_URL"
                ] = "wss://api-testnet.bybit.com/v5/"
            elif market == "Deribit":
                pass
            self.market_defaults[market]["CONNECTED"] = "YES"
            self.market_defaults[market]["TESTNET"] = "ACTIVE"

        self.indent = "  "
        self.entry_width = 45

        # To keep track whether market is clicked
        self.click_market = "false"

        # To keep track of the selected frame
        self.selected_frame = None

        # If settings_flag value is not 0, than at least one setting is changed
        self.settings_flag = 0

        # DraggableFrame array
        self.settings_center = []

        self.env_file_path = Path(".env.Settings")
        self.settings_bottom = tk.Frame(self.root_frame, bg=disp.bg_color)
        self.setting_button = tk.Button(
            self.settings_bottom,
            bg=self.bg_select_color,
            activebackground=self.bg_active,
            text="Settings Saved",
            command=lambda: self.save_dotenv("button"),
        )
        self.setting_button.pack()
        self.setting_button.config(state="disabled")
        self.initialized = False

    def load(self):
        if not os.path.isfile(self.env_file_path):
            # The .env file does not exist, so create the file.
            self.env_file_path.touch(mode=0o600, exist_ok=False)
            # Set default settings for each market.
            for market in self.market_list:
                for setting in self.market_settings:
                    self.market_changed[market][setting] = self.market_defaults[market][
                        setting
                    ]
            self.save_dotenv("new")
        else:
            dotenv_data = dotenv_values(self.env_file_path)
            for setting in self.common_settings.keys():
                try:
                    self.common_defaults[setting] = dotenv_data[setting]
                except KeyError:
                    self.common_defaults[setting] = self.common_settings[setting]
                self.common_trace_changed[setting].set(self.common_defaults[setting])
            # self.market_list = self.common_defaults["MARKET_LIST"].split(",")
            for market in self.market_list:
                for setting in self.market_settings:
                    try:
                        self.market_saved[market][setting] = dotenv_data[
                            f"{market}_{setting}"
                        ].replace(f"_{market}", "")
                    except KeyError:
                        self.market_saved[market][setting] = self.market_defaults[
                            market
                        ][setting]
                    self.market_changed[market][setting] = self.market_saved[market][
                        setting
                    ]

    def init(self):
        """
        Create the initial static frames.
        """
        if not self.initialized:
            self.create_static_frames()
            for i, market in enumerate(self.market_list):
                my_bg = self.bg_entry if i != 0 else self.bg_select_color
                frame = DraggableFrame(
                    self.root_frame,
                    self,
                    market,
                    bg=my_bg,
                    text=market,
                    relief="groove",
                    bd=0,
                    activebackground=self.bg_active,
                )
                if self.market_saved[market]["CONNECTED"] == "YES":
                    frame.var.set(1)
                if i == 0:
                    self.selected_frame = frame
                self.settings_center.append(frame)
            self.reorder_frames()
            self.set_market_fields(self.market_list[0])

            # Bind event for focus change
            self.root_frame.bind("<FocusIn>", self.on_focus_in)

            self.initialized = True
            # service.wrap(frame=disp.frame_tips, padx=5)

    def on_focus_in(self, event):
        pass
        # self.reorder_frames()

    def reorder_frames(self):
        self.settings_center.sort(key=lambda f: f.winfo_y())
        total_height = self.static_frames_height
        for frame in self.settings_center:
            frame.update_idletasks()
            frame_height = frame.winfo_reqheight()
            frame.place_configure(
                x=0, y=total_height + frame_height, height=frame_height, relwidth=1.0
            )
            total_height += frame_height
        # Update market_list
        self.market_list = [frame.market for frame in self.settings_center]
        # Remember the new market order
        self.common_trace_changed["MARKET_LIST"].set(self.get_str_markets())
        self.check_common_flag("MARKET_LIST")
        # print(self.common_defaults["MARKET_LIST"], self.common_trace_changed["MARKET_LIST"].get())

    def update_positions(self, moving_frame):
        current_y = moving_frame.winfo_y()
        moving_index = self.settings_center.index(moving_frame)
        for i, frame in enumerate(self.settings_center):
            if frame is moving_frame:
                continue
            frame_y = frame.winfo_y()
            frame_height = frame.winfo_height()
            if current_y < frame_y and moving_index > i:
                self.settings_center.insert(i, self.settings_center.pop(moving_index))
                self.reorder_frames()
                break
            elif current_y > frame_y + frame_height and moving_index < i:
                self.settings_center.insert(
                    i + 1, self.settings_center.pop(moving_index)
                )
                self.reorder_frames()
                break

    def set_common_fields(self):
        """
        Fills the common settings with default values.
        """
        for setting, value in self.common_defaults.items():
            if setting != "MARKET_LIST":
                widget_type = self.entry_common[setting].winfo_class()
                if widget_type == "TCombobox":
                    self.entry_common[setting].set(value)
                else:
                    self.entry_common[setting].delete(0, tk.END)
                    self.entry_common[setting].insert(0, value)
                self.entry_common[setting].selection_clear()
                self.entry_common[setting].config(style=f"default.{widget_type}")

    def set_market_fields(self, market):
        """
        Fills the market settings with current values.
        """
        for setting, value in self.market_changed[market].items():
            if setting != "CONNECTED":
                widget_type = self.entry_market[setting].winfo_class()
                if widget_type == "TCombobox":
                    self.entry_market[setting].config(state="readonly")
                    self.entry_market[setting].set(value)
                else:
                    self.entry_market[setting].config(state="normal")
                    self.entry_market[setting].delete(0, tk.END)
                    self.entry_market[setting].insert(0, value)
                self.entry_market[setting].selection_clear()
                if self.market_flag[market][setting] != 0:
                    self.entry_market[setting].config(style=f"changed.{widget_type}")
                else:
                    self.entry_market[setting].config(style=f"default.{widget_type}")
                if self.market_changed[market]["CONNECTED"] == "NO":
                    self.entry_market[setting].config(state="disabled")
        self.root_frame.focus()

    def get_str_markets(self):
        return ",".join(str(x) for x in self.market_list)

    def insert_comment(self, file_path, comment):
        with open(file_path, "a") as file:
            file.write(f"# {comment}\n")

    def common_trace_callback(self, var, index, mode):
        """
        Called when the corresponding common setting changed.
        """
        self.check_common_flag(var.replace(str(self), ""))

    def market_trace_callback(self, var, index, mode):
        """
        Called when the corresponding market setting changed.
        """
        var = var.replace(str(self), "")
        if self.selected_frame != None and self.click_market == "false":
            market = self.selected_frame.market
            self.market_changed[market][var] = self.market_trace[var].get()
            self.check_market_flag(var, market)

    def check_common_flag(self, var):
        """
        Tracks and keeps changes for common settings until the moment they
        are saved.
        """
        if var in self.common_flag:
            if self.common_trace_changed[var].get() != self.common_defaults[var]:
                if self.common_flag[var] == 0:
                    self.settings_flag += 1
                    self.common_flag[var] = 1
                    if var != "MARKET_LIST":
                        widget_type = self.entry_common[var].winfo_class()
                        self.entry_common[var].config(style=f"changed.{widget_type}")
                    self.set_button_color(self.settings_flag)
            else:
                if self.common_flag[var] != 0:
                    self.settings_flag -= 1
                    self.common_flag[var] = 0
                    if var != "MARKET_LIST":
                        widget_type = self.entry_common[var].winfo_class()
                        self.entry_common[var].config(style=f"default.{widget_type}")
                    self.set_button_color(self.settings_flag)
            # print(var, self.common_trace_changed[var].get(), self.common_defaults[var], self.common_flag[var], self.settings_flag)

    def check_market_flag(self, var, market):
        """
        Tracks and keeps changes for market settings until the moment they
        are saved.
        """
        if self.market_changed[market][var] != self.market_saved[market][var]:
            if self.market_flag[market][var] == 0:
                self.settings_flag += 1
                self.market_flag[market][var] = 1
                if var != "CONNECTED":
                    widget_type = self.entry_market[var].winfo_class()
                    self.entry_market[var].config(style=f"changed.{widget_type}")
                self.market_color[market] = self.bg_changed
                self.set_button_color(self.settings_flag)
        else:
            if self.market_flag[market][var] != 0:
                self.settings_flag -= 1
                self.market_flag[market][var] = 0
                if var != "CONNECTED":
                    widget_type = self.entry_market[var].winfo_class()
                    self.entry_market[var].config(style=f"default.{widget_type}")
                self.market_color[market] = self.bg_entry
                for setting in self.market_changed[market]:
                    if self.market_flag[market][setting] != 0:
                        self.market_color[market] = self.bg_changed
                        break
                self.set_button_color(self.settings_flag)

    def set_button_color(self, flag):
        if flag == 0:
            self.setting_button.configure(
                bg=self.bg_select_color, text="Settings Saved"
            )
            self.setting_button.config(state="disabled")
        else:
            self.setting_button.configure(bg=self.bg_changed, text="Save Settings")
            self.setting_button.config(state="active")

    def save_dotenv(self, status):
        """
        Saves common and market settings into .env file.
        """
        with open(self.env_file_path, "w") as f:
            pass
        for setting in self.common_settings.keys():
            set_key(
                dotenv_path=self.env_file_path,
                key_to_set=setting,
                value_to_set=self.common_trace_changed[setting].get(),
            )
            self.common_defaults[setting] = self.common_trace_changed[setting].get()
        for market in self.market_list:
            self.insert_comment(self.env_file_path, f"")
            for setting in self.market_settings:
                set_key(
                    dotenv_path=self.env_file_path,
                    key_to_set=f"{market}_{setting}",
                    value_to_set=self.market_changed[market][setting],
                )
                self.market_saved[market][setting] = self.market_changed[market][
                    setting
                ]
        self.set_all_flags_to_zero()
        if status != "new":
            self.set_market_fields(self.selected_frame.market)
            self.set_common_fields()
        self.setting_button.config(state="disabled")

    def set_all_flags_to_zero(self):
        self.settings_flag = 0
        for setting in self.common_settings.keys():
            self.common_flag[setting] = 0
        for market in self.market_list:
            self.market_color[market] = self.bg_entry
            for setting in self.market_settings:
                self.market_flag[market][setting] = 0
        for frame in self.settings_center:
            if frame != self.selected_frame:
                frame.config(bg=self.market_color[frame.market])
        self.set_button_color(0)

    def create_static_frames(self):
        static_frames_list = []
        widget_row = 0
        self.settings_top = tk.Frame(self.root_frame, bg=disp.bg_color)
        self.settings_top.grid_columnconfigure(0, weight=1)
        # self.settings_top.grid_rowconfigure(0, weight=1)
        self.settings_top.grid(row=widget_row, column=0, sticky="W", columnspan=3)
        self.setting_label = tk.Label(
            self.settings_top,
            text="The settings are located in the .env.Settings file.\n",
            bg=disp.bg_color,
        )
        static_frames_list.append(self.settings_top)
        self.setting_label.pack()

        # Custom style for the Combobox and Entry widgets
        ttk.Style().map(
            "default.TCombobox",
            fieldbackground=[
                ("readonly", self.bg_entry),
                ("disabled", self.title_color),
            ],
        )
        ttk.Style().map(
            "changed.TCombobox",
            fieldbackground=[
                ("readonly", self.bg_changed),
                ("disabled", self.title_color),
            ],
        )
        ttk.Style().configure("default.TEntry", fieldbackground=self.bg_entry)
        ttk.Style().configure("changed.TEntry", fieldbackground=self.bg_changed)

        # Draw grid for common settings
        self.common_col_0 = {}
        self.common_col_0_label = {}
        self.common_col_1 = {}
        self.entry_common = {}
        for setting in self.common_settings.keys():
            # self.common_trace_changed[setting] = StringVar(name=setting + str(self))
            if setting != "MARKET_LIST":
                widget_row += 1
                self.common_col_0[setting] = tk.Frame(self.root_frame)
                l = tk.Label(self.root_frame, bg=disp.bg_color)
                l.grid(row=widget_row, column=0, sticky="W")
                self.common_col_0[setting].grid(row=widget_row, column=1, sticky="W")
                self.common_col_0_label[setting] = tk.Label(
                    self.common_col_0[setting],
                    text=setting + self.indent,
                    bg=disp.bg_color,
                )
                self.common_col_0_label[setting].pack()
                self.common_col_1[setting] = tk.Frame(self.root_frame)
                self.common_col_1[setting].grid(row=widget_row, column=2, sticky="W")
                self.common_trace_changed[setting].trace_add(
                    "write", self.common_trace_callback
                )
                if setting == "SQLITE_DATABASE":
                    self.entry_common[setting] = ttk.Entry(
                        self.common_col_1[setting],
                        width=self.entry_width,
                        textvariable=self.common_trace_changed[setting],
                        style="default.TEntry",
                    )
                    # self.entry_common[setting].insert(0, "tmatic.db")
                elif setting == "ORDER_BOOK_DEPTH":
                    self.entry_common[setting] = ttk.Combobox(
                        self.common_col_1[setting],
                        width=self.entry_width,
                        textvariable=self.common_trace_changed[setting],
                        state="readonly",
                        style="default.TCombobox",
                    )
                    self.entry_common[setting]["values"] = ("orderBook", "quote")
                    self.entry_common[setting].current(0)
                elif setting == "BOTTOM_FRAME":
                    self.entry_common[setting] = ttk.Combobox(
                        self.common_col_1[setting],
                        width=self.entry_width,
                        textvariable=self.common_trace_changed[setting],
                        state="readonly",
                        style="default.TCombobox",
                    )
                    self.entry_common[setting]["values"] = (
                        "Orders",
                        "Robots",
                        "Wallet",
                        "Trades",
                        "Funding",
                        "Result",
                    )
                    self.entry_common[setting].current(1)
                elif setting == "REFRESH_RATE":
                    self.entry_common[setting] = ttk.Combobox(
                        self.common_col_1[setting],
                        width=self.entry_width,
                        textvariable=self.common_trace_changed[setting],
                        state="readonly",
                        style="default.TCombobox",
                    )
                    values = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
                    self.entry_common[setting]["values"] = values
                    self.entry_common[setting].current(4)
                self.entry_common[setting].pack()
                static_frames_list.append(self.common_col_0[setting])
                # Set the initial value for common setting
                self.common_defaults[setting] = self.entry_common[setting].get()
            else:
                # Set the initial value for common setting
                self.common_defaults[setting] = self.get_str_markets()
            self.common_trace_changed[setting].set(self.common_defaults[setting])
            self.common_flag[setting] = 0

        # Calculate the total height of static frames
        self.static_frames_height = 0
        for frame in static_frames_list:
            frame.update_idletasks()
            self.static_frames_height += frame.winfo_reqheight()

        self.root_frame.grid_columnconfigure(0, weight=1)
        self.root_frame.grid_columnconfigure(1, weight=2)
        self.root_frame.grid_columnconfigure(2, weight=2)

        # Draw blank frames. They are of no use
        self.blank_row = []
        self.blank_label = []
        for i in range(len(self.market_list)):
            widget_row += 1
            self.blank_row.append(tk.Frame(self.root_frame, bg=disp.bg_color))
            self.blank_row[i].grid(row=widget_row, column=0, sticky="EW", columnspan=3)
            self.blank_label.append(
                tk.Label(self.blank_row[i], text="", bg=disp.bg_color)
            )
            self.blank_label[i].pack()

        widget_row += 1
        l = tk.Label(self.root_frame, text="\n", bg=disp.bg_color)
        l.grid(row=widget_row, column=0, sticky="W", columnspan=3)

        # Draw grid representing settings for markets
        self.market_col_0 = {}
        self.market_col_0_label = {}
        self.market_col_1 = {}
        self.entry_market = {}
        for setting in self.market_settings:
            self.market_trace[setting] = StringVar(name=setting + str(self))
            if setting != "CONNECTED":
                widget_row += 1
                self.market_col_0[setting] = tk.Frame(self.root_frame)
                l = tk.Label(self.root_frame, bg=disp.bg_color)
                l.grid(row=widget_row, column=0, sticky="W")
                self.market_col_0[setting].grid(row=widget_row, column=1, sticky="W")
                self.market_col_0_label[setting] = tk.Label(
                    self.market_col_0[setting],
                    text=setting + self.indent,
                    bg=disp.bg_color,
                )
                self.market_col_0_label[setting].pack(side="left", fill="both")
                self.market_col_1[setting] = tk.Frame(self.root_frame)
                self.market_col_1[setting].grid(row=widget_row, column=2, sticky="W")
                self.market_trace[setting].trace_add(
                    "write", self.market_trace_callback
                )
                if setting == "TESTNET":
                    self.entry_market[setting] = ttk.Combobox(
                        self.market_col_1[setting],
                        width=self.entry_width,
                        textvariable=self.market_trace[setting],
                        state="readonly",
                        style="default.TCombobox",
                    )
                    self.entry_market[setting]["values"] = ("ACTIVE", "OFF")
                    self.entry_market[setting].current(0)
                    self.entry_market[setting].pack()
                else:
                    self.entry_market[setting] = ttk.Entry(
                        self.market_col_1[setting],
                        width=self.entry_width,
                        textvariable=self.market_trace[setting],
                        style="default.TEntry",
                    )
                    self.entry_market[setting].pack()

        widget_row += 1
        self.settings_indent_row = tk.Frame(self.root_frame, bg=disp.bg_color)
        self.settings_indent_row.grid(
            row=widget_row, column=0, sticky="EW", columnspan=3
        )
        self.settings_indent_label = tk.Label(
            self.settings_indent_row, text="", bg=disp.bg_color
        )
        self.settings_indent_label.pack()

        widget_row += 1
        self.settings_bottom.grid(row=widget_row, column=0, sticky="EW", columnspan=3)
        for i in range(widget_row):
            self.root_frame.grid_rowconfigure(i, weight=0)


class DraggableFrame(tk.Checkbutton):
    def __init__(self, master, app: SettingsApp, market, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.market = market
        self.var = tk.IntVar()
        self.config(variable=self.var, onvalue=1, offvalue=0)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)

        self.start_y = None
        self.is_dragging = False

    def on_press(self, event):
        self.start_y = event.y_root
        self.is_dragging = True
        # Bring the frame to the front
        self.lift()
        box_x, x = int(self.winfo_width() / 2 - self.winfo_reqwidth() / 2), event.x
        checked = "false"
        if x < box_x + 5 or x > box_x + 22:
            # No check or uncheck here
            self.toggle()
        else:
            checked = "true"
            if self.var.get() == 0:
                self.app.market_changed[self.market]["CONNECTED"] = "YES"
            else:
                self.app.market_changed[self.market]["CONNECTED"] = "NO"
            self.app.check_market_flag("CONNECTED", self.market)
        self.set_background_color(checked)

    def on_drag(self, event):
        if self.is_dragging:
            dy = event.y_root - self.start_y
            self.start_y = event.y_root
            current_y = self.winfo_y()
            new_y = current_y + dy
            # Restrict dragging to within the parent frame
            new_y = max(
                0, min(new_y, self.app.root_frame.winfo_height() - self.winfo_height())
            )
            self.place_configure(y=new_y)
            self.app.update_positions(self)

    def on_release(self, event):
        self.is_dragging = False
        self.app.reorder_frames()

    def set_background_color(self, checked):
        """
        Set background color for selected market.
        """
        if self != self.app.selected_frame or checked == "true":
            self.app.selected_frame.config(
                bg=self.app.market_color[self.app.selected_frame.market]
            )
            self.app.selected_frame = self
            self.config(bg=self.app.bg_select_color)
            self.app.click_market = "true"
            self.app.set_market_fields(self.market)
            self.app.click_market = "false"


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x600")
    app = SettingsApp(root)
    root.mainloop()
