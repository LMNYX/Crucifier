import argparse
from configuration import ConfigurationManager


parser = argparse.ArgumentParser(description='osu!simulation')
parser.add_argument('--width', '-sw', type=int)
parser.add_argument('--height', '-sh', type=int)
parser.add_argument("--fps", '-f', type=int)
parser.add_argument('--volume', '-v', type=int)
args = parser.parse_args()

config = ConfigurationManager.load()

if args.width is not None:
    config.set("rendering.resolution.width", args.width)
if args.height is not None:
    config.set("rendering.resolution.height", args.height)
if args.fps is not None:
    config.set("rendering.fps_cap", args.fps)
if args.volume is not None:
    config.set("audio.volume", args.volume)
config.save()


from game import GameLoop
from startscreen import StartScreen
from gameplay import Gameplay


states = {
    "start": StartScreen,
    "play": Gameplay
}

game = GameLoop(states, config)
game.run("start")
