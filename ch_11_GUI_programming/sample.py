import tkinter
from tkinter import messagebox

def Click():
    reply = messagebox.askquestion("Confirmation", "Are you sure you want to exit?")
    if reply == 'yes':
        skylight.quit()

skylight = tkinter.Tk()
skylight.title("Skylight")
skylight.geometry("400x300")
skylight.configure(bg="lightblue")
button = tkinter.Button(skylight, text='Bye!', command=Click)
button.place(x=100, y=100)
skylight.mainloop()