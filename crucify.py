from game import Game
from enums import Gamemode
import argparse

#
parser = argparse.ArgumentParser(description='osu!simulation')
parser.add_argument('--gamemode', '-g', type=int, nargs='+',
                    help='gamemode that is supposed to be played')
parser.add_argument('--width', '-sw', type=int, default=600)
parser.add_argument('--height', '-sh', type=int, default=480)
parser.add_argument("--fps", '-f', type=int, default=960)
parser.add_argument('--borderless', '-b', action='store_true')
parser.add_argument('--no-cache', '-nc', action='store_true')
args = parser.parse_args()
#

gamemode = Gamemode(
    args.gamemode[0]) if args.gamemode is not None else Gamemode(0)

print("Gamemode set to:", gamemode)

print("Please wait until the maps are loaded...")

game = Game([args.width, args.height], args.fps, gamemode,
            is_borderless=args.borderless,
            is_caching_enabled=not args.no_cache)
game.run()
