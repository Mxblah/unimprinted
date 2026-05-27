import os
from pathlib import Path
import json
import logging
import time
import uuid

log = logging.getLogger(__name__)


class GameState:
    """Class to manage game state, data, saving, loading, and similar operations.
    """

    def __init__(self,
                 path: str = str((Path(__file__).parent.parent.parent / 'saves').absolute()),
                 data_path: str = str((Path(__file__).parent.parent.parent / 'data').absolute())):
        """Initializes the game state, either by loading an existing save or by creating a new save.

        Args:
            path (str): Root path for save files. If not provided, defaults to "saves" folder in the project directory.
            data_path (str): Path to the default save data file.
        """
        log.info(f"Initializing GameState with path: {path}")

        self.save_path = path
        self.data_path = data_path
        log.debug(f"Save path set to: {self.save_path}")
        log.debug(f"Data path set to: {self.data_path}")
        self.load_data()

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
            log.info("📝 Autosaving...")
        else:
            # Update the ID to match the targeted slot
            self.state['id'] = save
            log.info(f"📝 Saving game to slot: {save}")

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
            log.debug(f"No save file found at slot {save}. Creating new save...")
            if (save == 0):
                # We have to get a new slot, since we can't create an autosave without an existing save slot
                save = self.get_empty_save_slot()

            # Create a new save file with default data
            try:
                with open(os.path.join(self.data_path, 'defaults', 'save.json'), 'r') as f:
                    self.state = json.load(f)
                    self.state['id'] = save
                    self.state['uuid'] = str(uuid.uuid4())
            except FileNotFoundError:
                log.error("Default save data not found. Cannot create new save. (Has the data directory been deleted?)")
                raise
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

    def load_data(self):
        """Loads game data from the data directory. This is not the state data, but rather defaults, definitions, and other required information.
        """

        log.info("📚 Loading game data...")
        self.data = {}
        start_time = time.time()

        # Walk all data files and load each one into self.data based on their path/filename
        for root, dirs, files in os.walk(self.data_path):
            for filename in files:
                if filename.endswith('.json'):
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, self.data_path)
                    path_parts = os.path.splitext(relative_path)[0].split(os.sep)

                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)

                        # Navigate/create nested dictionaries
                        current = self.data
                        for part in path_parts[:-1]:
                            # log.debug(f"Creating nested dictionary for part: {part}")
                            current = current.setdefault(part, {})

                        # Store data at the final key
                        current[path_parts[-1]] = data
                        # log.debug(f"Loaded data file: {'/'.join(path_parts)}")
                    except Exception as e:
                        log.error(f"Failed to load data file {'/'.join(path_parts)}: {e}")

        # This can take a while, so the diagnostics are welcome
        end_time = time.time()
        log.info(f"📚 Finished loading game data in {end_time - start_time:.2f} seconds.")

        # print(json.dumps(self.data, indent=2))  # debug test
