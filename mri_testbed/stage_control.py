import atexit
import os
import sys
import time

# load .net assemblies
# sys.path.append()  # os.getcwd()
sys.path.append("C:\\Program Files\\Thorlabs\\Kinesis")
sys.path.append(os.path.dirname(__file__))
import clr
clr.AddReference(r"C:\Program Files\Thorlabs\Kinesis\Thorlabs.MotionControl.Benchtop.StepperMotorCLI")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.Benchtop.StepperMotorUI")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI")

import System
import System.IO
import System.Threading
from Thorlabs.MotionControl.Benchtop.StepperMotorCLI import *
from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
import Thorlabs.MotionControl.GenericMotorCLI.Settings

class Kinesis:
    def __init__(self, serial_number, start_pos, zero_offset):
        atexit.register(self.shutdown)

        self.starting_angle = start_pos
        self.zero_offset = zero_offset

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

        #print(self.channel.AdvancedMotorLimits.VelocityMaximum)
        #settings = ThorlabsBenchtopStepperMotorSettings
        #settings.GetSettings(motorConfiguration)
        #con = settings.Control
        #con.DefMaxVel = System.Decimal(5) #type does not support setting attributes
        #self.channel.SetSettings(settings, False) # Object of type 'System.RuntimeType' cannot be converted to type 'Thorlabs.MotionControl.DeviceManagerCLI.DeviceSettings'.
        # TODO: contant Thorlabs or pythonnet devs about abiguous errors

        self.channel.SetRotationModes(
            Thorlabs.MotionControl.GenericMotorCLI.Settings.RotationSettings.RotationModes.RotationalRange,
            Thorlabs.MotionControl.GenericMotorCLI.Settings.RotationSettings.RotationDirections.Quickest,
        )

    def shutdown(self):
        self.move_to(self.zero_offset)
        self.channel.StopPolling()
        self.device.ShutDown()

    def home(self):
        print('Actuator is "Homing"')
        print(f"Start position: {self.starting_angle} : {self.starting_angle + self.zero_offset} (absolute)")
        self.move_to(self.starting_angle + self.zero_offset)
        if (pos := self.get_angle()) != (self.starting_angle + self.zero_offset):
            print(
                f"Error homing stage. Desired angle: {self.starting_angle}  measured angle: {pos}"
            )
            return False
        else:
            print("Stage is homed")
            return True

    def get_angle(self):
        angle = self.channel.Position
        return float(angle.ToString())  # dirty type conversion

    def move_to(self, angle):
        if angle < 0:
            angle = angle + 360
        elif angle > 360:
            angle = angle + 360
        self.channel.MoveTo(System.Decimal(angle), 60000)