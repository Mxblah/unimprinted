import logging
import argparse
import colorlog
from src.game.state import GameState
from src.game.facility import Facility

# Arg parsing
parser = argparse.ArgumentParser()
parser.add_argument('-?', action='help', help='show this help message and exit.')

parser.add_argument('-s', '--save', type=int, default=0, help='The save slot to load or create. The special value "0" is used for the autosave.')
parser.add_argument('-d', '--delete', type=int, help='The save slot to delete. The special value "0" is used for the autosave.')
parser.add_argument('-D', '--delete-all', action='store_true', help='Delete all saves.')
parser.add_argument('-l', '--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='WARNING', help='Set the logging level.')

args = parser.parse_args()

# Configure colored logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)-8s %(message)s%(reset)s',
    log_colors={
        'TRACE': 'bold_black',
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
))
root_logger = colorlog.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(getattr(logging, args.log_level))

# Logger for the entrypoint
log = logging.getLogger(__name__)

# Initialize the state
g = GameState()

# Clean up saves if requested
if args.delete is not None:
    g.delete_save(save=args.delete)
if args.delete_all:
    g.delete_save(all_saves=True)

# Load or create the save
g.load_save(args.save)

# Instantiate the facility and start the game loop
f = Facility(g)
f.show_facility_menu()
