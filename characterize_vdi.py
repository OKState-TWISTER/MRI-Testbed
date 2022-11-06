# v3.0b1

"""
This program serves to automatically profile VDI modules by controlling various components:
A Keysight DSOV254A oscilloscope captures received waveforms
The captured waveforms are analyzed using various MATLAB functions

Requires TWISTER Automation Library:
pip install git+https://github.com/OKState-TWISTER/TWISTER-Automation-Library
"""


import csv
import datetime
import os
import sys
import time

import matplotlib.pyplot as plt
import pickle

from oscilloscope_interface import Oscilloscope
from waveformgen_interface import WaveformGenerator
from signalgen_interface import SignalGenerator
import twister_utils

import fileio
from plot import Custom_Plot
from user_interface import UserSettings
from waveform_analysis import WaveformProcessor


# Global Variables
date_time = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%z")
output_dir = "Data"

# Various mode controls
debug = True  # prints a whole lot of debug info


def main():
    test_series = ""
    description = ""  # optional
    capture_count = 5  # number of captures to save from the scope per source waveform
    if_estimate = ""  # TODO: is this necessary to save?

    # Create save destination
    save_dir = os.path.join(output_dir, os.path.normpath(f"{test_series}_{date_time}"))
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)


    # Initialize Instruments
    scope = Oscilloscope(debug=debug)
    awg = WaveformGenerator(debug=debug)
    psg1 = SignalGenerator(1, debug=debug)
    psg2 = SignalGenerator(2, debug=debug)

    while True:
        response = input("Are the VDI modules powered on? (y/N): ")
        if response.lower() == "y":
            break
        else:
            print("Please ensure the VDI modules are powered on before enabling the LO and AWG outputs.\n")



    info_fp = os.path.join(save_dir, "info.txt")
    with open(info_fp, 'w') as file:
        file.writelines([
            f"Test Series: {test_series}\n",
            f"Description: {description}\n",
            f"# captures per waveform: {capture_count}\n",
            f"Waveform IF estimate: {if_estimate}\n",
        ])

    
    # Generate source waveforms (if option is selected)
    source_waveform_dir = os.path.join(save_dir, "source_waveforms")
    if not os.path.exists(source_waveform_dir):
        os.makedirs(source_waveform_dir)
    # for [parameter]
    # dump generated files in source_waveform_dir

    #else select path to source waveforms


    #created captured waveform directory
    captured_waveform_dir = os.path.join(save_dir, "captured_waveforms")
    if not os.path.exists(captured_waveform_dir):
        os.makedirs(captured_waveform_dir)


    #### Run the tests ####
    # Enable Signal Generators and then AWG output
    with psg1.enable_output(), psg2.enable_output(), awg.enable_output():
        for file in os.listdir(source_waveform_dir):
            if not file.endswith(".bin"):
                continue
            sourcefilepath = os.path.join(source_waveform_dir, file)
            
            awg.load_waveform(sourcefilepath, sample_rate)

            for n in range(1, capture_count+1):  # one-based index
                data = scope.get_waveform_bytes(channels=1)
                scope_sr = scope.get_sample_rate()

                outfilepath = os.path.join(captured_waveform_dir, f"{file.replace('.bin', '')}_{n}")
                fileio.save_waveform(data, scope_sr, outfilepath)


    input("Test complete.")


###############################################################################



def measure_ber(scope, waveform_proc, analyze):
    waveform = scope.get_waveform_words()
    samp_rate = float(scope.get_sample_rate())
    if debug:
        print(f"Captured sample rate: '{samp_rate}'")

    if analyze:
        (SNR, nbits, nbiterr, nsym, nsymerr) = waveform_proc.process_qam(samp_rate, waveform)
        ber = nbiterr/nbits
    else:
        ber = 0

    return (ber, waveform, samp_rate)


if __name__ == '__main__':
    main()
