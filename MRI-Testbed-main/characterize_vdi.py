# v2.7c

"""
This program serves to automatically profile VDI modules by controlling various components:
A Thorlabs HDR50 rotator stage connected to a BSC201 controller positions the TX antenna
A Keysight DSOV254A oscilloscope captures received waveforms
The captured waveforms are analyzed using various MATLAB functions
"""

# TODO:
# control speed of rotator

# import libraries
from array import array
import csv
import datetime
import os
import sys
import time

import matplotlib.pyplot as plt
import pickle

from fileio import File_IO
from plot import Custom_Plot
from stage_control import Kinesis
from scope_control import Infiniium
from user_interface import UserSettings
from waveform_analysis import WaveformProcessor


# Global Variables
serial_num = "40163084"  # Serial number for rotation stage
visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"  # VISA address for DSO

date_time = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%z")
output_dir = "Data"

# Various mode controls
debug = True  # prints a whole lot of debug info
ignore_rotator = True  # performs a single shot measurement (ignores rotation stage), dumps waveform to file


def main():
    if ignore_rotator:
        print("\nWarning: Rotation stage disabled\n")

    settings = UserSettings(debug)  # prompt user for settings

    mode = settings.mode()
    starting_angle = float(settings.starting_pos())
    ending_angle = float(settings.ending_pos())
    step_size = float(settings.step_size())
    zero_offset = float(settings.zero_offset())
    save_waveforms = settings.save_waveforms() == "true"

    # TODO: have UserSettings handle casting types
    if mode == "cw":
        averaging_time = float(settings.averaging_time())
    if mode == "ber":
        if_estimate = float(settings.if_estimate())
        if save_waveforms:
            waveform_count = int(settings.waveform_count())

    # Create save destination
    global save_dir
    save_dir = os.path.join(output_dir, os.path.normpath(settings.test_series()))
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    global destination_filename
    destination_filename = f"{settings.desc}_{date_time}"

    if save_waveforms:
        waveform_dir = os.path.join(save_dir, destination_filename + "_waveforms")
        fileio = File_IO(waveform_dir)

    # Initialize DSO (scope_control.py)
    scope = Infiniium(visa_address, debug)

    if not ignore_rotator:
        # Initialize rotation stage (stage_control.py)
        stage = Kinesis(serial_num, debug, starting_angle, zero_offset)

    if mode == "ber":
        # Initialize MATLAB Engine (waveform analysis.py)
        waveform_proc = WaveformProcessor(if_estimate=if_estimate, debug=True) #debug=not save_waveforms

    if not ignore_rotator:
        if not stage.home():
            print("Error when homing stage")
            sys.exit(-1)

    # TODO: have an updating estimation for remaining time
    #test_length = (starting_angle - ending_angle) / step_size * averaging_time / 60
    #print(f"Test will take {test_length} minutes to complete.")

    input("Press any key to begin")

    # Write test info to file
    info_fp = os.path.join(save_dir, f"{destination_filename}.info")
    with open(info_fp, 'w') as file:
        file.write(f"Description: {settings.desc}\n")
        file.write(f"Mode: {mode}\n")
        file.write(f"Rotation span: {starting_angle} - {ending_angle} degrees\n")
        file.write(f"Step size: {step_size} degrees\n")
        if mode == "cw":
            file.write(f"Averaging time: {averaging_time} seconds\n")
        if mode == "ber":
            file.write(f"# waveforms per position: {waveform_count}\n")
            file.write(f"Waveform IF estimate: {if_estimate}\n")
            file.write(f"Original waveform filename: {waveform_proc.original_waveform}\n")


    # Begin Test
    scope.do_command(":CDISplay")
    try:
        if not ignore_rotator:
            plot = Custom_Plot(settings.desc, mode, save_dir, destination_filename)
            current_pos = stage.get_rel_angle()
            data = [[], []]

            while current_pos >= ending_angle:
                print(f"Stage position: {current_pos} (absolute) {current_pos - zero_offset} (effective)")

                if mode == "cw":
                    datapoint = measure_amplitude(scope, averaging_time, save_wf=save_waveforms)
                    if save_waveforms:
                        datapoint, waveform, samp_rate = datapoint
                        fileio.save_waveform(waveform, samp_rate, current_pos, 1)
                elif mode == "ber":
                    datapoint = 0
                    n = waveform_count
                    while True:
                        (ber, waveform, samp_rate) = measure_ber(scope, waveform_proc)

                        if not save_waveforms:
                            datapoint = ber
                            break
                        else:
                            datapoint += ber
                            fileio.save_waveform(waveform, samp_rate, current_pos, n)
                            n -= 1
                            if n == 0:
                                datapoint = datapoint / waveform_count
                                break

                data[0].append(stage.get_abs_angle() - zero_offset)
                data[1].append(datapoint)

                plot.update(data)

                print("Stage is moving")
                # Be very careful when moving the stage to not wrap coax
                stage.move_to(current_pos - step_size)
                current_pos = stage.get_rel_angle()

            data_dest = os.path.join(save_dir, destination_filename + ".csv")
            print(f"writing data to {data_dest}")
            with open(data_dest, "w", newline="") as csvfile:
                csvwriter = csv.writer(csvfile)
                for i in range(len(data[0])):
                    row = (data[0][i], data[1][i])
                    csvwriter.writerow(row)

            plot.print_report()

        else:  # if ignore_rotator mode
            if mode == "cw":
                data = measure_amplitude(scope, averaging_time, save_wf=save_waveforms)
                if save_waveforms:
                    data, waveform, samp_rate = data
                    fileio.save_waveform(waveform, samp_rate, None, 1)
                
            elif mode == "ber":
                datapoint = 0
                n = waveform_count
                first = True
                while True:
                    (ber, waveform, samp_rate) = measure_ber(scope, waveform_proc, first)
                    first = False

                    if not save_waveforms:
                        datapoint = ber
                        break
                    else:
                        datapoint += ber
                        fileio.save_waveform(waveform, samp_rate, None, n)
                        n -= 1
                        if n == 0:
                            datapoint = datapoint / waveform_count
                            break
                print(f"Average BER: {datapoint}")

    except KeyboardInterrupt:
        pass

    input("Test complete.")


###############################################################################


def measure_amplitude(scope, averaging_time, save_wf=False):
    # Reset averaging
    scope.do_command(":CDISplay")
    time.sleep(averaging_time)
    datapoint = scope.get_fft_peak()
    # TODO: make sure peak is at correct frequency
    print(f"Power level: {datapoint} dBm")

    if save_wf:
        waveform = scope.get_waveform_words()
        samp_rate = scope.get_sample_rate()
        return (datapoint, waveform, samp_rate)

    return datapoint


def measure_ber(scope, waveform_proc, analyze):
    waveform = scope.get_waveform_words()
    samp_rate = float(scope.get_sample_rate())
    if debug:
        print(f"Captured sample rate: '{samp_rate}'")

    if analyze:
        ber = waveform_proc.process_qam(samp_rate, waveform)
    else:
        ber = 0

    return (ber, waveform, samp_rate)


if __name__ == '__main__':
    main()
