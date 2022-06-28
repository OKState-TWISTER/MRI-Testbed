# v0.2

# This program serves to automatically profile VDI modules by controlling various components:
## A Thorlabs HDR50 rotator stage connected to a BSC201 controller positions the TX antenna
##  - The stage is controlled using the Thorlabs provided .NET libraries via the pythonnet package
## A Keysight DSOV254A oscilloscope captures received waveforms
##  - The oscilloscope is controlled using the VISA standard via the pyvisa package
## The captured waveforms are analyzed using various MATLAB code
##   - Data is send to matlab via the matlab engine for python

# Requires:
# pythonnet, pyvisa (install with pip)
# MATLAB Engine API for Python: https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html
# KeySight IOLS: https://www.keysight.com/zz/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html
# Thorlabs Kinesis ~
# (all relevant .dlls should be included in this repo)


# import python modules
import atexit
import csv
import datetime
import math
#import matlab.engine
from matplotlib.pyplot import plot, ion, draw, show
import os
import pyvisa
import sys
import time

# load .net assemblies
# sys.path.append()  # os.getcwd()
sys.path.append("C:\\Program Files\\Thorlabs\\Kinesis")
sys.path.append(os.path.dirname(__file__))
import clr

print(sys.path)  # TODO: fix path issues for AddReference

#clr.AddReference("Thorlabs.MotionControl.Benchtop.StepperMotorCLI")
# clr.AddReference("Thorlabs.MotionControl.Benchtop.StepperMotorUI")
# clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
# clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")

clr.AddReference(r"C:\Program Files\Thorlabs\Kinesis\Thorlabs.MotionControl.Benchtop.StepperMotorCLI")
clr.AddReference(
    "C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.Benchtop.StepperMotorUI"
)
clr.AddReference(
    "C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI"
)
clr.AddReference(
    "C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI"
)

import System
import System.IO
import System.Threading
from Thorlabs.MotionControl.Benchtop.StepperMotorCLI import *
from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
import Thorlabs.MotionControl.GenericMotorCLI.Settings


################################################################################################
################################################################################################

# Global Variables
date_time = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
serial_num = "40163084"
visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"
destination_filename = f"300ghz_rx_data_full_{date_time}.csv"

zero_offset = 315  # stage position that results in 0 degree actual angle for DUT
starting_angle = 0  # where the test should begin
span = 105  # how far stage will rotate for the test
ending_angle = starting_angle - span
step_size = 1  # how many degrees between each sample point
averaging_time = 20  # how long to wait for DSO to average before recording value
debug = False


def main():
    # Initialize rotation stage
    stage = Kinesis(serial_num)

    # Initialize DSO
    rm = pyvisa.ResourceManager(r"C:\WINDOWS\system32\visa64.dll")
    scope = Infiniium(rm.open_resource(visa_address))

    print('Actuator is "Homing"')
    print(f"Start position: {starting_angle} (absolute)")
    stage.move_to(starting_angle)
    if pos := stage.get_angle() != starting_angle:
        print(
            f"Error homing stage. Desired angle: {starting_angle}  measured angle: {pos}"
        )
        exit()
    else:
        print("Stage is homed")
        print(f"Test will take {span / step_size * 20 / 60} minutes to complete.")
        input("Press any key to begin")

    data = [[], []]
    expect_peak = False

    #fig, axis = matplotlib.pyplot.subplots(subplot_kw={"projection": "polar"})

    current_pos = stage.get_angle()
    while current_pos > ending_angle:
        print(
            f"Stage position: {current_pos} (real) {current_pos - zero_offset} (test)"
        )
        time.sleep(averaging_time)

        spower = scope.get_fft_peak().strip().replace('"', '')
        print(spower)
        power = float(spower)
        print(f"Power level: {power} dBm")

        if power == float("-9.99999E+37"):
            if expect_peak:
                print("Scope did not measure a peak. Ending test.")
                break
        elif not expect_peak:
            expect_peak = True

        data[0].append(current_pos - zero_offset)
        data[1].append(power)
        #plot_polar(fig, axis, data)

        # TODO: make sure peak is at correct frequency

        print("Stage is moving")
        # Be very careful when moving the stage to not wrap coax
        stage.move_to(current_pos - step_size)
        current_pos = stage.get_angle()

    show()

    print(f"writing data to {destination_filename}")
    with open(destination_filename, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        for i in range(len(data[0])):
            row = (data[0][i], data[1][i])
            csvwriter.writerow(row)
    print("Test complete.")


def plot_polar(figure, axis, data):
    pos_data, power_data = data
    rad_pos = deg_to_rad(pos_data)
    power = normalize_power(power_data)

    axis.plot(rad_pos, power)
    # axis.set_rmax(2)
    draw()



def deg_to_rad(deg_data):
    rad_pos = []
    for angle in deg_data:
        rad_pos.append(angle * (math.pi / 180))
    return rad_pos


def normalize_power(power_data):
    pmax = max(power_data)
    power_rat = []
    for p in power_data:
        powernorm = p - pmax  # normalize max power to 0dB
        prat = 10 ** (powernorm / 20)  # convert dB to ratio
        power_rat.append(prat)
    return power_rat


################################################################################################
################################################################################################


class Kinesis:
    def __init__(self, serial_number):
        atexit.register(self.shutdown)
        # SimulationManager.Instance.InitializeSimulations() # only needed if using Kinesis simulator

        DeviceManagerCLI.BuildDeviceList()

        self.device = BenchtopStepperMotor.CreateBenchtopStepperMotor(serial_number)
        print(self.device)
        self.device.Connect(serial_number)
        # Thorlabs::MotionControl::Benchtop::StepperMotorCLI::StepperMotorChannel
        # inherits GenericAdvancedMotorCLI
        self.channel = self.device.GetChannel(1)

        if not self.channel.IsSettingsInitialized():
            self.channel.WaitForSettingsInitialized(5000)

        # Start the device polling
        # The polling loop requests regular status requests to the motor to ensure the program keeps track of the device.
        self.channel.StartPolling(250)
        time.sleep(1)
        self.channel.EnableDevice()
        time.sleep(1)
        print("Device Enabled")

        motorConfiguration = self.channel.LoadMotorConfiguration(self.channel.DeviceID)
        deviceInfo = self.channel.GetDeviceInfo()
        print(f"Device {deviceInfo.SerialNumber} = {deviceInfo.Name}")

        # set device parameters
        print(f"Stage needs homing? {self.channel.NeedsHoming}")
        print(f"Poisition calibrated? {self.channel.IsPositionCalibrated}")
        self.channel.SetBacklash(System.Decimal(0))

        # settings = ThorlabsBenchtopStepperMotorSettings
        # self.channel.GetSettings(settings) #Object of type 'System.RuntimeType' cannot be converted to type 'Thorlabs.MotionControl.DeviceManagerCLI.DeviceSettings'.
        # settings.Limit.CCWSoftLimitUnit = System.Decimal(90)
        # settings.Limit.CCWSoftLimitUnit = System.Decimal(0)
        # self.channel.SetSettings(settings, False)

        self.channel.SetRotationModes(
            Thorlabs.MotionControl.GenericMotorCLI.Settings.RotationSettings.RotationModes.RotationalRange,
            Thorlabs.MotionControl.GenericMotorCLI.Settings.RotationSettings.RotationDirections.Quickest,
        )

    def shutdown(self):
        self.channel.StopPolling()
        self.device.ShutDown()

    def get_angle(self):
        angle = self.channel.Position
        return float(angle.ToString())  # dirty type conversion
        # TODO real angle

    def move_to(self, angle):
        if angle < 0:
            angle = angle + 360
        self.channel.MoveTo(System.Decimal(angle), 60000)


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
        # Load saved setup #9
        self.do_command(":RECall:SETup 8")

    def shutdown(self):
        self.infiniium.close()

    def get_fft_peak(self):
        power = self.do_query(":FUNCtion4:FFT:PEAK:MAGNitude?")
        if "9.99999E+37" in power:
            power = "-9.99999E+37"
        return power

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
