import os
import json
import logging

log = logging.getLogger(__name__)

class GameState:
    """Class to manage game state, data, saving, loading, and similar operations.
    """

    def __init__(   self,
                    path: str = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'saves'))
                ):
        """Initializes the game state, either by loading an existing save or by creating a new save.

        Args:
            path (str): Root path for save files. If not provided, defaults to "saves" folder in the project directory.
        """
        log.info(f"Initializing GameState with path: {path}")

        self.save_path = path
        log.debug(f"Save path set to: {self.save_path}")

        # Ensure the directory exists
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    def save_game(self, save: int = 0, autosave: bool = False):
        """Saves the game state to a file.

        Args:
            save (int): Slot to save to. Only needed if not an autosave. Is ignored if autosave is True.
            autosave (bool): Whether this is an autosave. Defaults to False.
        """

        if autosave or (save == 0):
            # Don't need to update the ID for an autosave
            log.info("Autosaving...")
        else:
            # Update the ID to match the targeted slot
            self.state['id'] = save
            log.info(f"Saving game to slot: {save}")

        save_file = os.path.join(self.save_path, f'{save if save != 0 else "auto"}.save')
        with open(save_file, 'w') as f:
            json.dump(self.state, f, indent=4)

    def load_save(self, save: int = 0):
        """Loads the game state from a file, or creates a new save if not present.

        Args:
            save (int): Save slot to load. The special value "0" is used for the autosave.
        """

        if (save == 0):
            log.info("Loading autosave...")
        else:
            log.info(f"Loading save slot: {save}")
        save_file = os.path.join(self.save_path, f'{save if save != 0 else "auto"}.save')
        if os.path.exists(save_file):
            # Load the save file
            with open(save_file, 'r') as f:
                self.state: dict = json.load(f)

            # Basic verification
            if (save != 0 and self.state['id'] != save):
                log.error(f"Save file ID {self.state['id']} does not match expected save slot {save}. This may indicate a corrupted save file.")
                raise ValueError(f"Save file ID {self.state['id']} does not match expected save slot {save}.\nThis may indicate a corrupted save file.")
            else:
                log.info(f"Successfully loaded save from slot {save} with ID {self.state['id']}.")
        else:
            if (save == 0):
                # We have to get a new slot, since we can't create an autosave without an existing save slot
                save = self.get_empty_save_slot()

            # Create a new save file with default data
            self.state: dict = {
                'id': save
            }
            self.save_game(save)
            log.info(f"Created new save at slot {save}.")

    def delete_save(self, save: int = 0, all_saves: bool = False):
        """Deletes a save file.

        Args:
            save (int): Save slot to delete. The special value "0" is used for the autosave.
            all_saves (bool): If True, deletes all saves. Defaults to False.
        """
        if all_saves:
            log.info("Deleting all saves...")
            for filename in os.listdir(self.save_path):
                if filename.endswith('.save'):
                    os.remove(os.path.join(self.save_path, filename))
            log.info("All saves deleted.")
        else:
            log.info(f"Deleting save slot: {save}")
            save_file = os.path.join(self.save_path, f'{save if save != 0 else "auto"}.save')
            if os.path.exists(save_file):
                os.remove(save_file)
                log.info(f"Save slot {save} deleted.")
            else:
                log.warning(f"Save slot {save} does not exist.")

    def get_empty_save_slot(self) -> int:
        """Finds the lowest numbered save slot that is not currently in use.

        Returns:
            int: The lowest numbered save slot that is not currently in use.
        """
        existing_saves = set()
        for filename in os.listdir(self.save_path):
            if filename.endswith('.save') and filename != 'auto.save':
                try:
                    existing_saves.add(int(filename.split('.')[0]))
                except ValueError as e:
                    log.warning(f"Failed to parse save file {filename}: {e}")

        # Find the lowest numbered save slot that is not currently in use
        save_slot = 1
        while save_slot in existing_saves:
            save_slot += 1
        log.debug(f"Found empty save slot: {save_slot}")

        return save_slot
