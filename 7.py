import random
import platform
import time
import tkinter as tk
from datetime import datetime

class Variables:
    title_color = "gray83"
    bg_color = "gray98"


class Table(Variables):
    """
    The table contains a grid with one row in each column in which a Listbox 
    is inserted. The contents of table rows are managed through Listbox tools 
    in accordance with the row index.
    """

    def __init__(self, frame, title: list, height: int):
        self.title = title
        self.count = 0
        self.listboxes = []
        #frame.grid_columnconfigure(0, weight=1)
        #frame.grid_rowconfigure(0, weight=1)
        '''canvas = tk.Canvas(frame, highlightthickness=0, bg="red")
        scroll = tk.Scrollbar(frame, orient="vertical")
        scroll.pack(side="right", fill="y")
        scroll.config(command=canvas.yview)
        canvas.config(yscrollcommand=scroll.set)
        canvas.pack(fill="both", expand=True)'''
        self.sub = tk.Frame(frame)
        self.sub.pack(fill="both", expand=True) 
        '''id = canvas.create_window((0, 0), window=self.sub, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event, id=id, can=canvas: event_width(event, id, can),
        )
        self.sub.bind(
            "<Configure>", lambda event, can=canvas: event_config(event, can)
        )
        canvas.bind(
            "<Enter>", lambda event, canvas=canvas: on_enter(event, canvas)
        )
        canvas.bind(
            "<Leave>", lambda event, canvas=canvas: on_leave(event, canvas)
        )'''
        for column, name in enumerate(title):
            vars = tk.Variable(value=[name,])
            self.listboxes.append(
                tk.Listbox(
                    self.sub,
                    listvariable=vars,
                    bd=0,
                    highlightthickness=0,
                    selectbackground=self.title_color,
                    selectforeground="Black",
                    activestyle="none",
                    justify='center',
                    #height=height,
                    #selectmode=tk.SINGLE,
                )
            )
            self.listboxes[column].config(width=0)
            #self.listboxes[column].grid(row=0, column=column, sticky="N" + "S" + "W" + "E")
            self.listboxes[column].pack(fill="both", expand=True) 
            #self.sub.grid_columnconfigure(column, weight=1)
            #self.sub.grid_rowconfigure(0, weight=1)

    def add_line(self, elements: list, row: int):
        self.count += 1
        for column, listbox in enumerate(self.listboxes):
            text = str(column) + "_" + str(self.count) + "_" + str(self.count)
            listbox.insert(row, text)

    def on_closing(self, root, refresh_var):
        root.after_cancel(refresh_var)
        root.destroy()

def event_width(event, canvas_id, canvas_event):
    canvas_event.itemconfig(canvas_id, width=event.width)


def event_config(event, canvas_event):
    canvas_event.configure(scrollregion=canvas_event.bbox("all"))


def on_enter(event, canvas_event):
    if platform.system() == "Linux":
        canvas_event.bind_all(
            "<Button-4>",
            lambda event, canvas=canvas_event: robots_on_mousewheel(event, canvas),
        )
        canvas_event.bind_all(
            "<Button-5>",
            lambda event, canvas=canvas_event: robots_on_mousewheel(event, canvas),
        )
    else:
        canvas_event.bind_all(
            "<MouseWheel>",
            lambda event, canvas=canvas_event: robots_on_mousewheel(event, canvas),
        )


def on_leave(event, canvas_event):
    if platform.system() == "Linux":
        canvas_event.unbind_all("<Button-4>")
        canvas_event.unbind_all("<Button-5>")
    else:
        canvas_event.unbind_all("<MouseWheel>")

def robots_on_mousewheel(event, canvas_event):
    if platform.system() == "Windows":
        canvas_event.yview_scroll(int(-1 * (event.delta / 120)), "units")
    elif platform.system() == "Darwin":
        canvas_event.yview_scroll(int(-1 * event.delta), "units")
    else:
        if event.num == 4:
            canvas_event.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas_event.yview_scroll(1, "units")

def fill():
    for _ in range(90):
        lst = []
        for num in range(len(my_app.title)):
            lst.append(str(num) * 5)
        my_app.add_line(lst, row=1)


def refresh():
    '''lst = []
    for num in range(len(my_app.title)):
        lst.append(str(num) * 5 + "_**")'''
    #my_app.add_line(lst)
    root.after(1, refresh)


if __name__ == "__main__":
    root = tk.Tk()
    name_robots = [
    "EMI",
    ]
    '''"SYMB",
    "CURRENCY",
    "TIMEFR",
    "CAPITAL",
    "STATUS",
    "VOL",
    "PNL",
    "POS",
    ]'''
    my_app = Table(root, title=name_robots, height=80)
    fill()
    refresh_var = root.after_idle(refresh)
    root.protocol(
        "WM_DELETE_WINDOW",
        lambda root=root, refresh_var=refresh_var: my_app.on_closing(root, refresh_var),
    )
    root.mainloop()
