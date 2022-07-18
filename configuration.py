import pickle
from os.path import exists


def returns_self(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        return self
    return wrapper


class BaseConfig:
    """
    Contains some configuration functions used in multiple classes.
    """

    @returns_self
    def set(self, key, value):
        config = self.get(".".join(key.split(".")[:-1]))
        config[key] = value

    def get(self, key):
        attr = self.configuration
        if key != "":
            for attr_name in key.split("."):
                attr = attr[attr_name]
        return attr

    def getm(self, *keys):
        attributes = []
        for key in keys:
            attributes.append(self.get(key))
        return attributes


class ConfigurationManager(BaseConfig):
    version = 2

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
                "resolution": Config(self, {
                    "width": 640,
                    "height": 480,
                }),
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
    def save(self):
        with open(self.file, "wb") as f:
            pickle.dump(self.configuration, f)

    @classmethod
    def load(cls, file="config.bin"):
        if not exists(file):
            return cls(file)
        with open(file, "rb") as f:
            config = pickle.load(f)
            print(config["audio"].get("volume"))
            return cls(file, config)

    @property
    def config_version(self):
        return self.configuration["__version"]


class Config(BaseConfig):
    def __init__(self, parent, values):
        self.parent = parent
        self.configuration = values

    def __contains__(self, item):
        return item in self.configuration

    def __len__(self):
        return len(self.configuration)

    def __iter__(self):
        return self.keys()

    def __setitem__(self, key, value):
        self.configuration[key] = value

    def __getitem__(self, item):
        return self.configuration[item]

    def __delitem__(self, key):
        del self.configuration[key]

    def items(self):
        return self.configuration.items()

    def keys(self):
        return self.configuration.keys()

    def values(self):
        return self.configuration.values()
