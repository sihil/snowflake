import tkinter as tk
from tkinter import ttk

class SnowflakeUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Snowflake Plotter UI")

        self.order_label = ttk.Label(root, text="Order of Rotational Symmetry:")
        self.order_label.grid(column=0, row=0, padx=10, pady=10)

        self.order_value = ttk.Label(root, text="6")
        self.order_value.grid(column=1, row=0, padx=10, pady=10)

        self.mirror_label = ttk.Label(root, text="Mirroring State:")
        self.mirror_label.grid(column=0, row=1, padx=10, pady=10)

        self.mirror_value = ttk.Label(root, text="Enabled")
        self.mirror_value.grid(column=1, row=1, padx=10, pady=10)

        self.time_left_label = ttk.Label(root, text="Time Left for Plotting:")
        self.time_left_label.grid(column=0, row=2, padx=10, pady=10)

        self.time_left_value = ttk.Label(root, text="0s")
        self.time_left_value.grid(column=1, row=2, padx=10, pady=10)

        self.order_button = ttk.Button(root, text="Change Order", command=self.change_order)
        self.order_button.grid(column=0, row=3, padx=10, pady=10)

        self.mirror_button = ttk.Button(root, text="Toggle Mirroring", command=self.toggle_mirroring)
        self.mirror_button.grid(column=1, row=3, padx=10, pady=10)

    def update_order(self, order):
        self.order_value.config(text=str(order))

    def update_mirroring(self, mirroring):
        self.mirror_value.config(text="Enabled" if mirroring else "Disabled")

    def update_time_left(self, time_left):
        self.time_left_value.config(text=f"{time_left}s")

    def change_order(self):
        # Placeholder for changing order logic
        pass

    def toggle_mirroring(self):
        # Placeholder for toggling mirroring logic
        pass

    def start_ui(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = SnowflakeUI(root)
    app.start_ui()
