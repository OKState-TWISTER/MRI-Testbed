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
import time

import matlab.engine

# from utils import *


class WaveformProcessor:
    def __init__(self, org_waveform=None):
        print("Initializing MATLAB engine")
        start = time.time()
        self.eng = matlab.engine.start_matlab()
        end = time.time()
        print(f"Done. Took {end - start} seconds.")

        wf_struct = self.load_qam_waveform(org_waveform)["original"]
        self.mod_order = wf_struct["modulation_order"]
        self.block_length = wf_struct["block_length"]
        self.org_samples = wf_struct["samples"]
        self.sym_rate = wf_struct["symbol_rate"]
        self.rcf_rolloff = wf_struct["rcf_rolloff"]

        self.if_estimate = 4e9
        self.sym2drop = 300.0

    def load_qam_waveform(self, filepath=None):
        while filepath is None:
            file = input("Enter original waveform filename: ")
            file = os.path.normpath(file)
            if os.path.isfile(file):
                filepath = file
                break
            else:
                print("Please enter a valid filename")

        return self.eng.load(filepath)

    def process_qam(self, samp_rate, samples):
        start = time.time()
        print("Begin processing waveform")
        # function [data, nsym, errors, SNR] = processQAM(mod_order, block_length, sym_rate, IF_estimate, symbols_to_drop, rcf_rolloff, original_samples, samp_rate, captured_samples, diagnostics_on)
        (data, nsym, errors, SNR) = self.eng.processQAM(self.mod_order, self.block_length, self.sym_rate, self.if_estimate,
                                                        self.sym2drop, self.rcf_rolloff, self.org_samples, samp_rate, samples, 1, nargout=4)
        end = time.time()
        print(f"Done. Took {end - start} seconds.")

        # Theoretical SER for the calculated SNR, ASSUMING GAUSSIAN NOISE.
        # The assumption of Gaussian noise may not always be correct, so verify.
        # NOTE:  For QPSK only.
        # SER_theory = erfc(sqrt(0.5*(10.^(SNR/10)))) - (1/4)*(erfc(sqrt(0.5*(10.^(SNR/10))))).^2; # original
        SER_theory = self.eng.erfc(math.sqrt(0.5 * (10 ** (SNR / 10)))) - (1 / 4) * (self.eng.erfc(math.sqrt(0.5 * (10 ** (SNR / 10))))) ** 2

        # print results TODO: clean up
        print(f"\nAnalyzing {nsym} symbols:\n")
        print(f"SNR is {SNR} dB\n")
        bits = errors["bit"]
        biterr = bits / (nsym * math.log2(self.mod_order))
        print(f"Observed BER is {biterr} ({bits} bits)\n")
        syms = errors["sym"]
        symerr = syms / nsym
        print(f"Observed SER is {symerr} ({syms} symbols)\n")
        # For QPSK only:
        print(f"Predicted QPSK SER is {SER_theory} ({round(SER_theory*nsym)} symbols)\n")

        return biterr


if __name__ == '__main__':
    from scope_control import Infiniium

    #visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"
    #scope = Infiniium(visa_address, False)

    proc = WaveformProcessor("smallflag.mat")


    #waveform = scope.get_waveform_words()
    #samp_rate = scope.get_sample_rate()

    import pickle
    with open('saved_waveform.pkl', 'rb') as inp:
        waveform = pickle.load(inp)
        samp_rate = pickle.load(inp)


    print("test")

    #proc.eng.double(waveform)
    proc.process_qam(samp_rate, waveform)


#import pickle
    #with open('saved_waveform.pkl', 'wb') as outp:
    #    pickle.dump(waveform, outp, pickle.HIGHEST_PROTOCOL)
    #    pickle.dump(samp_rate, outp, pickle.HIGHEST_PROTOCOL)