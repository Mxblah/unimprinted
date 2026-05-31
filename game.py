import logging
import argparse
import os
from textual.logging import TextualHandler
from src.game.state import GameState
from src.game.facility import Facility
from src.game.ui.ui import GameUI

# Arg parsing
parser = argparse.ArgumentParser()
parser.add_argument('-?', action='help', help='show this help message and exit.')

parser.add_argument('-s', '--save', type=int, default=0, help='The save slot to load or create. The special value "0" is used for the autosave.')
parser.add_argument('-d', '--delete', type=int, help='The save slot to delete. The special value "0" is used for the autosave.')
parser.add_argument('-D', '--delete-all', action='store_true', help='Delete all saves.')
parser.add_argument('-l', '--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='WARNING', help='Set the logging level.')
parser.add_argument('-L', '--log-file', type=str, help='Path to the desired log file.', default=os.path.join('logs', 'game.log'))
parser.add_argument('--delete-log-file', '--init-log-file', action='store_true', help='Delete the log file before starting the game.')

args = parser.parse_args()

# Clean / init the logfile
if args.delete_log_file and os.path.exists(args.log_file):
    os.remove(args.log_file)

# Configure file logging
logging.basicConfig(
    level=getattr(logging, args.log_level),
    format='%(asctime)s %(levelname)-8s %(name)s: %(message)s',
    handlers=[
        # No console logging as Textual overrides it
        logging.FileHandler(filename=args.log_file, encoding='utf-8'),
        TextualHandler()
    ]
)
# Logger for the entrypoint
log = logging.getLogger(__name__)
log.info("==================== Starting Unimprinted ====================")

# Initialize the state
g = GameState()

# Clean up saves if requested
if args.delete is not None:
    g.delete_save(save=args.delete)
if args.delete_all:
    g.delete_save(all_saves=True)

# Load or create the save
g.load_save(args.save)

# Instantiate the facility
f = Facility(g)

# Instantiate the UI and start the game loop
ui = GameUI(g, f)
ui.run()
