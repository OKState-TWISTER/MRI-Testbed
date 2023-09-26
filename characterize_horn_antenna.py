import motion_stage
import time
import numpy as np

from twister_api.oscilloscope_interface import Oscilloscope
scope = Oscilloscope(debug=True)

#parameters: start angle (degrees), end angle (in degrees), step size (in degrees), sleep time (in ms)
def characterize(min_angle, max_angle, step_size, pause_time):
    #arrays to keep track of current angle and fft_peak measurements
    angles = np.array([])
    fft_peaks = np.array([])

    #motor setup and homing
    motor = motion_stage.setup()
    motion_stage.home(motor)

    #convert angles to device measurements
    min_angle = angle_to_device_units(min_angle)
    max_angle = angle_to_device_units(max_angle)
    step_size = angle_to_device_units(step_size)

    #step the specified size and take fft peak measurent repeatedly until rotated desired amount
    curr_angle = min_angle
    while curr_angle <= max_angle:
        motion_stage.set_pos(motor,curr_angle)
        curr_angle += step_size
        time.sleep(pause_time * 1000)

        #Capture oscilloscope measurements
        peak = scope.get_fft_peak()
        angles = np.append(angles, curr_angle)
        fft_peaks = np.append(fft_peaks, peak)

    #save data in csv format
    arr = np.asarray([peak, angles])
    np.savetxt('horn_anntena_characterization.csv', arr, fmt='%d', delimiter=",")

#convert angle degree measurements to device units
def angle_to_device_units(angle):
    return int(angle/0.00001331666666667)

class characterize_horn_antenna:
    characterize(0, 90, 1, 1000)