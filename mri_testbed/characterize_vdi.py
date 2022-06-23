## Will perform a rough antenna characterization using KeySight DSO FFT averaging
## and Thorlabs HDR50 rotator stage

# Requires: pythonnet, pyvisa (install with pip)

# May require:
# https://www.keysight.com/zz/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html
# Thorlabs Kinesis ~
# (all relevant .dlls should be included in this repo)

# v0.1

# import python modules
import atexit
import pyvisa
import sys
import os
import time

# load .net assemblies
# sys.path.append()  # os.getcwd()
sys.path.append("C:\\Program Files\\Thorlabs\\Kinesis")
import clr

print(sys.path)  # TODO: fix path issues for AddReference

# clr.AddReference("Thorlabs.MotionControl.Benchtop.StepperMotorCLI")
# clr.AddReference("Thorlabs.MotionControl.Benchtop.StepperMotorUI")
# clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
# clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")

clr.AddReference(
    "C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.Benchtop.StepperMotorCLI"
)
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


# Global Variables
serial_num = "40163084"
visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"

starting_angle = 315  # "home" - Should result in 0 degree actual angle for DUT
span = 90  # how far stage will rotate for the test
ending_angle = starting_angle - span
rotate_direction = MotorDirection.Backward

averaging_time = 5  # how long to wait for DSO to average before recording value
debug = False


def main():
    rm = pyvisa.ResourceManager(r"C:\WINDOWS\system32\visa64.dll")
    scope = Infiniium(rm.open_resource(visa_address))

    stage = Kinesis(serial_num)

    result = scope.do_query(":FUNCtion3:FFT:PEAK:LEVel?")
    print(f"Scope will measure all RF peaks above {result}")

    ## Begin work
    print('Actuator is "Homing"')
    print(f"Start position: {starting_angle} (absolute)")
    stage.move_to(starting_angle)
    if (pos := stage.get_angle()) != starting_angle:
        print(
            f"Error homing stage. Desired angle: {starting_angle}  measured angle: {pos}"
        )
    else:
        print("Stage is homed")
        input("Press any key to begin")

    current_pos = stage.get_angle()
    while current_pos > ending_angle:
        print(f"Stage position: {current_pos} degrees")
        time.sleep(averaging_time)

        power = scope.do_query(":FUNCtion3:FFT:PEAK:MAGNitude?")
        print(f"Power level: {power} dBm")

        print("Stage is moving")
        stage.move_to(
            current_pos - 0.5
        )  # this could be very dangerous. make sure move direction is correct (do not wrap coax)
        current_pos = stage.get_angle()


##########################################################################


class Kinesis:
    def __init__(self, serial_number):
        atexit.register(self.shutdown)
        # SimulationManager.Instance.InitializeSimulations() # only needed if using Kinesis simulator
        # DeviceManagerCLI.BuildDeviceList() # unecessary?

        self.device = BenchtopStepperMotor.CreateBenchtopStepperMotor(serial_number)
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

        settings = ThorlabsBenchtopStepperMotorSettings
        self.channel.GetSettings(settings)
        settings.Limit.CCWSoftLimitUnit = System.Decimal(90)
        settings.Limit.CCWSoftLimitUnit = System.Decimal(0)
        self.channel.SetSettings(settings, False)

        self.channel.SetRotationModes(
            RotationSettings.RotationModes.RotationalRange,
            RotationSettings.RotationDirections.Quickest,
        )

    def shutdown(self):
        self.channel.StopPolling()
        self.device.ShutDown()

    def get_angle(self):
        return self.channel.Position
        # TODO real angle

    def move_to(self, angle):
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
        self.do_command(":RECall:SETup 9")

    def shutdown(self):
        self.infiniium.close()

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
