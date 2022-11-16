# v3.0b1

# this program will process data captured using the vdi_characterization program

import os
import re
from time import perf_counter as time

import twister_api.fileio as fileio

from waveform_analysis import WaveformProcessor


# this is where the captured waveform files are located
waveform_dir = r"C:\Users\UTOL\Desktop\test1_2022-11-09T1306"
# this is where the matlab source files are located
original_waveform_dir = r"C:\Users\UTOL\Desktop\Waveforms"

output_file = os.path.join(waveform_dir, "trash_results.csv")

proc = WaveformProcessor(debug=True)

def main():
    # loop through each test series in the root directory
    for file in os.listdir(waveform_dir):
        filepath = os.path.join(waveform_dir, file)
        sourcefile = '_'.join(file.split('_')[:4]) + ".mat"
        sourcepath = os.path.join(original_waveform_dir, sourcefile)

        proc.load_qam_waveform(sourcepath)

        samp_rate, samp_count, samples = fileio.load_waveform(filepath)

        SNR, nbits, biterr, nsyms, symerr = proc.process_qam(samp_rate, samples)

        #TODO: do something with the output of process_qam
        # can look at previous process_data.py for examples



if __name__ == "__main__":
    main()
    input()
