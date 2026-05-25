import json
import os

import pytest
from unittest.mock import patch
from src.game.state import GameState

class Test_GameState:
    """Tests for the GameState class
    """

    ### Fixtures ###

    @pytest.fixture
    def game_state(self):
        with patch('src.game.state.os.makedirs'):
            with patch('src.game.state.os.path.exists', return_value=True):
                return GameState()

    @pytest.fixture
    def tmp_game_state(self, tmp_path, save: int = 1):
        # An actually real directory, using tmp_path, for testing without mocks.
        g = GameState(path=str(tmp_path))
        g.state = {
            'id': save
        }
        return g

    ### Helper methods ###

    def check_save_id(self, path: str, id: int):
        assert os.path.exists(path), f"Expected save file at {path} does not exist."
        with open(path, 'r') as f:
            data = json.load(f)
            assert data['id'] == id, f"Expected ID {id}, but got {data['id']}"

    ### __init__() tests ###

    def test_initializes_with_default_path(self, game_state):
        # there has to be a better way to write this path
        assert game_state.save_path == os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'saves')), "Default save path should be '<root dir>/saves'"

    def test_creates_save_directory_if_not_exists(self, tmp_path):
        """Test that the save directory is created if it doesn't exist.
        """
        with patch('src.game.state.os.path.exists', return_value=False):
            with patch('src.game.state.os.makedirs') as mock_makedirs:
                GameState(path=str(tmp_path))
                mock_makedirs.assert_called_once_with(str(tmp_path))

    ### save_game() tests ###

    def test_autosaves_with_slot_0(self, tmp_game_state):
        tmp_game_state.save_game(save=0)
        expected_file = os.path.join(tmp_game_state.save_path, 'auto.save')
        self.check_save_id(path=expected_file, id=1)

    def test_saves_with_specified_slot(self, tmp_game_state):
        tmp_game_state.save_game(save=2)
        expected_file = os.path.join(tmp_game_state.save_path, '2.save')
        self.check_save_id(path=expected_file, id=2)

    ### load_save() tests ###

    @pytest.mark.parametrize("save_slot, expected_id", [
        (0, 1),  # Autosave should have ID 1
        (2, 2),  # Slot 2 should have ID 2
    ])
    def test_loads_save_with_correct_id(self, tmp_game_state, save_slot, expected_id):
        # First save to create the file
        tmp_game_state.save_game(save=save_slot)
        # Now load it into a new GameState instance to verify the contents
        g2 = GameState(path=tmp_game_state.save_path)
        g2.load_save(save=save_slot)
        assert g2.state['id'] == expected_id, f"Expected ID {expected_id} in save slot {save_slot}, but got {g2.state['id']}"

    def test_creates_new_save_if_file_not_exists(self, tmp_game_state):
        # Attempt to load a non-existent slot (e.g., slot 3)
        tmp_game_state.load_save(save=3)
        # Verify that the state was initialized with the correct ID (3)
        assert tmp_game_state.state['id'] == 3, f"Expected new save to have ID 3, but got {tmp_game_state.state['id']}"

    def test_gets_empty_slot_when_loading_nonexistent_autosave(self, tmp_game_state):
        with patch.object(tmp_game_state, 'get_empty_save_slot', return_value=5) as mock_get_empty:
            tmp_game_state.load_save(save=0)
            mock_get_empty.assert_called_once()

            # Verify that the new save was created with the ID returned by get_empty_save_slot(), and *not* auto.save
            assert tmp_game_state.state['id'] == 5, f"Expected new save to have ID 5, but got {tmp_game_state.state['id']}"
            self.check_save_id(os.path.join(tmp_game_state.save_path, '5.save'), 5)

    def test_raises_value_error_on_id_slot_mismatch(self, tmp_game_state):
        # Manually save a file with ID 1 in slot 2 to create a mismatch (using save_game() automatically prevents this problem!)
        with open(os.path.join(tmp_game_state.save_path, '2.save'), 'w') as f:
            json.dump({'id': 1}, f)

        # Now attempt to load it, which should raise a ValueError due to the mismatch
        with pytest.raises(ValueError, match="Save file ID 1 does not match expected save slot 2"):
            tmp_game_state.load_save(save=2)

    ### delete_save() tests ###

    def test_deletes_specific_save_slot(self, tmp_game_state):
        # First save to create the file
        tmp_game_state.save_game(save=2)
        expected_file = os.path.join(tmp_game_state.save_path, '2.save')
        assert os.path.exists(expected_file), "Save file should exist before deletion."

        # Now delete it
        tmp_game_state.delete_save(save=2)
        assert not os.path.exists(expected_file), "Save file should be deleted."

    def test_does_nothing_if_save_slot_does_not_exist(self, tmp_game_state):
        expected_file = os.path.join(tmp_game_state.save_path, '999.save')
        assert not os.path.exists(expected_file), "Save file should not exist before deletion."

        # Attempt to delete a non-existent save slot
        tmp_game_state.delete_save(save=999)
        assert not os.path.exists(expected_file), "Save file should still not exist after deletion attempt."

    def test_deletes_all_saves(self, tmp_game_state):
        # Create multiple save files
        for slot in range(1, 4):
            tmp_game_state.save_game(save=slot)
        assert len(os.listdir(tmp_game_state.save_path)) == 3, "Save files should exist before deletion."

        # Now delete all saves
        tmp_game_state.delete_save(all_saves=True)

        # Verify that all save files have been deleted
        assert len(os.listdir(tmp_game_state.save_path)) == 0, "All save files should be deleted."

    ### get_empty_save_slot() tests ###

    def test_returns_1_when_saves_directory_is_empty(self, game_state):
        with patch('src.game.state.os.listdir', return_value=[]):
            result = game_state.get_empty_save_slot()

        assert result == 1, "First available slot should be 1"

    def test_returns_2_when_slot_1_exists(self, game_state):
        with patch('src.game.state.os.listdir', return_value=['1.save']):
            result = game_state.get_empty_save_slot()

        assert result == 2

    def test_skips_autosave_file(self, game_state):
        with patch('src.game.state.os.listdir', return_value=['auto.save']):
            result = game_state.get_empty_save_slot()

        assert result == 1, "auto.save should not affect slot numbering"

    def test_finds_first_gap_in_save_slots(self, game_state):
        with patch('src.game.state.os.listdir', return_value=['1.save', '2.save', '4.save']):
            result = game_state.get_empty_save_slot()

        assert result == 3, "Should return the lowest available slot (3), not the next sequential (5)"

    def test_skips_misnamed_save_files(self, tmp_path):
        g = GameState(path=str(tmp_path))

        # Create some valid and invalid save files
        with open(os.path.join(tmp_path, '1.save'), 'w') as f:
            json.dump({'id': 1}, f)
        with open(os.path.join(tmp_path, 'invalid.save'), 'w') as f:
            json.dump({'id': 999}, f)
        with open(os.path.join(tmp_path, '3.save'), 'w') as f:
            json.dump({'id': 3}, f)

        # Should skip the invalid file and return the next available slot
        result = g.get_empty_save_slot()
        assert result == 2, "Should skip misnamed file and return slot 2"
