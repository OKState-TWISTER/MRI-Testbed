import math


# decorator for class functions
def catch_exceptions(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"Error: {e}")
            if not self.debug:
                raise e

    return wrapper


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
        prat = 10 ** (powernorm / 10)  # convert dB to ratio
        power_rat.append(prat)
    return power_rat

def normalize_data(data):
    dmax = max(data)
    norm_data = []
    for point in data:
        norm_data.append(point - dmax)
    return norm_data

def to_log(data):
    return [math.log10(point) for point in data]
