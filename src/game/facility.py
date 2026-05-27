import logging
from src.game.state import GameState

log = logging.getLogger(__name__)


class Facility:
    """Class that represents the main facility in the game. Directly or indirectly handles all base-related systems.
    """

    def __init__(self, state: GameState):
        # Rejigger some common attributes to be more accessible for ease of use
        self.state = state.state
        self.data = state.data
        self.g = state

        # This is a new game (or something has gone catastrophically wrong with the save), so we need to initialize the facility.
        if (not self.state.get('facility')):
            log.info("No facility data found in save. Initializing new facility with default settings...")
            self.state['facility'] = self.data['defaults']['facility']

            # We also have to start the first day here since it's brand new
            self.start_day()

    def start_day(self):

        # Init day if not already set
        if (not self.state['facility']['day']):
            self.state['facility']['day'] = 1

        # todo: logic to start the day

        # Autosave after finishing so we don't have to do the setup again during a reload.
        self.g.save_game(autosave=True)
        log.info(f'🌅 Starting day {self.state['facility']['day']}...')

    def show_facility_menu(self):
        """Presents the main game interface where the player can perform facility-related tasks. This is the main game loop.
        """

        pass
        # todo: this is where the TUI goes. workin' on it.

    def end_day(self):

        # Autosave before starting in case we get interrupted (i.e. in the summary), so the player doesn't lose the whole day.
        self.g.save_game(autosave=True)
        log.info(f'🌇 Ending day {self.state['facility']['day']}...')

        # Perform end-day steps such as displaying a summary and incrementing the day
        self.show_day_summary()
        self.state['facility']['day'] += 1

        # Start the next day
        self.start_day()

    def show_day_summary(self):
        pass
        # todo!
