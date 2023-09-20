import motion_stage.py

def characterize(min_angle, max_angle, step_size):
    motion_stage.setup()
    motion_stage.home(motion_stage.motor)
    motion_stage.set_pos(motion_stage.motor,min_angle)
    curr_angle = min_angle
    while curr_angle <= max_angle:
        motion_stage.set_pos(motion_stage.motor,curr_angle)
        curr_angle += step_size
        motion_stage.wait(1,motion_stage.motor)
        #Capture oscilloscope measurements
