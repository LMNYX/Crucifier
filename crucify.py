import utilities
import argparse
import os
import time

#
parser = argparse.ArgumentParser(description='osu!simulation')
parser.add_argument('--gamemode', '-g', type=int, nargs='+',
                    help='gamemode that is supposed to be played')
parser.add_argument('--width', '-sw', type=int, default=600)
parser.add_argument('--height', '-sh', type=int, default=480)
parser.add_argument('--borderless', '-b', action='store_true')
args = parser.parse_args()
#

if(args.gamemode == None):
    gamemode = utilities.Gamemode(0)
else:
    gamemode = utilities.Gamemode(args.gamemode[0])

print("Gamemode set to:", gamemode)

MapCollector = utilities.MapCollector()
MapCollector.Collect()
print(MapCollector.GetMapset(0))
print(MapCollector.GetRandomMapset())
print(MapCollector.GetRandomMap())

Game = utilities.Game([args.width, args.height],
                      gamemode, isBorderless=args.borderless)
Game.Start()
