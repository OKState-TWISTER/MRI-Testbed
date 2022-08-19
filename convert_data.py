from array import array
import pickle
import os

data_dir = r"Data"

for root, d_names, f_names in os.walk(data_dir):
    for file in f_names:
        filepath = os.path.join(root, file)

        if not filepath.endswith(".pkl"):
            continue
        if os.path.exists(filepath.replace(".pkl", "")):
            continue

        with open(filepath, 'rb') as inp:
            samp_rate = pickle.load(inp)
            num_samples = pickle.load(inp)
            waveform = pickle.load(inp)

        if len(waveform) != num_samples:
            print(f"Error: Number of samples does not match sample count in file {filepath}")
            input()

        version = 1
        ver = version.to_bytes(2, 'big')
        sample_rate = int(samp_rate).to_bytes(8, 'big')
        num_samples = len(waveform).to_bytes(8, 'big')
        data = array('i', waveform).tobytes()

        datafile = filepath.replace(".pkl", "")
        print(f"Writing {waveform} at {samp_rate} samp/sec to file {datafile}")
        with open(datafile, 'wb') as outp:
            outp.write(ver)
            outp.write(sample_rate)
            outp.write(num_samples)
            outp.write(data)