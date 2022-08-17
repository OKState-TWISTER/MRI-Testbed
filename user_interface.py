# This file is a mess and desperately needs to be rewritten.
# Please do not edit unless you really know what you are doing.

import csv
import pathlib
import os

settings_filename = "settings.csv"


class UserSettings:
    def __init__(self, debug):
        self.debug = debug

        self.mode = Setting("measurement mode", description="measure complex waveform errors or single-tone signal amplitude", valid_values=["cw", "ber"])

        self.test_series = Setting("test series", description="this will determine which folder the test data is saved to")
        self.desc = Setting("test description", description="this will be used to name the output files")
        self.starting_pos = Setting("starting angle", description="where the test should begin (positive)")
        self.ending_pos = Setting("ending angle", description="where the test should end (negative probably)")
        self.step_size = Setting("step size", description="how many degrees between each sample point")
        self.zero_offset = Setting("zero offset", default_value="0", description="stage position that results in 0 degree actual angle for DUT.\n" +
                                   "!!! Leave at 0 unless you know what you're doing !!!")
        
        # Save waveforms
        self.save_waveforms = Setting("save waveforms", description="should every waveform capture be saved to a file for further analysis", valid_values=['t', 'f', 'y', 'n', '1', '0'], bool=True)
        self.waveform_count = Setting("waveform count", description="how many waveforms should be captured at each position (ignored if save waveforms is false)")

        # Single tone
        self.averaging_time = Setting("averaging time", description="how many seconds to wait for DSO to average before recording value")

        # Modulated
        self.if_estimate = Setting("if estimate", description="todo")


        self.settings_file = os.path.join(
            pathlib.Path(__file__).parent.absolute(), settings_filename
        )

        gen_settings = {
            "mode": self.mode,
            "series": self.test_series,
            "starting_pos": self.starting_pos,
            "ending_pos": self.ending_pos,
            "step_size": self.step_size,
            "zero_offset": self.zero_offset,
            "save_waveforms": self.save_waveforms,
        }

        swf_settings = {
            "waveform_count": self.waveform_count,
        }

        cw_settings = {
            "averaging_time": self.averaging_time,
        }

        mt_settings = {
            "if_estimate": self.if_estimate,
        }

        self.load(gen_settings)

        mode = gen_settings["mode"]
        if not mode.value:
            self.get_input(self.mode)
            mode = self.mode

        if mode.value == "cw":
            self.load(cw_settings)
            settings = gen_settings | cw_settings
        elif mode.value == "ber":
            self.load(mt_settings)
            settings = gen_settings | mt_settings

        if mode.value == "ber" and self.save_waveforms.value:
            self.load(swf_settings)
            settings = settings | swf_settings
            


        if None not in [setting.value for setting in settings.values()]:
            print("\nPreviously used settings:")
            for k, v in settings.items():
                print(f"{k}: {v}")
            choice = input(
                '\nWould you like to edit these settings?\n(enter "y" to edit or nothing to continue): '
            )
            if choice.lower() == "y":
                self.get_input(self.mode)
                mode = self.mode

                if mode.value == "cw":
                    self.load(cw_settings)
                    settings = gen_settings | cw_settings
                elif mode.value == "ber":
                    self.load(mt_settings)
                    settings = gen_settings | mt_settings

                for setting in settings.values():
                    if not setting.name == "measurement mode":
                        self.get_input(setting)
        else:
            for setting in settings.values():
                if not setting.name == "measurement mode":
                    self.get_input(setting)

        self.get_input(self.desc)

        self.save(settings)

    def load(self, settings):
        if not os.path.exists(self.settings_file):
            return
        try:
            with open(self.settings_file, "r") as inp:
                reader = csv.reader(inp)
                data = {rows[0]: rows[1] for rows in reader}
                if self.debug:
                    print(f"printing loaded data:\n{data}")
        except Exception:
            print(f"Error loading settings from file '{self.settings_file}'")
            return
        if data:
            for k, v in settings.items():
                if k in data:
                    v.value = data[k]

    def save(self, settings):
        with open(self.settings_file, "w", newline="") as outp:
            writer = csv.writer(outp)
            for k, v in settings.items():
                writer.writerow([k, v])

    def get_input(self, setting):
        prompt_text = f"\n[{setting.name}]"
        if setting.desc:
            prompt_text += f": {setting.desc}"
        if setting.valid_values:
            prompt_text += f"\nValid options: [{', '.join(setting.valid_values)}]"
        if setting.value:
            prompt_text += f"\nEnter {setting.name} or press enter to use previous value ({setting.value}): "
        else:
            prompt_text += f"\nEnter {setting.name}: "

        while True:
            nv = input(prompt_text)
            if nv:
                if (setting.valid_values and nv in setting.valid_values) or not setting.valid_values:
                    if setting.bool:
                        if nv.lower() in ("y", "yes", "t", "true", "1"):
                            setting.value = "true"
                        else:
                            setting.value = "false"
                    else:
                        setting.value = nv
                elif setting.valid_values:  # and nv not in setting.valid_values
                    continue

            if setting.value:
                break


class Setting:
    def __init__(self, name=None, default_value=None, valid_values=None, description=None, bool=None):
        self.name = name
        self.value = default_value
        self.valid_values = valid_values
        self.desc = description
        self.bool = bool

    def __call__(self):
        return self.value

    def __repr__(self):
        return self.value

if __name__ == '__main__':
    UserSettings(True)
