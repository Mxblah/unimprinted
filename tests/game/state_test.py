import json
import os
from pathlib import Path

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
                with patch('src.game.state.GameState.load_data'):
                    return GameState()

    @pytest.fixture
    def tmp_game_state(self, tmp_path, save: int = 1):
        # An actually real directory, using tmp_path, for testing without mocks.
        g = GameState(path=str(tmp_path), data_path=str(tmp_path / 'data'))
        g.state = {
            'id': save
        }
        return g

    @pytest.fixture
    def tmp_game_state_with_data(self, tmp_path, save: int = 1):
        # Create a proper data directory structure with a default save.json
        data_path = tmp_path / 'data'
        defaults_path = data_path / 'defaults'
        defaults_path.mkdir(parents=True)

        default_save = {
            'id': None,
            'config': {},
            'options': {}
        }
        with open(defaults_path / 'save.json', 'w') as f:
            json.dump(default_save, f)

        tmp_game_state = GameState(path=str(tmp_path), data_path=str(data_path))
        tmp_game_state.data = {'defaults': {'save': default_save}}
        tmp_game_state.state = {
            'id': save
        }
        return tmp_game_state

    ### Helper methods ###

    def check_save_id(self, path: str, id: int):
        assert os.path.exists(path), f"Expected save file at {path} does not exist."
        with open(path, 'r') as f:
            data = json.load(f)
            assert data['id'] == id, f"Expected ID {id}, but got {data['id']}"

    ### __init__() tests ###

    def test_initializes_with_default_paths(self, game_state):
        assert game_state.save_path == str((Path(__file__).parent.parent.parent / 'saves').absolute()), "Default save path should be '<root dir>/saves'"
        assert game_state.data_path == str((Path(__file__).parent.parent.parent / 'data').absolute()), "Default data path should be '<root dir>/data'"

    def test_initializes_with_custom_paths(self, tmp_path):
        custom_save_path = str(tmp_path / 'custom_saves')
        custom_data_path = str(tmp_path / 'custom_data')

        with patch('src.game.state.os.makedirs'):
            with patch('src.game.state.os.path.exists', return_value=True):
                with patch('src.game.state.GameState.load_data'):
                    g = GameState(path=custom_save_path, data_path=custom_data_path)
                    assert g.save_path == custom_save_path
                    assert g.data_path == custom_data_path

    def test_calls_load_data_on_init(self, tmp_path):
        with patch('src.game.state.os.makedirs'):
            with patch('src.game.state.os.path.exists', return_value=True):
                with patch.object(GameState, 'load_data') as mock_load_data:
                    GameState(path=str(tmp_path))
                    mock_load_data.assert_called_once()

    def test_creates_save_directory_if_not_exists(self, tmp_path):
        """Test that the save directory is created if it doesn't exist.
        """
        with patch('src.game.state.os.path.exists', return_value=False):
            with patch('src.game.state.os.makedirs') as mock_makedirs:
                with patch('src.game.state.GameState.load_data'):
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

    def test_creates_new_save_if_file_not_exists(self, tmp_game_state_with_data):

        # Attempt to load a non-existent slot (e.g., slot 3)
        tmp_game_state_with_data.load_save(save=3)
        # Verify that the state was initialized with the correct ID (3)
        assert tmp_game_state_with_data.state['id'] == 3, f"Expected new save to have ID 3, but got {tmp_game_state_with_data.state['id']}"
        # Verify that uuid was added
        assert 'uuid' in tmp_game_state_with_data.state, "Expected new save to have a uuid"
        assert tmp_game_state_with_data.state['uuid'] != '', "UUID should not be empty"

    def test_gets_empty_slot_when_loading_nonexistent_autosave(self, tmp_game_state_with_data):

        with patch.object(tmp_game_state_with_data, 'get_empty_save_slot', return_value=5) as mock_get_empty:
            tmp_game_state_with_data.load_save(save=0)
            mock_get_empty.assert_called_once()

            # Verify that the new save was created with the ID returned by get_empty_save_slot(), and *not* auto.save
            assert tmp_game_state_with_data.state['id'] == 5, f"Expected new save to have ID 5, but got {tmp_game_state_with_data.state['id']}"
            self.check_save_id(os.path.join(tmp_game_state_with_data.save_path, '5.save'), 5)

    def test_raises_value_error_on_id_slot_mismatch(self, tmp_game_state):
        # Manually save a file with ID 1 in slot 2 to create a mismatch (using save_game() automatically prevents this problem!)
        with open(os.path.join(tmp_game_state.save_path, '2.save'), 'w') as f:
            json.dump({'id': 1}, f)

        # Now attempt to load it, which should raise a ValueError due to the mismatch
        with pytest.raises(ValueError, match="Save file ID 1 does not match expected save slot 2"):
            tmp_game_state.load_save(save=2)

    def test_raises_file_not_found_error_when_default_save_missing(self, tmp_path):
        # Create GameState with a data_path that doesn't have a defaults/save.json
        data_path = tmp_path / 'data'
        data_path.mkdir()

        g = GameState(path=str(tmp_path), data_path=str(data_path))
        g.data = {}

        # Try to load a non-existent save, which should fail when trying to load the default save.json
        with pytest.raises(FileNotFoundError):
            g.load_save(save=1)

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

    ### load_data() tests ###

    def test_load_data_loads_single_json_file(self, tmp_path):
        # Create a simple data directory with one JSON file
        data_path = tmp_path / 'data'
        data_path.mkdir()

        test_data = {'key': 'value', 'number': 42}
        with open(data_path / 'test.json', 'w') as f:
            json.dump(test_data, f)

        g = GameState(path=str(tmp_path), data_path=str(data_path))
        # load_data() was called in __init__, so we can check the result
        assert 'test' in g.data, "test.json should be loaded as g.data['test']"
        assert g.data['test'] == test_data, "Data should match the JSON file contents"

    def test_load_data_creates_nested_structure(self, tmp_path):
        # Create a nested directory structure with JSON files
        data_path = tmp_path / 'data'
        facility_path = data_path / 'facility' / 'rooms' / 'base'
        facility_path.mkdir(parents=True)

        room_data = {'name': 'Life Support', 'type': 'base'}
        with open(facility_path / 'life-support.json', 'w') as f:
            json.dump(room_data, f)

        g = GameState(path=str(tmp_path), data_path=str(data_path))

        # Check that the nested structure was created correctly
        assert g.data['facility']['rooms']['base']['life-support'] == room_data

    def test_load_data_loads_multiple_files(self, tmp_path):
        # Create multiple JSON files
        data_path = tmp_path / 'data'
        data_path.mkdir()

        test_data1 = {'file': 'one'}
        test_data2 = {'file': 'two'}
        test_data3 = {'file': 'three'}

        with open(data_path / 'first.json', 'w') as f:
            json.dump(test_data1, f)
        with open(data_path / 'second.json', 'w') as f:
            json.dump(test_data2, f)
        with open(data_path / 'third.json', 'w') as f:
            json.dump(test_data3, f)

        g = GameState(path=str(tmp_path), data_path=str(data_path))

        assert g.data['first'] == test_data1
        assert g.data['second'] == test_data2
        assert g.data['third'] == test_data3

    def test_load_data_ignores_non_json_files(self, tmp_path):
        # Create a mix of JSON and non-JSON files
        data_path = tmp_path / 'data'
        data_path.mkdir()

        test_data = {'valid': 'json'}
        with open(data_path / 'valid.json', 'w') as f:
            json.dump(test_data, f)
        with open(data_path / 'ignored.txt', 'w') as f:
            f.write('This should be ignored')
        with open(data_path / 'ignored.md', 'w') as f:
            f.write('# This should also be ignored')

        g = GameState(path=str(tmp_path), data_path=str(data_path))

        assert 'valid' in g.data
        assert 'ignored' not in g.data
        assert len(g.data) == 1, "Only the JSON file should be loaded"

    def test_load_data_handles_invalid_json_gracefully(self, tmp_path):
        # Create a JSON file with invalid JSON content
        data_path = tmp_path / 'data'
        data_path.mkdir()

        # Create a valid JSON file and an invalid one
        valid_data = {'valid': 'json'}
        with open(data_path / 'valid.json', 'w') as f:
            json.dump(valid_data, f)

        with open(data_path / 'invalid.json', 'w') as f:
            f.write('{invalid json content')

        # load_data() should handle the error gracefully
        g = GameState(path=str(tmp_path), data_path=str(data_path))

        # Valid file should still be loaded
        assert 'valid' in g.data
        # Invalid file should not be loaded (but should have logged an error)
        assert 'invalid' not in g.data or g.data.get('invalid') is None

    def test_load_data_with_empty_directory(self, tmp_path):
        # Create an empty data directory
        data_path = tmp_path / 'data'
        data_path.mkdir()

        g = GameState(path=str(tmp_path), data_path=str(data_path))

        # data should be an empty dictionary
        assert isinstance(g.data, dict)
        assert len(g.data) == 0, "Empty data directory should result in empty data dict"
