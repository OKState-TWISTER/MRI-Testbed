# v2.1

# this program will process data captured using the vdi_characterization program

from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
import os
import re
from time import perf_counter as time

import fileio
from waveform_analysis import WaveformProcessor


# this is where waveform files are located
waveform_dir = r"C:\Users\UTOL\Desktop\test1_2022-11-09T1306"
# this is where the matlab source files are located
original_waveform_dir = r"C:\Users\UTOL\Desktop\Waveforms"

output_file = os.path.join(waveform_dir, "trash_results.csv")

def main():
    # loop through each test series in the root directory
    for file in os.listdir(waveform_dir):
        filepath = os.path.join(waveform_dir, file)
        sourcefile = '_'.join(file.split('_')[:4]) + ".mat"
        sourcepath = os.path.join(original_waveform_dir, sourcefile)

        try:
            proc = WaveformProcessor(debug=True, org_waveform=sourcepath) # Change debug to true to see eye information.
        except FileNotFoundError as e:
            return e, None

        samp_rate, samp_count, samples = fileio.load_bin1(filepath)
        proc.process_qam(samp_rate, samples)

    return #TODO clean up this mess

    # process waveforms in directory
    SNRsum = 0
    biterrsum = 0
    symerrsum = 0
    bitsum = 0
    symsum = 0
    seg_count = 0
    for file in os.listdir(dirpath):
        root, dir = os.path.split(dirpath)
        longfn = os.path.join(dir, file)
        filepath = os.path.join(dirpath, file)
        samp_rate, samp_count, samples = fileio.load_waveform(filepath)

        start = time()
        SNR, nbits, nbiterrors, nsyms, nsymerrors = proc.process_qam(samp_rate, samples)
        end = time()

        print(f"File '{longfn}' computed in {end - start} seconds")
        SNRsum += SNR
        biterrsum += nbiterrors
        symerrsum += nsymerrors
        bitsum += nbits
        symsum += nsyms
        seg_count += 1
   
    SNRavg = SNRsum / seg_count
    #berav = bersum / seg_count
    #symerravg = symerrsum / seg_count


    key = dir.replace("_waveforms", "")
    #return key, (SNRavg, bitsum, berav, symsum, symerravg)
    return key, (SNRavg, bitsum, biterrsum, symsum, symerrsum)


if __name__ == "__main__":
    main()
    input()
