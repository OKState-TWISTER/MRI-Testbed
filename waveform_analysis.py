"""
This module handles processing of waveforms captured by the DSO.
Matlab functions are called via the matlab engine for python.

Requires:
- MATLAB Engine API for Python: https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html
References:
https://www.mathworks.com/help/matlab/matlab_external/call-user-script-and-function-from-python.html
"""

import math
import os
import sys
from time import time

import matlab.engine

# from utils import *


class WaveformProcessor:
    def __init__(self, debug=False, org_waveform=None):
        self.debug = debug

        print("Initializing MATLAB engine")
        start = time()
        self.eng = matlab.engine.start_matlab()
        end = time()
        print(f"Done. Took {end - start} seconds.")

        wf_struct = self.load_qam_waveform(org_waveform)
        self.mod_order = wf_struct["modulation_order"]
        self.block_length = wf_struct["block_length"]
        self.org_samples = wf_struct["samples"]
        self.sym_rate = wf_struct["symbol_rate"]
        self.rcf_rolloff = wf_struct["rcf_rolloff"]

        self.if_estimate = 1.64e9
        self.sym2drop = 300.0

    def load_qam_waveform(self, filepath=None):
        while filepath is None:
            print()
            files = [file for file in os.listdir() if file.endswith(".mat")]
            for idx, filename in enumerate(files):
                print(f"{idx}: {filename}")

            index = int(input("Choose original waveform filename (enter number): "))
            try:
                filepath = files[index]
            except IndexError:
                print("Please enter a valid choice")
                continue

        print(f"Loading waveform file '{filepath}'")

        struct = self.eng.load(filepath)
        try:
            wf_struct = struct["original"]
        except KeyError:
            print(f"\nError: no field named \"original\" in file {filepath}")
            sys.exit(-1)
        return wf_struct

    def process_qam(self, samp_rate, captured_samples):
        start = time()
        print("Begin processing waveform")

        # function [data, nsym, errors, SNR] = processQAM(mod_order, block_length, sym_rate, IF_estimate, symbols_to_drop, rcf_rolloff, original_samples, samp_rate, captured_samples, diagnostics_on)
        mod_order = matlab.double(self.mod_order)
        block_length = matlab.double(self.block_length)
        symbol_rate = matlab.double(self.sym_rate)
        if_estimate = matlab.double(self.if_estimate)
        sym2drop = matlab.double(self.sym2drop)
        rcf_rolloff = matlab.double(self.rcf_rolloff)
        original_samples = self.org_samples
        captured_samples = matlab.double(captured_samples)

        samp_rate = matlab.double(samp_rate)
        print(len(samp_rate))
        print(type(samp_rate))

        print(len(captured_samples))
        print(type(captured_samples))

        data, nsym, errors, SNR = self.eng.processQAM(mod_order, block_length, symbol_rate, if_estimate,
                                                      sym2drop, rcf_rolloff, original_samples,
                                                      samp_rate, captured_samples, self.debug, nargout=4)

        end = time()
        if self.debug:
            print(f"Done. Took {end - start} seconds.")

        # Theoretical SER for the calculated SNR, ASSUMING GAUSSIAN NOISE.
        # The assumption of Gaussian noise may not always be correct, so verify.
        # NOTE:  For QPSK only.
        # SER_theory = erfc(sqrt(0.5*(10.^(SNR/10)))) - (1/4)*(erfc(sqrt(0.5*(10.^(SNR/10))))).^2; # original
        SER_theory = self.eng.erfc(math.sqrt(0.5 * (10 ** (SNR / 10)))) - (1 / 4) * (self.eng.erfc(math.sqrt(0.5 * (10 ** (SNR / 10))))) ** 2

        bits = errors["bit"]
        biterr = bits / (nsym * math.log2(self.mod_order))
        syms = errors["sym"]
        symerr = syms / nsym

        if self.debug:
            print(f"\nAnalyzing {nsym} symbols:\n")
            print(f"SNR is {SNR} dB\n")
            print(f"Observed BER is {biterr} ({bits} bits)\n")
            print(f"Observed SER is {symerr} ({syms} symbols)\n")
            # For QPSK only:
            print(f"Predicted QPSK SER is {SER_theory} ({round(SER_theory*nsym)} symbols)\n")

        return biterr


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import pickle

    captured_waveform_filename = ""  # this is the python object file (.pkl)

    with open(captured_waveform_filename, 'rb') as inp:
        waveform = pickle.load(inp)
        samp_rate = pickle.load(inp)
        original_waveform_filename = pickle.load(inp)

    proc = WaveformProcessor(True, original_waveform_filename)

    plt.figure(1)
    plt.plot(waveform)
    plt.title("capturer waveform")

    proc.process_qam(samp_rate, waveform)
    input()

#import pickle
    #with open('saved_waveform.pkl', 'wb') as outp:
    #    pickle.dump(waveform, outp, pickle.HIGHEST_PROTOCOL)
    #    pickle.dump(samp_rate, outp, pickle.HIGHEST_PROTOCOL)