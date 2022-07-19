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
from time import time

import matlab.engine

# from utils import *


class WaveformProcessor:
    def __init__(self, debug, org_waveform=None):
        self.debug = debug

        print("Initializing MATLAB engine")
        start = time()
        self.eng = matlab.engine.start_matlab()
        end = time()
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

    def process_qam(self, samp_rate, captured_samples):
        start = time()
        print("Begin processing waveform")

        # function [data, nsym, errors, SNR] = processQAM(mod_order, block_length, sym_rate, IF_estimate, symbols_to_drop, rcf_rolloff, original_samples, samp_rate, captured_samples, diagnostics_on)
        mod_order = self.mod_order
        block_length = self.block_length
        symbol_rate = self.sym_rate
        if_estimate = self.if_estimate
        sym2drop = self.sym2drop
        rcf_rolloff = self.rcf_rolloff
        original_samples = self.org_samples
        captured_samples = matlab.double(captured_samples)
        
        data, nsym, errors, SNR = self.eng.processQAM(mod_order, block_length, symbol_rate, if_estimate,
                                                      sym2drop, rcf_rolloff, original_samples,
                                                      samp_rate, captured_samples, 1, nargout=4)
        
        end = time()
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

        end = time()


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    source = "visa_cap_file"

    proc = WaveformProcessor(True, "M4N5_Permutation_Sequence.mat")

    if source == "scope":
        from scope_control import Infiniium
        visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"
        scope = Infiniium(visa_address, False)
        waveform = scope.get_waveform_words()
        samp_rate = scope.get_sample_rate()

    elif source == "visa_cap_file":
        import pickle
        with open('m4n5_waveform_obj.pkl', 'rb') as inp:
            waveform = pickle.load(inp)[0::2]
            samp_rate = pickle.load(inp) / 2

    #plt.figure(1)
    #plt.plot(waveform1)
    #plt.title(f"visa (scope) capture")
        print(f"visa (scope) capture:\n{len(waveform)} samples\n{len(waveform) / samp_rate} seconds\n")

    elif source == "matlab_cap_file":
        loaded = proc.load_qam_waveform("m4n5capture.mat")["Channel_1"]
        samp_rate = 1 / loaded["XInc"]
        waveform = loaded["Data"].tomemoryview().tolist()
        waveform = [row[0] for row in waveform]#[352000:352500]


    proc.process_qam(samp_rate, waveform)
    input()

#import pickle
    #with open('saved_waveform.pkl', 'wb') as outp:
    #    pickle.dump(waveform, outp, pickle.HIGHEST_PROTOCOL)
    #    pickle.dump(samp_rate, outp, pickle.HIGHEST_PROTOCOL)