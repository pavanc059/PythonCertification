# Placeholder for UI widgets
# import tkinter as tk

# window = tk.Tk()
# button_1 = tk.Button(window, text="Button #1")
# button_2 = tk.Button(window, text="Button #2")
# button_3 = tk.Button(window, text="Button #3")
# button_1.place(x=10, y=10, width=100, height=50)
# button_2.place(x=20, y=40)
# button_3.place(x=30, y=70)
# window.mainloop()

# Grid Layout Manager
# import tkinter as tk

# window = tk.Tk()
# button_1 = tk.Button(window, text="Button #1")
# button_2 = tk.Button(window, text="Button #2")
# button_3 = tk.Button(window, text="Button #3")
# button_1.grid(row=0, column=0)
# button_2.grid(row=1, column=1)
# #button_3.grid(row=2, column=2)
# button_3.grid(row=2, column=0, columnspan=2)
# window.mainloop()

# Pack Layout Manager
# import tkinter as tk


# window = tk.Tk()
# button_1 = tk.Button(window, text="Button #1")
# button_2 = tk.Button(window, text="Button #2")
# button_3 = tk.Button(window, text="Button #3")
# button_1.pack(side=tk.RIGHT)
# button_2.pack(side=tk.BOTTOM)
# button_3.pack(side=tk.BOTTOM)
# window.mainloop()

# Colors and Fonts
import tkinter as tk

window = tk.Tk()
button = tk.Button(window, text="Button #1", bg="#9370DB", fg="#FFA07A", activeforeground ="blue", activebackground="green")
button.pack()
window.mainloop()
#bg="#9370DB",    fg="#FFA07A",