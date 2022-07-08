import pickle
from os.path import exists


def returns_self(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        return self
    return wrapper


class ConfigurationManager:
    version = 1

    # self return is to create chains, like for example:
    # config = ConfigurationManager().load().set("key", "value").save()
    # i have no clue how efficient it is, but it works (also idk how gc works on python)

    def __init__(self, file="config.bin", config=None):
        self.file = file
        self.configuration = {
            "__version": ConfigurationManager.version,
            "songs_path": None,
            "audio": Config(self, {
                "volume": 0.05,
            }),
            "rendering": Config(self, {
                "fps_cap": 60,
            })
        }

        def assign_config(default, new):
            for key, value in new.items():
                if key == "__version":
                    continue
                if isinstance(value, Config):
                    assign_config(default[key], value)
                elif key in default:
                    default[key] = value

        if config is not None:
            assign_config(self.configuration, config)


    @returns_self
    def set(self, key, value):
        self.configuration[key] = value

    def get(self, key):
        return self.configuration[key]

    @returns_self
    def save(self):
        with open(self.file, "wb") as f:
            pickle.dump(self.configuration, f)

    @classmethod
    def load(cls, file="config.bin"):
        if not exists(file):
            return cls(file)
        with open(file, "rb") as f:
            config = pickle.load(f)
            if config["__version"] != cls.version:
                return cls(file, config.configuration)
            return config

    @property
    def config_version(self):
        return self.configuration["__version"]


class Config:
    def __init__(self, parent, values):
        self.parent = parent
        self.config = values

    @returns_self
    def set(self, key, value):
        self.config[key] = value

    def get(self, key):
        return self.config[key]

    def __contains__(self, item):
        return item in self.config

    def __len__(self):
        return len(self.config)

    def __iter__(self):
        return self.keys()

    def __setitem__(self, key, value):
        self.config[key] = value

    def __getitem__(self, item):
        return self.config[item]

    def __delitem__(self, key):
        del self.config[key]

    def items(self):
        return self.config.items()

    def keys(self):
        return self.config.keys()

    def values(self):
        return self.config.values()
