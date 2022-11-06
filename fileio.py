from array import array
import pickle
import os

# TODO: save only required number of bytes per sample

def save_waveform(self, waveform, samp_rate, filepath):
    if not position:
        position = "static"
    datafile = os.path.join(self.waveform_dir, f"{position}_{n}")

    version = 1
    ver = version.to_bytes(2, 'big')
    sample_rate = int(samp_rate).to_bytes(8, 'big')
    num_samples = len(waveform).to_bytes(8, 'big')
    data = array('i', waveform).tobytes()

    print(f"Saving {num_samples} samples at {samp_rate} Samp/sec to file '{datafile}' using v{version} formatting")
    with open(datafile, 'wb') as outp:
        outp.write(ver)
        outp.write(sample_rate)
        outp.write(num_samples)
        outp.write(data)


def load_waveform(self, filename):
    filepath = os.path.join(self.waveform_dir, filename)
    
    # If data is pickled
    if filepath.endswith(".pkl"):
        return self.load_pickle(filepath)

    # Else, get format version number from binary file
    with open(filepath, 'rb') as file:
        version = int.from_bytes(file.read(2), 'big')

    # Load the file depending on the format
    if version == 1:
        return self.load_bin1(filepath)
    if version == 2:
        pass


def load_pickle(self, filepath):
    with open(filepath, 'rb') as inp:
        samp_rate = pickle.load(inp)
        num_samples = pickle.load(inp)
        waveform = pickle.load(inp)

    return (samp_rate, num_samples, waveform)


def load_bin1(self, filepath):
    ## [bytes] - description ##
    # [0:1] - version (2 bytes)
    # [2:9] - samplerate (8 bytes)
    # [10:17] - sample count (8 bytes)
    # [18:] - samples (n bytes)
    
    data = array('i')

    with open(filepath, 'rb') as inp:
        version = int.from_bytes(inp.read(2), 'big')
        samp_rate = int.from_bytes(inp.read(8), 'big')
        samp_count = int.from_bytes(inp.read(8), 'big')
        data.frombytes(inp.read())
    
    samples = data.tolist()

    if len(data) != samp_count:
        print("Warning: loading file error.\nPayload length does not match sample count. Data may be corrupted")

    return (samp_rate, samp_count, samples)


if __name__ == '__main__':
    pass