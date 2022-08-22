import os
import pandas
import re
from time import time

from fileio import File_IO
from waveform_analysis import WaveformProcessor

# this is where waveform files are located
waveform_dir = r""

output_file = os.path.join(waveform_dir, "results.csv")
print(f"Will write results to {output_file}")

fileio = File_IO(waveform_dir)

for root, d_names, f_names in os.walk(waveform_dir):
    # collect any already processed data
    if os.path.exists(output_file):
        BER = pandas.read_csv(output_file, header=None, index_col=0).squeeze("columns").to_dict()
    else:
        BER = {}
    print(BER)
    for dir in d_names:
        dir_fp = os.path.join(root, dir)
        if not os.listdir(dir_fp):
            print(f"Directory {dir_fp} is empty")
            continue

        testname = dir.replace("_waveforms", "")
        if testname in BER:
            print(f"Data for test '{testname}' already exists. skipping")
            continue
        
        print(dir)

        # get if_estimate and original waveform file from .info file
        info_fn = dir.replace("_waveforms", ".info")
        info_fp = os.path.join(root, info_fn)
        print(f"name: {info_fn}. path: {info_fp}")
        if os.path.exists(info_fp):
            with open (info_fp, 'rt') as info_file:
                contents = info_file.read()

            ifregex = re.compile(r"IF estimate: ([0-9.]+)")
            if_estimate = float(ifregex.search(contents).group(1))

            matregex = re.compile(r"Original waveform filename: (.*\.mat)")
            owf_file = matregex.search(contents).group(1)
            
        else:
            print(f"Could not find .info file for test dir {dir}. provide if_estimate manually:")
            inp = input("if_estimate: ")
            if_estimate = float(inp)

        print(f"IF estimate: {if_estimate}")
        print(f"Original waveform .mat file: {owf_file}")

        try:
            proc = WaveformProcessor(if_estimate, debug=False, org_waveform=owf_file)
        except FileNotFoundError:
            continue

        # process waveforms in directory
        bersum = 0
        seg_count = 0
        for file in os.listdir(dir_fp):
            filepath = os.path.join(dir_fp, file)
            samp_rate, samp_count, samples = fileio.load_waveform(filepath)

            start = time()
            ber = proc.process_qam(samp_rate, samples)
            end = time()

            print(f"BER for file '{file}': {ber} - computed in {end - start} seconds")
            bersum += ber
            seg_count += 1
   
        berav = bersum / seg_count

        key = dir.replace("_waveforms", "")
        BER[key] = berav
        print(f"\nAverage BER for {key}: {berav}\n")

        pandas.DataFrame.from_dict(data=BER, orient='index').to_csv(output_file, header=False)

input()