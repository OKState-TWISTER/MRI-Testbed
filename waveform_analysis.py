"""
This module handles processing of waveforms captured by the DSO.
Matlab functions are called via the matlab engine for python.

Requires:
- MATLAB Engine API for Python: https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html
References:
https://www.mathworks.com/help/matlab/matlab_external/call-user-script-and-function-from-python.html
"""

import math
from multiprocessing.sharedctypes import Value
import os
import sys
from time import perf_counter as time

import matlab.engine

# from utils import *


class WaveformProcessor:
    def __init__(self, if_estimate=None, debug=False, org_waveform=None):
        self.debug = debug
        self.diagnostics = False

        print("Initializing MATLAB engine")
        start = time()
        self.eng = matlab.engine.start_matlab()
        end = time()
        print(f"Done. Took {end - start} seconds.")

        wf_struct, self.original_waveform = self.load_qam_waveform(org_waveform)
        self.mod_order = wf_struct["modulation_order"]
        self.block_length = wf_struct["block_length"]
        self.org_samples = wf_struct["samples"]
        self.sym_rate = wf_struct["symbol_rate"]
        self.rcf_rolloff = wf_struct["rcf_rolloff"]

        # measured waveform center freq estimate
        self.if_estimate = if_estimate
        # throw away symbols corrupted by filter/PLL initilization
        self.sym2drop = 600.0

    def load_qam_waveform(self, filepath=None):
        while filepath is None:
            print()
            files = [file for file in os.listdir() if file.endswith(".mat")]
            if not files:
                print("Error: No valid source (.mat) files found. Exiting.")
                raise FileNotFoundError("Error: No valid source (.mat) files found. Exiting.")
            for idx, filename in enumerate(files):
                print(f"{idx}: {filename}")

            try:
                index = int(input("Choose original waveform filename (enter number): "))
                filepath = files[index]
            except ValueError:
                print("Please enter a value")
            except IndexError:
                print("Please enter a valid choice")
            finally:
                continue

        if self.debug:
            print(f"Loading waveform file '{filepath}'")

        if not os.path.isfile(filepath):
            print(f"Error loading file {filepath}. File does not exist.")
            raise FileNotFoundError(f"Error loading file {filepath}. File does not exist.")

        try:
            struct = self.eng.load(filepath)
            wf_struct = struct["original"]
        except KeyError:
            print(f"\nError: no field named \"original\" in file {filepath}")
            raise ValueError(f"\nError: no field named \"original\" in file {filepath}")
        except Exception as e:
            print(f"\nError loading file '{filepath}'\n{e}\n")
            raise IOError(f"\nError loading file '{filepath}'\n{e}\n")
        
        return (wf_struct, filepath)

    def process_qam(self, samp_rate, captured_samples):
        start = time()
        if self.debug:
            print("Begin processing waveform")

        #captured_samples = [float(dat) for dat in captured_samples]

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

        data, nsym, errors, SNR = self.eng.processQAM(mod_order, block_length, symbol_rate, if_estimate,
                                                      sym2drop, rcf_rolloff, original_samples, samp_rate, 
                                                      captured_samples, self.debug, self.diagnostics, nargout=4)

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

        # SNR, nbits, biterr, nsyms, symerr
        return (SNR, (nsym * math.log2(self.mod_order)), biterr, nsym, symerr)


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from fileio import File_IO

    # this is where waveform files are located
    waveform_dir = r"C:\Users\UTOL\Desktop\MRI-Testbed\Data\mendis_data_variable_span\bpsk_75mm_2022-08-18T1527_waveforms"
    if_estimate = 7e9

    fileio = File_IO(waveform_dir)

    proc = WaveformProcessor(if_estimate=if_estimate, debug=True)

    for filename in os.listdir(waveform_dir):
        path = os.path.join(waveform_dir, filename)

        (samp_rate, samp_count, samples) = fileio.load_waveform(path)
        
        plt.figure(1)
        plt.plot(samples[:500])
        plt.title("captured waveform (first 500 samples)")

        proc.process_qam(samp_rate, samples)

        break

    input()

#import pickle
    #with open('saved_waveform.pkl', 'wb') as outp:
    #    pickle.dump(waveform, outp, pickle.HIGHEST_PROTOCOL)
    #    pickle.dump(samp_rate, outp, pickle.HIGHEST_PROTOCOL)