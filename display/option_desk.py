import tkinter as tk

from api.api import Markets
from common.data import Instrument
from common.variables import Variables as var

from .headers import Header
from .variables import ScrollFrame, TreeTable, TreeviewTable
from .variables import Variables as disp


class OptionDesk:
    def __init__(self) -> None:
        self.is_on = False
        self.ws: Markets
        self.dash = ["-", "-", "-", "-", "-", "-", "-", "-", "-"]

    def on_closing(self) -> None:
        self.is_on = False
        self.desk.destroy()

    def create(self, instrument: Instrument):
        self.is_on = True
        self.market = instrument.market
        self.category = instrument.category
        self.currency = instrument.settlCurrency[0]
        self.ws = Markets[self.market]
        self.calls = self.ws.instrument_index[self.category][self.currency][
            instrument.symbol
        ]["CALLS"]
        self.puts = self.ws.instrument_index[self.category][self.currency][
            instrument.symbol
        ]["PUTS"]
        self.calls_set = set(self.calls)
        self.puts_set = set(self.puts)
        call_strikes = list(map(lambda x: x.split("-")[-2], self.calls))
        put_strikes = list(map(lambda x: x.split("-")[-2], self.puts))
        self.strikes = list(set(call_strikes).union(set(put_strikes)))
        try:
            self.strikes.sort(key=lambda x: float(x))
        except Exception:
            self.strikes.sort()
        symb = instrument.symbol.split(var._series)[0]
        self._calls = [f"{symb}-{strike}-C" for strike in self.strikes]
        self._puts = [f"{symb}-{strike}-P" for strike in self.strikes]

        self.desk = tk.Toplevel()
        self.desk.geometry(
            "{}x{}".format(disp.window_width, int(disp.window_height * 0.8))
        )
        self.desk.title(f"{self.market} options ({self.currency})")
        self.desk.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.desk.grid_rowconfigure(0, weight=0)
        self.desk.grid_rowconfigure(1, weight=1000)  # change weight to 4
        self.desk.grid_columnconfigure(0, weight=1)
        self.desk.grid_columnconfigure(1, weight=0)
        self.desk.grid_columnconfigure(2, weight=1)

        self.label = tk.Label(self.desk, text="Calls", font=disp.bold_font)
        self.label.grid(row=0, column=0, sticky="NSEW")
        tk.Label(self.desk, text=instrument.symbol, font=disp.bold_font).grid(
            row=0, column=1, sticky="NSEW"
        )
        tk.Label(self.desk, text="Puts", font=disp.bold_font).grid(
            row=0, column=2, sticky="NSEW"
        )

        bottom = tk.Frame(self.desk, bg=disp.bg_color)
        bottom.grid(row=1, column=0, columnspan=3, sticky="NSEW")
        bottom.grid_rowconfigure(0, weight=0)
        bottom.grid_rowconfigure(1, weight=100)
        bottom.grid_columnconfigure(0, weight=10)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_columnconfigure(2, weight=10)
        bottom.grid_columnconfigure(3, weight=0)
        self.calls_headers = tk.Frame(bottom)
        strikes_headers = tk.Frame(bottom)
        puts_headers = tk.Frame(bottom)
        self.calls_headers.grid(row=0, column=0, sticky="NEWS")
        strikes_headers.grid(row=0, column=1, sticky="NEWS")
        puts_headers.grid(row=0, column=2, sticky="NEWS")
        trim = tk.Label(bottom, text="  ")
        trim.grid(row=0, column=3)

        headers_calls = TreeviewTable(
            frame=self.calls_headers,
            name="t",
            title=Header.name_calls,
            size=0,
            cancel_scroll=True,
        )
        headers_strikes = TreeviewTable(
            frame=strikes_headers,
            name="t",
            title=Header.name_strikes,
            size=0,
            cancel_scroll=True,
        )
        headers_puts = TreeviewTable(
            frame=puts_headers,
            name="t",
            title=Header.name_puts,
            size=0,
            cancel_scroll=True,
        )

        bottom_sub = tk.Frame(bottom, bg=disp.bg_color)
        bottom_sub.grid_rowconfigure(0, weight=1)
        bottom_sub.grid_columnconfigure(0, weight=1)
        bottom_sub.grid(row=1, column=0, columnspan=4, sticky="NEWS")
        main = ScrollFrame(bottom_sub, bg=disp.bg_color, bd=0, trim=trim)
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=10)
        main.grid_columnconfigure(1, weight=1)
        main.grid_columnconfigure(2, weight=10)
        calls_body = tk.Frame(main, bg=disp.bg_color)
        strikes_body = tk.Frame(main, bg=disp.bg_color)
        puts_body = tk.Frame(main, bg=disp.bg_color)
        calls_body.grid(row=0, column=0, sticky="NEWS")
        strikes_body.grid(row=0, column=1, sticky="NEWS")
        puts_body.grid(row=0, column=2, sticky="NEWS")

        TreeTable.calls = TreeviewTable(
            frame=calls_body,
            name="calls",
            title=Header.name_calls,
            size=len(self.strikes),
            # bind=OptionDesk.handler,
            style="option.Treeview",
            cancel_scroll=True,
            headings=False,
        )
        TreeTable.strikes = TreeviewTable(
            frame=strikes_body,
            name="strikes",
            title=Header.name_strikes,
            size=len(self.strikes),
            style="option.Treeview",
            cancel_scroll=True,
            headings=False,
        )
        TreeTable.puts = TreeviewTable(
            frame=puts_body,
            name="puts",
            title=Header.name_puts,
            size=len(self.strikes),
            # bind=OptionDesk.handler,
            style="option.Treeview",
            cancel_scroll=True,
            headings=False,
        )

        headers_calls.tree.bind(
            "<B1-Motion>", lambda event: trim_columns(event, TreeTable.calls)
        )
        headers_puts.tree.bind(
            "<B1-Motion>", lambda event: trim_columns(event, TreeTable.puts)
        )

        for num, strike in enumerate(self.strikes):
            values = [strike]
            TreeTable.strikes.update(num, values=values)


def trim_columns(event, body: TreeTable):
    headers = event.widget
    cols = ("#0",) + headers.cget("columns")  # tuple of all columns
    for column in cols:
        body.tree.column(column, width=headers.column(column, "width"))


options_desk = OptionDesk()
