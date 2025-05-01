import tkinter as tk
import tkinter.messagebox as messagebox

def clicked(event=None):
    global button

    # Using widget['property'] to get the text of the button
    # state = button["text"]
    # if state == "Showing info":
    #     state = "show info"
    # else:
    #     state = "Showing info"

    if event is None:
        messagebox.showinfo("Click!", "I love clicks!")
    else:
        string = "x=" + str(event.x) + ",y=" + str(event.y) + \
                 ",num=" + str(event.num) + ",type=" + event.type
        messagebox.showinfo("Click!", string)


    state = button.cget("text")
    if state == "Showing info":
        state = "show info"
    else:
        state = "Showing info"
    button.config(text=state)

    
Window = tk.Tk()

label = tk.Label(Window, text= "Little Label:")
label.bind("<Button-1>", clicked) 
label.pack()
label_1 = tk.Label(Window, text="Quick brown fox jumps over the lazy dog")
label_1.pack()
label_2 = tk.Label(Window, text="Quick brown fox jumps over the lazy dog", font=("Times", "12"), cursor="coffee_mug")
label_2.pack()
label_3 = tk.Label(Window, text="Quick brown fox jumps over the lazy dog", font=("Arial", "16", "bold"), cursor="heart")
label_3.pack()

frame = tk.Frame(Window, width= 100, height= 30, bg= "#000099")
frame.pack()

button = tk.Button(Window, text='Show info', command=clicked)
button.pack(fill=tk.X)
button2 = tk.Button(Window, text='Close', command=Window.destroy)
button2.pack(fill=tk.X)
button2["borderwidth"] = 10
button2["highlightthickness"] = 10
button2["padx"] = 10
button2["pady"] = 5
button2["underline"] = 1
button2.config(bg ="#000000")
button2.config(fg ="yellow")
button2.config(activeforeground ="#FF0000")
button2.config(activebackground ="green")
button2["anchor"] = 'sw'
switch = tk.IntVar()
switch.set(1)

checkbutton = tk.Checkbutton(Window, text="Check Button", variable=switch)
checkbutton.pack()

entry = tk.Entry(Window, width=30)
entry.pack()


radiobutton_1 = tk.Radiobutton(Window, text="Steak", variable=switch, value=0)
radiobutton_1.pack()
radiobutton_2 = tk.Radiobutton(Window, text="Salad", variable=switch, value=1)
radiobutton_2.pack()

Window.mainloop()