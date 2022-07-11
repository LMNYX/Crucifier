from os import path
import pygame
from enums import SkinOption


class ResourceManager:
    def __init__(self, resolution):
        self.resolution = resolution
        self.path = "resources"
        self.skin = SkinManager(
            path.join(self.path, "default_skin"), resolution)
        self.beatmap = BeatmapResourceManager()

        pekora = pygame.image.load(path.join(self.path, "pekora.png"))
        self.pekora = pygame.transform.smoothscale(pekora, (128, 128))
        self.font_size = int(16 * self.resolution.screen_size[1] / 1080)
        self.font = pygame.font.Font(
            path.join(self.path, "Torus.otf"), self.font_size)
        self.pekora_font = pygame.font.Font(
            path.join(self.path, "Torus.otf"), int(24 * self.resolution.screen_size[1] / 1080))

    def load_skin(self, skin_path):
        self.skin.path = skin_path
        self.skin.load_skin()

    def load_map(self, map_path):
        self.beatmap.path = map_path
        self.beatmap.load_map()
        self.skin.on_new_beatmap()


class BaseManager:
    def load_image(self, name):
        a = name.split(".")
        base_name, ext = ".".join(a[:-1]), a[-1]
        hd = path.join(self.path, f"{base_name}@2x.{ext}")
        if path.exists(hd):
            return pygame.image.load(hd)
        return pygame.image.load(path.join(self.path, name))

    def load_audio(self, name):
        pass


class SkinManager(BaseManager):
    """
    Manages all the resources of a skin such as hit objects and hit sounds.
    """

    def __init__(self,  skin_path, resolution):
        self.resolution = resolution
        self.path = skin_path
        self.config = SkinConfigParser(path.join(skin_path, "skin.ini"))

        self.load_skin()

    def load_skin(self):
        self._hitcircle = self.load_image("hitcircle.png")
        self.hitcircle = None

    def on_new_beatmap(self):
        self.hitcircle = pygame.transform.smoothscale(self._hitcircle, (self.resolution.object_size,
                                                                        self.resolution.object_size))


class SkinConfigParser:
    LATEST_VERSION = "2.7"
    VALID_VERSIONS = ["1.0", "2.0", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"]
    configs = {  # Config name: default value
        "Name": "",
        "Author": "",
        "Version": "1.0",
        "AnimationFramerate": -1,
        "AllowSliderBallTint": False,
        "ComboBurstRandom": False,
        "CursorCentre": True,
        "CursorRotate": True,
        "CursorTrailRotate": True,
        "CustomComboBurstSounds": [],
        "HitCircleOverlayAboveNumber": True,
        "LayeredHitSounds": True,
        "SliderBallFlip": True,
        "SpinnerFadePlayfield": False,
        "SpinnerFrequencyModule": True,
        "SpinnerNoBlink": False,
        "Combo1": (255, 192, 0),
        "Combo2": (0, 202, 0),
        "Combo3": (18, 124, 255),
        "Combo4": (242, 24, 57),
        "Combo5": None,
        "Combo6": None,
        "Combo7": None,
        "Combo8": None,
        "InputOverlayText": (0, 0, 0),
        "MenuGlow": (0, 78, 155),
        "SliderBall": (2, 170, 255),
        "SliderBorder": (255, 255, 255),
        "SliderTrackOverride": SkinOption.CURRENT_COMBO_COLOR,
        "SongSelectActiveText": (0, 0, 0),
        "SongSelectInactiveText": (255, 255, 255),
        "SpinnerBackground": (100, 100, 100),
        "StarBreakAdditive": (255, 182, 193),
        "HitCirclePrefix": "default",
        "HitCircleOverlap": -2,
        "ScorePrefix": "score",
        "ScoreOverlap": 0,
        "ComboPrefix": "score",
        "ComboOverlap": 0,

        # TODO: CatchTheBeat and Mania sections
    }

    def __init__(self, skin_ini_path):
        self.path = skin_ini_path

        file_exists = path.exists(self.path)

        # Default values
        self.version = self.LATEST_VERSION if not file_exists else self.configs["Version"]
        for config, default in self.configs.items():
            if config == "Version":
                continue
            setattr(self, self.format_name(config), default)

        if file_exists:
            self.load_config()

        self.combo_colors = []
        for i in (2, 3, 4, 5, 6, 7, 8, 1):
            color = getattr(self, f"combo_{i}")
            if color is not None:
                self.combo_colors.append(color)

    def load_config(self):
        with open(self.path, "r") as f:
            for line in f.readlines():
                if not line.strip():
                    continue
                split = line.split(":")
                var = split[0].strip()
                if var not in self.configs:
                    continue

                value = ":".join(split[1:]).strip()
                default_value = self.configs[var]
                if isinstance(default_value, tuple):
                    value = tuple(map(lambda n: int(n.strip()), value.split(",")))
                elif isinstance(default_value, int):
                    value = int(value)
                elif isinstance(default_value, bool):
                    value = bool(value)
                elif isinstance(default_value, list):
                    value = list(map(str.strip, value.split(",")))

                if var == "Version" and value not in self.VALID_VERSIONS:
                    self.version = "1.0"
                    continue

                setattr(self, self.format_name(var), value)

    @staticmethod
    def format_name(name):
        name = name[0].lower() + name[1:]
        return "".join([char if char.islower() else "_"+char.lower() for char in name])


class BeatmapResourceManager(BaseManager):
    """
    Manages all the resources of a beatmap such as background, custom skin elements, hit sounds, etc.
    """

    def __init__(self):
        pass

    def load_map(self):
        pass
