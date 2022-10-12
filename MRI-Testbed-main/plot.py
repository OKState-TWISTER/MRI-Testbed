import matplotlib.pyplot as plt
import numpy
import os

from utils import deg_to_rad, to_log

class Custom_Plot:
    def __init__(self, description, mode, save_dir, dest_filename):
        self.mode = mode
        self.save_dir = save_dir
        self.dest_filename = dest_filename

        self.data = [[],[]]
        plt.ion()

        self.fig = plt.figure()
        self.axis = self.fig.add_subplot(111, polar=True)
        self.axis.set_theta_zero_location("N")
        (self.line,) = self.axis.plot([],[])
        self.label_position = self.axis.get_rlabel_position()
        
        title = "BER (log10) " if mode == "ber" else "Received Power "
        self.axis.set_title(title + str(description))

        units = "errors" if mode == "ber" else "dB"
        self.text = self.axis.text(
            numpy.radians(self.label_position),
            2,
            units,
            rotation=self.label_position,
            ha="center",
            va="center",
        )
        

    def update(self, data):
        self.data = data
        angle_data, r_data = data
        theta = deg_to_rad(angle_data)

        
        r = to_log(r_data) if self.mode == "ber" else r_data
        
        self.line.set_xdata(theta)
        self.line.set_ydata(r)

        self.text.set(position=(numpy.radians(self.label_position), max(r) + 1))

        self.axis.set_ylim(min(r), max(r))
        # recompute the axis.dataLim
        self.axis.relim()
        # update ax.viewLim using the new dataLim
        self.axis.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def print_report(self):
        unit = "dBm" if self.mode == "cw" else "errors"
        self.fig.savefig(
            os.path.join(self.save_dir, self.dest_filename + ".png")
        )
        print(f"Max value: {max(self.data[1])} {unit}")


if __name__ == '__main__':
    from random import randint
    from time import sleep

    size = 10
 
    plot = Custom_Plot("test description", "ber", "trash", "trash")

    data = [[], []]

    for i in range(size):
        data[0].append(i)
        datapoint = randint(-20, -2)
        print(f"new datapoint: '{datapoint}'")
        data[1].append(datapoint)

        plot.update(data)
        sleep(.5)

    input()