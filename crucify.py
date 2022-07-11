from game import Game
from beatmap_reader import GameMode
from dotenv import load_dotenv
import argparse

load_dotenv()

#
parser = argparse.ArgumentParser(description='osu!simulation')
parser.add_argument('--gamemode', '-g', type=int, nargs='+',
                    help='gamemode that is supposed to be played')
parser.add_argument('--width', '-sw', type=int, default=640)
parser.add_argument('--height', '-sh', type=int, default=480)
parser.add_argument("--fps", '-f', type=int, default=-1)
parser.add_argument('--volume', '-v', type=int, default=-1)
parser.add_argument('--debug-mode', '-d', type=int, default=0)
parser.add_argument('--borderless', '-b', action='store_true')
parser.add_argument('--no-cache', '-nc', action='store_false')
parser.add_argument('--reset-cache', '-rc', action='store_true')
parser.add_argument('--no-background', '-nb', action='store_false')
parser.add_argument('--no-audio', '-na', action='store_false')
args = parser.parse_args()
#

gamemode = GameMode(
    args.gamemode[0]) if args.gamemode is not None else GameMode.STANDARD

print("Gamemode set to:", gamemode)

print("Please wait until the maps are loaded...")

game = Game([args.width, args.height], args.fps, gamemode,
            is_borderless=args.borderless,
            is_caching_enabled=args.no_cache,
            should_reset_cache=args.reset_cache,
            is_background_enabled=args.no_background,
            is_audio_enabled=args.no_audio,
            default_volume=args.volume,
            debug_mode=args.debug_mode
            )
game.run()
