# hexcolor.py

class HexColorContainer:
    def __init__(self, *args):
        self._colors = []
        for arg in args:
            self.add_color(arg[0], arg[1], arg[2])

    def add_color(self, red, green, blue):
        self._colors.append(f"#{red:02x}{green:02x}{blue:02x}")

    def __getitem__(self, key):
        return self._colors[key]

    def __len__(self):
        return len(self._colors)

    def __iter__(self):
        return self._colors.__iter__()
