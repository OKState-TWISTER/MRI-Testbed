import csv
import pathlib
import os

settings_filename = "settings.csv"


class IO:
    def __init__(self, debug):
        self.debug = debug

        self.test_series = Setting("test series", description="this will determine which folder the test data is saved to")
        self.desc = Setting("test description", description="this will be used to name the output files")
        self.starting_pos = Setting("starting angle", description="where the test should begin (positive)")
        self.ending_pos = Setting("ending angle", description="where the test should end (negative probably)")
        self.step_size = Setting("step size", description="how many degrees between each sample point")
        self.averaging_time = Setting("averaging time", description="how long to wait for DSO to average before recording value")
        self.zero_offset = Setting("zero_offset", default_value="0", description="stage position that results in 0 degree actual angle for DUT.\n" +
                                   "!!! Leave at 0 unless you know what you're doing !!!")

        self.settings_file = os.path.join(
            pathlib.Path(__file__).parent.absolute(), settings_filename
        )

        settings = {
            "series": self.test_series,
            "starting_pos": self.starting_pos,
            "ending_pos": self.ending_pos,
            "step_size": self.step_size,
            "averaging_time": self.averaging_time,
            "zero_offset": self.zero_offset,
        }

        self.load(settings)

        if None not in [setting.value for setting in settings.values()]:
            print("\nPreviously used settings:")
            for k, v in settings.items():
                print(f"{k}: {v}")
            choice = input(
                '\nWould you like to edit these settings?\n(enter "y" to edit or nothing to continue): '
            )
            if choice.lower() == "y":
                for setting in settings.values():
                    self.get_input(setting)
        else:
            for setting in settings.values():
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
        if setting.value:
            prompt_text += f"\nEnter {setting.name} or press enter to use previous value ({setting.value}): "
        else:
            prompt_text += f"\nEnter {setting.name}: "

        if setting.value:
            nv = input(prompt_text)
            if nv:
                setting.value = nv
        else:
            while setting.value is None:
                nts = input(prompt_text)
                if nts:
                    setting.value = nts


class Setting:
    def __init__(self, name=None, default_value=None, description=None):
        self.name = name
        self.value = default_value
        self.desc = description

    def __call__(self):
        return self.value

    def __repr__(self):
        return self.value


if __name__ == '__main__':
    IO(True)
