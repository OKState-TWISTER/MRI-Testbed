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
from time import perf_counter as time

import matlab.engine

# from utils import *


class WaveformProcessor:
    def __init__(self, debug=False):
        self.debug = debug
        self.diagnostics = True

        print("Initializing MATLAB engine")
        start = time()
        self.eng = matlab.engine.start_matlab()
        end = time()
        print(f"Done. Took {end - start} seconds.")



    def load_qam_waveform(self, filepath):
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
        
        self.mod_order = wf_struct["modulation_order"]
        self.block_length = wf_struct["block_length"]
        self.org_samples = wf_struct["samples"]
        self.sym_rate = wf_struct["symbol_rate"]
        self.rcf_rolloff = wf_struct["rcf_rolloff"]
        self.if_estimate = wf_struct["fc"]
        # throw away symbols corrupted by filter/PLL initilization
        self.sym2drop = 1000



    def process_qam(self, samp_rate, captured_samples):
        """Returns: (SNR_raw, SNR_est, nbits, biterr, nsyms, symerr)"""

        start = time()
        if self.debug:
            print("Begin processing waveform")

        # function [data, nsym, errors, SNR] = processQAM(M, block_length, symbol_rate, fc, symbols_to_drop, rcf_rolloff, original_sample_frame, rate_samp, captured_samples, debug, diagnostics_on)
        mod_order = matlab.double(self.mod_order)
        block_length = matlab.double(self.block_length)
        symbol_rate = matlab.double(self.sym_rate)
        if_estimate = matlab.double(self.if_estimate)
        sym2drop = matlab.double(self.sym2drop)
        rcf_rolloff = matlab.double(self.rcf_rolloff)
        original_samples = self.org_samples
        captured_samples = matlab.double(captured_samples)

        samp_rate = matlab.double(samp_rate)

        data, nsym, errors, SNR_est, SNR_raw = self.eng.processQAM2(mod_order, block_length, symbol_rate, if_estimate,
                                                      sym2drop, rcf_rolloff, original_samples, samp_rate, 
                                                      captured_samples, self.debug, self.diagnostics, nargout=5)

        end = time()
        if self.debug:
            print(f"Done. Took {end - start} seconds.")

        # Theoretical SER for the calculated SNR, ASSUMING GAUSSIAN NOISE.
        # The assumption of Gaussian noise may not always be correct, so verify.
        # NOTE:  For QPSK only.
        # SER_theory = erfc(sqrt(0.5*(10.^(SNR/10)))) - (1/4)*(erfc(sqrt(0.5*(10.^(SNR/10))))).^2; # original
        SER_theory = self.eng.erfc(math.sqrt(0.5 * (10 ** (SNR_est / 10)))) - (1 / 4) * (self.eng.erfc(math.sqrt(0.5 * (10 ** (SNR_est / 10))))) ** 2

        n_bit_errors = errors["bit"]
        BER = n_bit_errors / (nsym * math.log2(self.mod_order))
        n_sym_errors = errors["sym"]
        SER = n_sym_errors / nsym

        if self.debug:
            print(f"\nAnalyzing {nsym} symbols:\n")
            print(f"Raw SNR is {SNR_raw} dB\n")
            print(f"Estimated SNR is {SNR_est} dB\n")
            print(f"Observed BER is {BER} ({n_bit_errors} bits)\n")
            print(f"Observed SER is {SER} ({n_sym_errors} symbols)\n")
            # For QPSK only:
            # print(f"Predicted QPSK SER is {SER_theory} ({round(SER_theory*nsym)} symbols)\n")

        # SNR, nbits, biterr, nsyms, symerr
        return (SNR_raw, SNR_est, (nsym * math.log2(self.mod_order)), n_bit_errors, nsym, n_sym_errors)
