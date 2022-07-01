# v0.4

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


## TODO:
# get waveforms off of scope
# execute matlab from script
# control speed of rotator
# reset scope averaging every time rotator resets

# import python modules
import atexit
import csv
import datetime
import math
#import matlab.engine
import matplotlib.pyplot as plot
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
serial_num = "40163084"
visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"

date_time = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
#destination_filename = f"300ghz_data_test4.1-{date_time}.csv"
destination_filename = f"antenna_pattern_6_antithzmaterialmk2_goodaverage-{date_time}.csv"

starting_angle = 50  # where the test should begin
ending_angle = -50
step_size = 0.1  # how many degrees between each sample point
averaging_time = 0.1  # how long to wait for DSO to average before recording value
zero_offset = 0  # stage position that results in 0 degree actual angle for DUT (DO NOT CHANGE)
debug = False

# Do not change
#ending_angle = (ending_angle + 360) if ending_angle < 0 else ending_angle
test_duration = (starting_angle - ending_angle) / step_size * averaging_time / 60 # minutes

def main():
    # Initialize rotation stage
    stage = Kinesis(serial_num)

    # Initialize DSO
    rm = pyvisa.ResourceManager(r"C:\WINDOWS\system32\visa64.dll")
    scope = Infiniium(rm.open_resource(visa_address))

    print('Actuator is "Homing"')
    print(f"Start position: {starting_angle} : {starting_angle + zero_offset} (absolute)")
    stage.move_to(starting_angle + zero_offset)
    if (pos := stage.get_angle()) != (starting_angle + zero_offset):
        print(
            f"Error homing stage. Desired angle: {starting_angle}  measured angle: {pos}"
        )
        exit()
    else:
        print("Stage is homed")
        print(f"Test will take {test_duration} minutes to complete.")
        input("Press any key to begin")

    data = [[], []]

    plot = Custom_Plot()

    current_pos = stage.get_angle()
    print(f"ending angle: {ending_angle}")

    # TODO: save data even if test ends prematurely

    while current_pos > ending_angle: # TODO: fix this
        print(f"Stage position: {current_pos} (absolute) {current_pos - zero_offset} (effective)")
        time.sleep(averaging_time)

        power = scope.get_fft_peak()
        print(f"Power level: {power} dBm")

        data[0].append(current_pos - zero_offset)
        data[1].append(power)
        
        plot.update(data)

        # TODO: make sure peak is at correct frequency

        print("Stage is moving")
        # Be very careful when moving the stage to not wrap coax
        stage.move_to(current_pos - step_size)
        current_pos = stage.get_angle()
        if current_pos > starting_angle:
            current_pos = current_pos - 360

    print(f"writing data to {destination_filename}")
    with open(destination_filename, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        for i in range(len(data[0])):
            row = (data[0][i], data[1][i])
            csvwriter.writerow(row)
    print("Test complete.")


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

class Custom_Plot:
    def __init__(self):
        plot.ion()
        self.fig = plot.figure(figsize=(6,6))
        self.axis = plot.subplot(111, polar=True)
        self.line, = self.axis.plot([],[])
        atexit.register(self.print_report)

    def update(self, data):
        self.data = data
        pos_data, power_data = data
        theta = deg_to_rad(pos_data)
        r = normalize_power(power_data)

        self.line.set_xdata(theta)
        self.line.set_ydata(r)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def print_report(self):
        self.fig.savefig(destination_filename.replace(".csv", ".png"))
        print(f"Max value: {max(self.data[1])} dBm")

        input("Press any key to exit")


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

        print(self.channel.AdvancedMotorLimits.VelocityMaximum)


        #settings = ThorlabsBenchtopStepperMotorSettings
        #settings.GetSettings(motorConfiguration)
        #con = settings.Control
        #con.DefMaxVel = System.Decimal(5) #type does not support setting attributes
        #self.channel.SetSettings(settings, False) # Object of type 'System.RuntimeType' cannot be converted to type 'Thorlabs.MotionControl.DeviceManagerCLI.DeviceSettings'.

        # TODO: contant Thorlabs or pythonnet devs about 

        #self.channel.SetRotationModes(
         #   Thorlabs.MotionControl.GenericMotorCLI.Settings.RotationSettings.RotationModes.RotationalRange,
          #  Thorlabs.MotionControl.GenericMotorCLI.Settings.RotationSettings.RotationDirections.Quickest,
        #)

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
        power = self.do_query(":FUNCtion4:FFT:PEAK:MAGNitude?").strip().replace('"', '')
        if "9.99999E+37" in power:
            power = "-9999"
        return float(power)

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
