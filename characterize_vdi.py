# v2.2b1

"""
This program serves to automatically profile VDI modules by controlling various components:
A Thorlabs HDR50 rotator stage connected to a BSC201 controller positions the TX antenna
A Keysight DSOV254A oscilloscope captures received waveforms
The captured waveforms are analyzed using various MATLAB functions
"""

# TODO:
# control speed of rotator

# import libraries
import csv
import datetime
import os
import sys
import time

import matplotlib.pyplot as plot
import numpy
import pickle

from utils import deg_to_rad, normalize_power
from stage_control import Kinesis
from scope_control import Infiniium
from user_interface import IO
from waveform_analysis import WaveformProcessor


# Global Variables
serial_num = "40163084"  # Serial number for rotation stage
visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"  # VISA address for DSO

date_time = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
output_dir = "Data"

BER_test = True  # Set to 'False' to take simple signal amplitude measurements

# Various mode controls
debug = False  # prints a whole lot of debug info
processor_debug = True  # performs a single shot measurement (ignores rotation stage), dumps waveform to file


def main():
    settings = IO(debug)  # prompt user for settings

    global save_dir
    save_dir = os.path.join(output_dir, os.path.normpath(settings.test_series()))
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    global destination_filename
    destination_filename = f"{settings.desc}-{date_time}"

    starting_angle = float(settings.starting_pos())
    ending_angle = float(settings.ending_pos())
    step_size = float(settings.step_size())
    averaging_time = float(settings.averaging_time())
    zero_offset = float(settings.zero_offset())
    mode = settings.mode()

    # Initialize DSO (scope_control.py)
    scope = Infiniium(visa_address, debug)

    if not processor_debug:
        # Initialize rotation stage (stage_control.py)
        stage = Kinesis(serial_num, debug, starting_angle, zero_offset)

    if mode == "ser":
        # Initialize MATLAB Engine (waveform analysis.py)
        waveform_proc = WaveformProcessor(debug=True)

    if not processor_debug:
        if not stage.home():
            print("Error when homing stage")
            sys.exit(-1)

        test_length = (starting_angle - ending_angle) / step_size * averaging_time / 60
        print(f"Test will take {test_length} minutes to complete.")

    input("Press any key to begin")

    # Reset averaging
    scope.do_command(":CDISplay")
    try:
        if not processor_debug:
            plot = Custom_Plot(settings.desc)
            current_pos = stage.get_angle()
            data = [[], []]

            while current_pos > ending_angle:
                print(f"Stage position: {current_pos} (absolute) {current_pos - zero_offset} (effective)")

                if mode == "amplitude":
                    datapoint = measure_amplitude(scope, averaging_time)
                elif mode == "ser":
                    datapoint = measure_ser(scope, waveform_proc)

                data[0].append(current_pos - zero_offset)
                data[1].append(datapoint)

                plot.update(data)

                print("Stage is moving")
                # Be very careful when moving the stage to not wrap coax
                stage.move_to(current_pos - step_size)
                current_pos = stage.get_angle()
                if current_pos > starting_angle:
                    current_pos = current_pos - 360

            data_dest = os.path.join(save_dir, destination_filename + ".csv")
            print(f"writing data to {data_dest}")
            with open(data_dest, "w", newline="") as csvfile:
                csvwriter = csv.writer(csvfile)
                for i in range(len(data[0])):
                    row = (data[0][i], data[1][i])
                    csvwriter.writerow(row)

            plot.print_report()

        else:  # if processor_debug mode
            if mode == "amplitude":
                measure_amplitude(scope, averaging_time, dump=True)
            elif mode == "ser":
                measure_ser(scope, waveform_proc, dump=True)

    except KeyboardInterrupt:
        pass

    print("Test complete.")


###############################################################################


def measure_amplitude(scope, averaging_time, dump=False):
    time.sleep(averaging_time)
    datapoint = scope.get_fft_peak()
    # TODO: make sure peak is at correct frequency
    print(f"Power level: {datapoint} dBm")

    if dump:
        waveform = scope.get_waveform_words()
        samp_rate = scope.get_sample_rate()
        dump_waveform(waveform, samp_rate)

    return datapoint


def measure_ser(scope, waveform_proc, dump=False):
    waveform = scope.get_waveform_words()
    waveform = [float(dat) for dat in waveform]
    samp_rate = float(scope.get_sample_rate())

    if dump:
        dump_waveform(waveform, samp_rate)

    ser = waveform_proc.process_qam(samp_rate, waveform)
    return ser


def dump_waveform(waveform, samp_rate):
    plot.figure(1)
    plot.plot(waveform[:500])
    plot.title("Waveform dump (first 500 samples)")
    # plot.show()  # TODO: change number of samples to show to a useful ammount (based on samplerate)
    # TODO: dont halt program on waveform plot

    datafile = os.path.join(save_dir, destination_filename + "_waveform.pkl")
    print(f"\nSaving {len(waveform)} samples at rate {samp_rate} smp/s to {datafile}\n")
    with open(datafile, 'wb') as outp:
        pickle.dump(waveform, outp, pickle.HIGHEST_PROTOCOL)
        pickle.dump(samp_rate, outp, pickle.HIGHEST_PROTOCOL)


class Custom_Plot:
    def __init__(self, description):
        self.data = []
        plot.ion()
        self.fig = plot.figure(figsize=(8, 8))
        self.axis = plot.subplot(111, polar=True)
        self.axis.set_theta_zero_location("N")
        (self.line,) = self.axis.plot([], [])
        label_position = self.axis.get_rlabel_position()
        self.axis.text(
            numpy.radians(label_position),
            2,
            "dB",
            rotation=label_position,
            ha="center",
            va="center",
        )
        # self.axis.set_yticks(range(-24, 6, 6))
        self.axis.set_title(description)

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
        self.fig.savefig(
            os.path.join(save_dir, destination_filename + ".png")
        )
        print(f"Max value: {max(self.data[1])} dBm")

        input("Press any key to exit")


if __name__ == '__main__':
    main()
