import atexit
import csv
import datetime
import math
#import matlab.engine
import matplotlib.pyplot as plot
import numpy
import os
import pyvisa
import struct
import sys
import time

debug = False
visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"

def main():
    rm = pyvisa.ResourceManager(r"C:\WINDOWS\system32\visa64.dll")
    scope = Infiniium(rm.open_resource(visa_address))

    var = scope.get_waveform()

    print(var)
    input()


class Infiniium:
    def __init__(self, resource):
        atexit.register(self.shutdown)
        self.infiniium = resource
        self.infiniium.timeout = 20000
        self.infiniium.clear()
        # Clear status.
        self.do_command("*CLS")
        # Get and display the device's *IDN? string.
        idn_string = self.do_query("*IDN?")
        print("Identification string: '%s'" % idn_string)

    def shutdown(self):
        self.infiniium.close()

    def get_fft_peak(self):
        power = self.do_query(":FUNCtion4:FFT:PEAK:MAGNitude?").strip().replace('"', '')
        if "9.99999E+37" in power:
            power = "-9999"
        return float(power)

    def get_waveform(self):
        # Get the waveform type.
        qresult = self.do_query(":WAVeform:TYPE?")
        print("Waveform type: %s" % qresult)
        # Get the number of waveform points.
        qresult = self.do_query(":WAVeform:POINts?")
        print("Waveform points: %s" % qresult)
        # Set the waveform source.
        self.do_command(":WAVeform:SOURce CHANnel1")
        qresult = self.do_query(":WAVeform:SOURce?")
        print("Waveform source: %s" % qresult)
        # Choose the format of the data returned:
        self. do_command(":WAVeform:FORMat BYTE")
        print("Waveform format: %s" % self.do_query(":WAVeform:FORMat?"))

        # Get the waveform data.
        self.do_command(":WAVeform:STReaming OFF")
        sData = self.do_query_ieee_block(":WAVeform:DATA?")
        # Unpack signed byte data.
        values = struct.unpack("%db" % len(sData), sData)
        print("Number of data values: %d" % len(values))
        return values

    def do_command(self, command, hide_params=False):
        if hide_params:
            (header, data) = command.split(" ", 1)
            if debug:
                print("\nCmd = '%s'" % header)
        else:
            if debug:
                print("\nCmd = '%s'" % command)

        self.infiniium.write("%s" % command)

        if hide_params:
            self.check_instrument_errors(header)
        else:
            self.check_instrument_errors(command)

    def do_query(self, query):
        if debug:
            print("Qys = '%s'" % query)
        result = self.infiniium.query("%s" % query)
        self.check_instrument_errors(query)
        return result

    def do_query_ieee_block(self, query):
        if debug:
            print("Qyb = '%s'" % query)
        result = self.infiniium.query_binary_values("%s" % query, datatype='s', container=bytes)
        self.check_instrument_errors(query, exit_on_error=False)
        return result

    def check_instrument_errors(self, command, exit_on_error=True):
        while True:
            error_string = self.infiniium.query(":SYSTem:ERRor? STRing")
            if error_string:  # If there is an error string value.
                if error_string.find("0,", 0, 2) == -1:  # Not "No error".
                    print("ERROR: %s, command: '%s'" % (error_string, command))
                    if exit_on_error:
                        print("Exited because of error.")
                        sys.exit(1)
                else:  # "No error"
                    break
            else:  # :SYSTem:ERRor? STRing should always return string.
                print(
                    "ERROR: :SYSTem:ERRor? STRing returned nothing, command: '%s'"
                    % command
                )
                print("Exited because of error.")
                sys.exit(1)





main()