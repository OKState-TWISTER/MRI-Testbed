# v1.1

# This program serves to automatically profile VDI modules by controlling various components:
## A Thorlabs HDR50 rotator stage connected to a BSC201 controller positions the TX antenna
##  - The stage is controlled using the Thorlabs provided .NET libraries via the pythonnet package
## A Keysight DSOV254A oscilloscope captures received waveforms
##  - The oscilloscope is controlled using the VISA standard via the pyvisa package
## The captured waveforms are analyzed using various MATLAB code
##   - Data is send to matlab via the matlab engine for python

# Requires:
# pythonnet, pyvisa (install with pip)
# MATLAB Engine API for Python: https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html
# KeySight IOLS: https://www.keysight.com/zz/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html
# Thorlabs Kinesis ~
# (all relevant .dlls should be included in this repo)


## TODO:
# control speed of rotator
# add test cataegory for data sorting

# import libraries
import atexit
import csv
import datetime
import math
import matlab.engine
import matplotlib.pyplot as plot
import numpy
import os
import pathlib
import pickle
import sys
import time

from stage_control import Kinesis
from scope_control import Infiniium

################################################################################################
################################################################################################

# Global Variables
serial_num = "40163084"
visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"

date_time = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
output_dir = "Data"
#destination_filename = f"300ghz_data_test4.1-{date_time}.csv"


starting_angle = 20  # where the test should begin (positive)
ending_angle = -20 # where the test should end (negative probably)
step_size = .05  # how many degrees between each sample point
averaging_time = 0.5  # how long to wait for DSO to average before recording value
zero_offset = 0  # stage position that results in 0 degree actual angle for DUT (DO NOT CHANGE)

debug = True

# Do not change
test_duration = (starting_angle - ending_angle) / step_size * averaging_time / 60 # minutes

def main():
    # TODO: check destination filename

    # Initialize DSO (scope_contro.py)
    scope = Infiniium(visa_address, debug)

    # Initialize rotation stage (stage_control.py)
    stage = Kinesis(serial_num, debug, starting_angle, zero_offset)

    # Initialize MATLAB engine
    #mle = Matlab_Engine()


    settings = UI() # prompt user for settings
    global save_dir
    save_dir = os.path.join(output_dir,os.path.normpath(settings.test_series))
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    global destination_filename
    destination_filename = f"{settings.desc}-{date_time}.csv"
    # todo number data files


    if not stage.home():
        print("Error when homing stage")
        if not debug:
            sys.exit(-1)
        input("Program paused. Check stage then press any key to continue")  
    else:
        print(f"Test will take {test_duration} minutes to complete.")
        input("Press any key to begin")

    # Reset averaging
    scope.do_command(":CDISplay")
    data = [[], []]
    plot = Custom_Plot(settings.desc)
    current_pos = stage.get_angle()
    try:
        while current_pos > ending_angle:
            print(f"Stage position: {current_pos} (absolute) {current_pos - zero_offset} (effective)")
            time.sleep(averaging_time)

            power = scope.get_fft_peak()
            print(f"Power level: {power} dBm")

            data[0].append(current_pos - zero_offset)
            data[1].append(power)

            #var = scope.get_waveform()
            
            plot.update(data)

            # TODO: make sure peak is at correct frequency

            print("Stage is moving")
            # Be very careful when moving the stage to not wrap coax
            stage.move_to(current_pos - step_size)
            current_pos = stage.get_angle()
            if current_pos > starting_angle:
                current_pos = current_pos - 360

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        if not debug:
            sys.exit(-1)

    data_dest = os.path.join(save_dir,destination_filename)
    print(f"writing data to {data_dest}")
    with open(data_dest, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        for i in range(len(data[0])):
            row = (data[0][i], data[1][i])
            csvwriter.writerow(row)
    print("Test complete.")


################################################################################################
################################################################################################


def deg_to_rad(deg_data):
    rad_pos = []
    for angle in deg_data:
        rad_pos.append(angle * (math.pi / 180))
    return rad_pos


def normalize_power(power_data):
    pmax = max(power_data)
    power_rat = []
    for p in power_data:
        powernorm = p - pmax  # normalize max power to 0dB
        prat = 10 ** (powernorm / 20)  # convert dB to ratio
        power_rat.append(prat)
    return power_rat


class Custom_Plot:
    def __init__(self, description):
        self.data = []
        plot.ion()
        self.fig = plot.figure(figsize=(8,8))
        self.axis = plot.subplot(111, polar=True)
        self.axis.set_theta_zero_location("N")
        self.line, = self.axis.plot([],[])
        label_position = self.axis.get_rlabel_position()
        self.axis.text(
            numpy.radians(label_position),
            2,
            "dB",
            rotation=label_position,
            ha="center",
            va="center",
        )
        #self.axis.set_yticks(range(-24, 6, 6))
        self.axis.set_title(description)
        atexit.register(self.print_report)

    def update(self, data):
        self.data = data
        pos_data, power_data = data
        theta = deg_to_rad(pos_data)
        r = normalize_power(power_data)

        self.line.set_xdata(theta)
        self.line.set_ydata(r)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def print_report(self):
        self.fig.savefig(os.path.join(save_dir,destination_filename.replace(".csv", ".png")))
        #print(f"Max value: {max(self.data[1])} dBm")

        input("Press any key to exit")



class UI:
    def __init__(self):
        self.desc = None
        self.test_series = None
        self.settings_file = os.path.join(pathlib.Path(__file__).parent.absolute(),"settings.pkl")
        print(f"pwd: {self.settings_file}")
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "rb") as inp:
                    self.test_series = pickle.load(inp)
            except:
                pass
        self.get_input()

        atexit.register(self.save)

    def get_input(self):
        while True:
            new_ts = input(f"Enter name of test series or press enter to use last series ({self.test_series}): ")
            if new_ts:
                print(f"new input: {new_ts}")
                self.test_series = new_ts
            if self.test_series is not None:
                break

        while self.desc is None:
            desc = input(f"Enter description for test: ")
            if desc:
                print(f"new description: {desc}")
                self.desc = desc

    def save(self):
        with open(self.settings_file, 'wb') as outp:
            pickle.dump(self.test_series, outp, pickle.HIGHEST_PROTOCOL)


main()
