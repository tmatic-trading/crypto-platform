import tkinter as tk

from .variables import Variables as disp

label_robots = tk.Label(disp.menu_robots, text="Robots Menu")
label_robots.pack()
label_robots_dev = tk.Label(
    disp.menu_robots, text="This page is under development", fg="red"
)
label_robots_dev.pack()
robots_button_back = tk.Button(
    disp.menu_robots,
    bg=disp.bg_select_color,
    text="Back",
    command=lambda: disp.back_to_main(),
)
robots_button_back.pack()
