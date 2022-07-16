"""
This module handles processing of waveforms captured by the DSO.
Matlab functions are called via the matlab engine for python.

Requires:
- MATLAB Engine API for Python: https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html
References:
https://www.mathworks.com/help/matlab/matlab_external/call-user-script-and-function-from-python.html
"""

import cmath
import math
import os
from time import time

import matlab.engine
import matplotlib.pyplot as plt
import numpy as np

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

        #signal, sps, time_ds = self.normalize_waveform(signal, sample_rate, symbol_rate)

        #signal = self.mixdown(signal, time_ds, f_LO)

        #signal = self.agc(signal)

        end = time()

    def normalize_waveform(self, signal, sample_rate, symbol_rate):
        if self.debug:
            start = time()
            print("Normalizing signal")

        # EXTRACT, SCALE, AND INTERPOLATE THE WAVEFORM
        # Create the time vector
        org_siglen = len(signal)
        tmin = 0
        tmax = tmin + (1 / sample_rate) * org_siglen
        time_full = np.arange(tmin, tmax, 1 / sample_rate).tolist()

        # Calculate samples per symbol, and force it do be an integer.
        # (An integer SPS is required by communication toolbox system objects)
        sps = math.floor(sample_rate / symbol_rate)
        new_sample_rate = sps * symbol_rate

        # Create downsampled time (query) vector
        time_ds = np.arange(0, tmax, 1 / new_sample_rate).tolist()

        # Downsample by interpolation
        signal = self.eng.interp1(matlab.double(time_full), matlab.double(signal), matlab.double(time_ds))[0].toarray()

        # Make the time-domain waveform zero-mean
        mean = sum(signal) / len(signal)
        signal = [(sample - mean) for sample in signal]

        # Apply a uniform gain so signal peak is unity
        max_mag = max([abs(sample) for sample in signal])
        signal = [(sample / max_mag) for sample in signal]

        # Diagnostics
        if self.debug:
            end = time()
            print(f"Done in {end - start} seconds.")
            print(f"Original samples: {org_siglen}\nDownsampled: {len(signal)}")
            # plt.plot(time_full, signal)
            # plt.show()

        return signal, sps, time_ds

    def mixdown(self, signal, time_ds, f_LO):
        if self.debug:
            start = time()
            print("Mixing signal with local oscillator")

        # MIX WITH THE LOCAL OSCILLATOR
        # signal = signal.*exp(1j*2*pi*f_LO*time)
        mixed_signal = []
        for idx, sample in enumerate(signal):
            mixed_signal.append(sample * cmath.exp(1j * 2 * math.pi * f_LO * time_ds[idx]))

        # Diagnostics
        if self.debug:
            end = time()
            print(f"Done in {end - start} seconds.")
            # figure(100); clf; hold on;
            # plot(8*signal, '.', 'MarkerSize', 5);
        
        return mixed_signal

    def agc(self, signal):
        if self.debug:
            start = time()
            print("Attempting signal smoothing")

        # AUTOMATIC GAIN CONTROL
        # Attempts to smooth out fading and hold the signal power constant
        # MATLAB system objects have to be handled differently
        self.eng.workspace["automaticGainControl"] = self.eng.comm.AGC('AdaptationStepSize', 0.05, 'DesiredOutputPower', 1.0, 'MaxPowerGain', 60.0)
        self.eng.workspace["signal"] = self.eng.complex(signal)
        signal, powerlevel = self.eng.eval("automaticGainControl(signal)", nargout=2)

        # Diagnostics
        if self.debug:
            end = time()
            print(f"Done in {end - start} seconds.")
            
            # Main plot
            # figure(100);
            # plot(2*signal, '.', 'MarkerSize', 4);
            
            # Power amplification level
            # figure(1); clf;
            # plot(time, powerLevel);
            # xlabel("Time (s)"); ylabel("Power (units?)");
        end

        return signal


if __name__ == '__main__':
    # from scope_control import Infiniium

    # visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"
    # scope = Infiniium(visa_address, False)

    proc = WaveformProcessor(True, "M4N5_Permutation_Sequence.mat")

    # waveform = scope.get_waveform_words()
    # samp_rate = scope.get_sample_rate()

    #import pickle
    #with open('m4n5_waveform_obj.pkl', 'rb') as inp:
    #    waveform = pickle.load(inp)
    #    samp_rate = pickle.load(inp)

    loaded = proc.load_qam_waveform("m4n5capture.mat")["Channel_1"]
    samp_rate = 1 / loaded["XInc"]
    waveform = loaded["Data"]


    print("test")

    # proc.eng.double(waveform)
    proc.process_qam(samp_rate, waveform)


#import pickle
    #with open('saved_waveform.pkl', 'wb') as outp:
    #    pickle.dump(waveform, outp, pickle.HIGHEST_PROTOCOL)
    #    pickle.dump(samp_rate, outp, pickle.HIGHEST_PROTOCOL)