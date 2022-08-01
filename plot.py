
import matplotlib.pyplot as plt
import numpy
import os

from utils import deg_to_rad, normalize_power

class Custom_Plot:
    def __init__(self, description, mode, save_dir, dest_filename):
        self.mode = mode
        self.save_dir = save_dir
        self.dest_filename = dest_filename
        self.data = []
        plt.ion()
        self.fig = plt.figure(figsize=(8, 8))
        self.axis = plt.subplot(111, polar=True)
        self.axis.set_theta_zero_location("N")
        (self.line,) = self.axis.plot([], [])
        label_position = self.axis.get_rlabel_position()

        units = "magical BER units" if mode == "ser" else "dB"
        self.axis.text( #  Why doesn't this do anything
            numpy.radians(label_position),
            2,
            units,
            rotation=label_position,
            ha="center",
            va="center",
        )
        self.axis.set_title(description)

    def update(self, data):
        self.data = data
        angle_data, r_data = data
        theta = deg_to_rad(angle_data)

        if self.mode == "ser":
            r = r_data
        else:
            # should probably correct R axis values (axis.set_yticks)
            r = normalize_power(r_data)
        
        self.line.set_xdata(theta)
        self.line.set_ydata(r)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def print_report(self):
        self.fig.savefig(
            os.path.join(self.save_dir, self.dest_filename + ".png")
        )
        print(f"Max value: {max(self.data[1])} dBm")


if __name__ == '__main__':
    from random import random
    from time import sleep

    size = 10
 
    plot = Custom_Plot("test description", "amplitude", "trash", "trash")

    data = [[], []]

    for i in numpy.linspace(-5, 5, size):
        data[0].append(i)
        data[1].append(random())

        plot.update(data)
        sleep(.1)

    input()