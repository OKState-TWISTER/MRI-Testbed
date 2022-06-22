# Will perform a rough antenna characterization using KeySight DSO FFT averaging
## and Thorlabs HDR50 rotator stage
# needs pythonnet and pyvisa

# v0.1

# import python modules
import pyvisa
import sys
import os
import time

# load .net assemblies
# sys.path.append()  # os.getcwd()
sys.path.append("C:\\Program Files\\Thorlabs\\Kinesis")
import clr

print(sys.path)

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


# serialNo = "40163084"
serialNo = "40000001"
visa_address = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"

startingPos = 315  # the "home" position
endingPos = 315 - 90
rotateDirection = MotorDirection.Backward


SimulationManager.Instance.InitializeSimulations()
# DeviceManagerCLI.BuildDeviceList()

device = BenchtopStepperMotor.CreateBenchtopStepperMotor(serialNo)
device.Connect(serialNo)
channel = device.GetChannel(1)

if not channel.IsSettingsInitialized():
    channel.WaitForSettingsInitialized(5000)

# Start the device polling
# The polling loop requests regular status requests to the motor to ensure the program keeps track of the device.
channel.StartPolling(250)
time.sleep(1)
channel.EnableDevice()
time.sleep(1)
print("Device Enabled")

motorConfiguration = channel.LoadMotorConfiguration(channel.DeviceID)
deviceInfo = channel.GetDeviceInfo()
print(f"Device {deviceInfo.SerialNumber} = {deviceInfo.Name}")

channel.SetBacklash(System.Decimal(0))

## Begin work
print('Actuator is "Homing"')
print(f"Start position: {startingPos} (absolute)")
channel.MoveTo(System.Decimal(startingPos), 60000)
