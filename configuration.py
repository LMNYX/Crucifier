from pickle import dump, load as pickle


class ConfigurationManager:
    version = 1

    # self return is to create chains, like for example:
    # config = ConfigurationManager().load().set("key", "value").save()
    # i have no clue how efficient it is, but it works (also idk how gc works on python)

    def get_version(self):
        return self.configuration["__version"]

    def __init__(self, file="config.bin"):
        self.file = file
        self.configuration = {
            "__version": ConfigurationManager.version,
            "osu_path": None,
            "audio": {
                "volume": 0.05
            },
            "rendering": {
                "fps_cap": 60
            }
        }
        return

    def set(self, key, value):
        self.configuration[key] = value
        return self

    def get(self, key):
        return [self.configuration[key], self]

    def save(self):
        with open(self.file, "wb") as f:
            pickle.dump(self.configuration, f)
        return self

    def load(self):
        with open(self.file, "rb") as f:
            self.configuration = pickle.load(f)
        return self
