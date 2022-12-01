
# v3.0b1

# this program will process data captured using the vdi_characterization program

import os
import re
from time import perf_counter as time
import pandas
import twister_api.fileio as fileio
from waveform_analysis import WaveformProcessor

import queue
import threading


# this is where the captured waveform files are located
waveform_dir = r"C:\Users\kstreck\Desktop\test1_2022-11-18T1350"

# this is where the matlab source files are located
original_waveform_dir = r"C:\Users\kstreck\Desktop\Waveforms"

output_file = os.path.join(waveform_dir, "trash_results.csv")

all_data = {}


# The queue for tasks
q = queue.Queue()
proc_q = queue.Queue()

# Worker, handles each task
def worker():
    while True:
        filepath = q.get()
        proc = proc_q.get()
        if filepath is None:
            break
        while proc is None:
            proc = proc_q.get()
        root, file = os.path.split(filepath)

        sourcefile = '_'.join(file.split('_')[:4]) + ".mat"
        sourcepath = os.path.join(original_waveform_dir, sourcefile)

        proc.load_qam_waveform(sourcepath)
        samp_rate, samp_count, samples = fileio.load_waveform(filepath)
        SNR, nbits, biterr, nsyms, symerr = proc.process_qam(samp_rate, samples)

        # This could be unsafe with multithreaded processes?!?  Check this!
        all_data.update({str(filepath) : (SNR, nbits, biterr, nsyms, symerr)})

        proc_q.put(proc)
        #print(q.qsize())
        q.task_done()


def start_workers(worker_pool=4):
    threads = []
    for i in range(worker_pool):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)
        proc_q.put(WaveformProcessor(debug=False))
    return threads


def stop_workers(threads):
    # stop workers
    for i in threads:
        q.put(None)
    for t in threads:
        t.join()


def create_queue(task_items):
    for item in task_items:
        q.put(item)

def main():
    start = time()
    # loop through each test series in the root directory
    #series_names = next(os.walk(waveform_dir))[1]
    # Get the paths to every directory rooted in the "waveform_dir" folder
    #series_paths = [os.path.join(waveform_dir, dir) for dir in series_names if os.listdir(os.path.join(waveform_dir, dir))]

    # Create a list of all the files we want to process.
    # NOTE: This will choke if there are any non-waveform filetypes in the directory.
    # TODO:  Add a filter to solve this problem.
    list_of_files = [os.path.join(waveform_dir, file) for file in os.listdir(waveform_dir)]

    # Start up the workers
    # Creating the queue before the workers lets them get started as soon as they're created.
    # This is beneficial since the spin-up on the matlab engine can be many seconds.
    create_queue(list_of_files)
    workers = start_workers(worker_pool=4)

    # Block until all tasks are complete
    q.join()

    # Shut down the workers
    stop_workers(workers)

    # Print the results to file
    headerlist = ["SNR", "nbits", "biterr", "nsyms", "symerr"]
    pandas.DataFrame.from_dict(data=all_data, orient='index').to_csv(output_file, header=headerlist)
    end = time()
    print(f"processing test data took: {end - start:.2f} seconds")
    



if __name__ == "__main__":
    main()
    input()