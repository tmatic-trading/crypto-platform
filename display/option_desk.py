import tkinter as tk

from api.api import Markets
from common.data import Instrument
from common.variables import Variables as var

from .variables import ScrollFrame, TreeviewTable
from .variables import Variables as disp


class TreeTable:
    calls: TreeviewTable
    strike: TreeviewTable
    puts: TreeviewTable


class OptionDesk:
    def create(instrument: Instrument):
        market = instrument.market
        category = instrument.category
        currency = instrument.settlCurrency[0]
        desk = tk.Toplevel()
        desk.geometry("{}x{}".format(disp.window_width, int(disp.window_height * 0.8)))
        desk.title(f"{market} options ({currency})")
        main = tk.Frame(desk)
        main.pack(fill="both", expand="yes")
        frame = ScrollFrame(main, bg="blue", bd=0)
        tk.Label(frame, text="Calls", font=disp.bold_font).grid(
            row=0, column=0, sticky="NSEW"
        )
        tk.Label(frame, text=instrument.symbol, font=disp.bold_font).grid(
            row=0, column=1, sticky="NSEW"
        )
        tk.Label(frame, text="Puts", font=disp.bold_font).grid(
            row=0, column=2, sticky="NSEW"
        )
        frame.grid_columnconfigure(0, weight=10)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=10)
        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(1, weight=1)
        frame_calls = tk.Frame(frame)
        frame_strikes = tk.Frame(frame)
        frame_puts = tk.Frame(frame)
        frame_calls.grid(row=1, column=0, sticky="NSEW")
        frame_strikes.grid(row=1, column=1, sticky="NSEW")
        frame_puts.grid(row=1, column=2, sticky="NSEW")
        TreeTable.calls = TreeviewTable(
            frame=frame_calls,
            name="calls",
            title=var.name_calls,
            bind=OptionDesk.handler,
            size=10, 
        )
        TreeTable.strike = TreeviewTable(
            frame=frame_strikes,
            name="strikes",
            title=var.name_strikes,
            size=10,
        )
        TreeTable.calls = TreeviewTable(
            frame=frame_puts,
            name="puts",
            title=var.name_puts,
            bind=OptionDesk.handler,
            size=10,
        )
        ws = Markets[market]
        calls = ws.instrument_index[category][currency][instrument.symbol]["CALLS"]
        for symb in calls:
            option = ws.Instrument[(symb, market)]
            # line =
            print("-------", option.symbol)
            for item in option:
                print(item.name, item.value)
            values = [
                "Open",
                option.delta,
                "size",
                option.bidIv,
                option.bidPrice,
                option.markPrice,
                option.askPrice,
                option.askPrice,
                "size",
            ]
            TreeTable.calls.insert(values=values, iid=symb)
        """print("___________", calls)
        puts = ws.instrument_index[category][currency][instrument.symbol]["PUTS"]
        print("___________", puts)"""

    def handler():
        pass
