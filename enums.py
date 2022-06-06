from enum import Enum


class Gamemode(Enum):
    STD = 0
    MANIA = 1
    TAIKO = 2
    CTB = 3  # NOBODY GIVES A FUCK ABOUT IT.


class DebugMode(Enum):
    NO = 0
    FEW = 1
    FULL = 2
