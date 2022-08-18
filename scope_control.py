"""
This module handles interfacing with the Keysight DSOV254A.
The oscilloscope is controlled using the VISA standard via the pyvisa package.

Requires:
- pyvisa: (install with pip)
- KeySight IOLS: https://www.keysight.com/zz/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html
"""

import atexit
import struct
import sys

import pyvisa


class Infiniium:
    def __init__(self, visa_address, debug):
        self.debug = debug
        atexit.register(self.shutdown)

        rm = pyvisa.ResourceManager("C:\\WINDOWS\\system32\\visa64.dll")
        self.infiniium = rm.open_resource(visa_address)
        self.infiniium.timeout = 20000
        self.infiniium.clear()
        # Clear status.
        self.do_command("*CLS")
        idn_string = self.do_query("*IDN?")
        print("Identification string: '%s'" % idn_string)

        # TODO: load trigger setup (#9)

        # Set waveform capture settings
        self.do_command(":SYSTem:HEADer OFF")
        self.do_command(":WAVeform:SOURce CHANnel1")
        self.do_command(":WAVeform:STReaming OFF")
        # self.do_command(":ACQuire:MODE HRESolution")  # this may slow data acquisition down considerably
        self.do_command(":ACQuire:COMPlete 100")  # take a full measurement
        # self.do_command(":ACQuire:POINts 1000") # dont set points, let the scope capture between two triggers

    def shutdown(self):
        self.infiniium.close()

    def get_fft_peak(self):
        power = self.do_query(":FUNCtion2:FFT:PEAK:MAGNitude?").strip().replace('"', "")
        if "9.99999E+37" in power:
            power = "-9999"
        return float(power)

    def get_sample_rate(self):
        xinc = self.do_query(":WAVeform:XINCrement?")
        samp_rate = 1 / float(xinc)

        if self.debug:
            print(f"Xinc: '{xinc}'\nSample rate: '{samp_rate}'")

        return samp_rate

    def get_waveform_bytes(self):
        # Get the number of waveform points.
        qresult = self.do_query(":WAVeform:POINts?")
        print("Waveform points: %s" % qresult)

        # Choose the format of the data returned:
        self.do_command(":WAVeform:FORMat BYTE")
        print("Waveform format: %s" % self.do_query(":WAVeform:FORMat?"))

        # Get the waveform data.
        self.do_command(":DIGitize CHANnel1")
        sData = self.do_query_ieee_block(":WAVeform:DATA?")

        # Unpack signed byte data.
        values = struct.unpack("%db" % len(sData), sData)
        print("Number of data values: %d" % len(values))
        return values

    def get_waveform_words(self):
        # Get the number of waveform points.
        qresult = self.do_query(":WAVeform:POINts?")
        print("Waveform points: %s" % qresult)

        # Choose the format of the data returned:
        self.do_command(":WAVeform:FORMat WORD")
        print("Waveform format: %s" % self.do_query(":WAVeform:FORMat?"))

        # Get the waveform data.
        self.do_command(":DIGitize CHANnel1")
        sData = self.do_query_ieee_block(":WAVeform:DATA?")

        print(f"length: {len(sData)}")

        # Unpack signed byte data.
        # values = struct.unpack("%db" % (len(sData)/1), sData)
        values = []
        for m, l in zip(sData[0::2], sData[1::2]):
            values.append(int.from_bytes([m, l], byteorder="big", signed=True))

        print("Number of data values: %d" % len(values))

        return values

    def get_waveform_ascii(self):
        # Get the number of waveform points.
        qresult = self.do_query(":WAVeform:POINts?")
        print("Waveform points: %s" % qresult)

        # Choose the format of the data returned:
        self.do_command(":WAVeform:FORMat ASCii")
        print("Waveform format: %s" % self.do_query(":WAVeform:FORMat?"))

        # Get the waveform data.
        self.do_command(":DIGitize CHANnel1")
        values = "".join(self.do_query(":WAVeform:DATA?")).split(",")
        values.pop()  # remove last element (it's empty)
        print("Number of data values: %d" % len(values))
        return values

    def do_command(self, command, hide_params=False):
        if hide_params:
            (header, data) = command.split(" ", 1)
            if self.debug:
                print("\nCmd = '%s'" % header)
        else:
            if self.debug:
                print("\nCmd = '%s'" % command)

        self.infiniium.write("%s" % command)

        if hide_params:
            self.check_instrument_errors(header)
        else:
            self.check_instrument_errors(command)

    def do_query(self, query):
        if self.debug:
            print("Qys = '%s'" % query)
        result = self.infiniium.query("%s" % query)
        self.check_instrument_errors(query)
        return result

    def do_query_ieee_block(self, query):
        if self.debug:
            print("Qyb = '%s'" % query)
        result = self.infiniium.query_binary_values(
            "%s" % query, datatype="s", container=bytes
        )
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
                        exit()
                else:  # "No error"
                    break
            else:  # :SYSTem:ERRor? STRing should always return string.
                print(
                    "ERROR: :SYSTem:ERRor? STRing returned nothing, command: '%s'"
                    % command
                )
                print("Exited because of error.")
                sys.exit(1)
