import tkinter as tk

root = tk.Tk()

# Create a canvas
canvas = tk.Canvas(root, height=200, width=300, background="lightblue")
canvas.pack()

# Create a frame
frame = tk.Frame(root, bg="red")
frame.pack(fill="both", expand=True)
lst = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
box = tk.Listbox(frame, listvariable=tk.Variable(value=lst))
box.pack(fill="both", expand=True)

# Add the frame to the canvas
canvas.create_window(50, 50, window=frame, anchor="nw")

# Add a button to the frame

#button = tk.Button(frame, text="Click me!")
#button.pack(padx = 20, pady = 20)

root.mainloop()

exit(0)


from tkinter import *
from tkinter import ttk
 
root = Tk()
root.title("METANIT.COM")
root.geometry("250x200")
 
v = ttk.Scrollbar(orient=VERTICAL)
canvas = Canvas(scrollregion=(0, 0, 1000, 1000), bg="white", yscrollcommand=v.set)
v["command"] = canvas.yview
 
canvas.grid(column=0, row=0, sticky=(N,W,E,S))
v.grid(column=1, row=0, sticky=(N,S))
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)

fr = Frame(canvas)
#fr.pack(fill="both", expand=True)

lst = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
box = Listbox(fr, listvariable=Variable(value=lst))

btn = ttk.Button(text="Click")
canvas.create_window(10, 20, anchor=NW, window=fr)
 
#canvas.create_rectangle(10,10, 300, 300, fill="red")
 
root.mainloop()