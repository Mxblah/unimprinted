import pytest
from src.game.helpers.rooms import RoomManager


class Test_RoomManager:
    """Tests for the RoomManager class"""

    ### Fixtures ###

    @pytest.fixture
    def room_data(self):
        """Standard room data structure for testing."""
        return {
            'facility': {
                'rooms': {
                    'base': {
                        'life-support': {
                            'id': 'life-support',
                            'type': 'base',
                            'power': {
                                'passive': 10,
                                'per_space': 0.5,
                            }
                        }
                    },
                    'generator': {
                        'medarial-gen': {
                            'id': 'medarial-gen',
                            'type': 'generator',
                            'power': {
                                'passive': 5,
                                'per_space': 0.1,
                            },
                            'generator': {
                                'type': 'fueled',
                                'generates': {
                                    'base': 100,
                                    'per_fuel': 10,
                                },
                                'consumes': {
                                    'id': 'medarial',
                                    'max_amount': 50,
                                }
                            }
                        }
                    },
                    'crafting': {
                        'clone-bay-basic': {
                            'id': 'clone-bay-basic',
                            'type': 'crafting',
                            'power': {
                                'passive': 20,
                                'per_thread': 15,
                            }
                        }
                    }
                }
            }
        }

    @pytest.fixture
    def room_state_base(self):
        """Standard base room state."""
        return {
            'id': 'life-support',
            'type': 'base',
            'online': True,
        }

    @pytest.fixture
    def room_state_generator(self):
        """Standard generator room state."""
        return {
            'id': 'medarial-gen',
            'type': 'generator',
            'online': True,
            'fuel_amount': 0,
        }

    @pytest.fixture
    def room_state_crafting(self):
        """Standard crafting room state."""
        return {
            'id': 'clone-bay-basic',
            'type': 'crafting',
            'online': True,
        }

    @pytest.fixture
    def game_state(self):
        """Standard game state structure."""
        return {
            'facility': {
                'space': {
                    'total': 100,
                },
                'power': {
                    'total': 0,
                    'available': 0,
                },
                'storage': {
                    'medarial': 0,
                },
                'rooms': [],
            }
        }

    ### get_room_data() tests ###

    def test_get_room_data_returns_full_room_data(self, room_data, room_state_base):
        """Should return the entire room data dict when key is empty string."""
        result = RoomManager.get_room_data(room_state_base, room_data, key="")

        assert isinstance(result, dict)
        assert result['id'] == 'life-support'
        assert result['type'] == 'base'
        assert 'power' in result

    def test_get_room_data_returns_subsection_with_key(self, room_data, room_state_base):
        """Should return the specified subsection when a key is provided."""
        result = RoomManager.get_room_data(room_state_base, room_data, key="power")

        assert isinstance(result, dict)
        assert 'passive' in result
        assert result['passive'] == 10
        assert result['per_space'] == 0.5

    def test_get_room_data_returns_empty_dict_for_missing_key(self, room_data, room_state_base):
        """Should return empty dict if the key doesn't exist in room data."""
        result = RoomManager.get_room_data(room_state_base, room_data, key="nonexistent")

        assert result == {}

    def test_get_room_data_handles_generator_room(self, room_data, room_state_generator):
        """Should correctly retrieve generator-specific data."""
        result = RoomManager.get_room_data(room_state_generator, room_data, key="generator")

        assert 'generates' in result
        assert 'consumes' in result
        assert result['generates']['base'] == 100

    ### is_toggleable() tests ###

    @pytest.mark.parametrize("room_type, expected", [
        ('base', False),
        ('generator', True),
        ('crafting', True),
        ('unknown_type', True),
    ])
    def test_is_toggleable(self, room_type, expected):
        """Should return correct toggleability based on room type."""
        assert RoomManager.is_toggleable(room_type) is expected

    ### toggle_room() tests ###

    def test_toggle_room_returns_false_for_immutable_type(self, room_state_base, game_state, room_data):
        """Should return False when attempting to toggle an immutable room type."""
        result = RoomManager.toggle_room(room_state_base, game_state, room_data)
        assert result is False

    @pytest.mark.parametrize("initial_online, expected_online", [
        (True, False),
        (False, True),
    ])
    def test_toggle_room_toggles_online_state(self, room_state_generator, game_state, room_data, initial_online, expected_online):
        """Should toggle room from online to offline or vice versa."""
        room_state_generator['online'] = initial_online

        result = RoomManager.toggle_room(room_state_generator, game_state, room_data)

        assert result is True
        assert room_state_generator['online'] is expected_online

    def test_toggle_room_clears_fuel_when_toggling_generator_offline(self, room_state_generator, game_state, room_data):
        """Should clear fuel amount when toggling a generator from online to offline."""
        room_state_generator['fuel_amount'] = 30

        RoomManager.toggle_room(room_state_generator, game_state, room_data)

        assert room_state_generator['fuel_amount'] == 0
        assert room_state_generator['online'] is False
        assert game_state['facility']['storage']['medarial'] == 30  # Fuel should be returned to storage

    def test_toggle_room_handles_missing_online_field(self, room_state_generator, game_state, room_data):
        """Should default online to True if field is missing."""
        del room_state_generator['online']

        result = RoomManager.toggle_room(room_state_generator, game_state, room_data)

        assert result is True
        assert room_state_generator['online'] is False

    ### set_generator_fuel() tests ###

    def test_set_generator_fuel_returns_false_for_non_generator(self, room_state_base, game_state, room_data):
        """Should return False when attempting to set fuel on a non-generator room."""
        result = RoomManager.set_generator_fuel(room_state_base, 20, game_state, room_data)
        assert result is False

    def test_set_generator_fuel_sets_fuel_successfully(self, room_state_generator, game_state, room_data):
        """Should successfully set fuel amount for a generator."""
        game_state['facility']['storage']['medarial'] = 100
        room_state_generator['fuel_amount'] = 0

        result = RoomManager.set_generator_fuel(room_state_generator, 30, game_state, room_data)

        assert result is True
        assert room_state_generator['fuel_amount'] == 30
        assert game_state['facility']['storage']['medarial'] == 70

    def test_set_generator_fuel_clamps_fuel_to_max_capacity(self, room_state_generator, game_state, room_data):
        """Should clamp fuel to the generator's max capacity."""
        game_state['facility']['storage']['medarial'] = 100
        room_state_generator['fuel_amount'] = 0

        # Try to set 100 fuel, but max is 50
        result = RoomManager.set_generator_fuel(room_state_generator, 100, game_state, room_data)

        assert result is True
        assert room_state_generator['fuel_amount'] == 50
        assert game_state['facility']['storage']['medarial'] == 50

    def test_set_generator_fuel_clamps_fuel_to_available_storage(self, room_state_generator, game_state, room_data):
        """Should clamp fuel to available storage amount."""
        game_state['facility']['storage']['medarial'] = 20
        room_state_generator['fuel_amount'] = 0

        # Try to set 50 fuel, but only 20 available
        result = RoomManager.set_generator_fuel(room_state_generator, 50, game_state, room_data)

        assert result is True
        assert room_state_generator['fuel_amount'] == 20
        assert game_state['facility']['storage']['medarial'] == 0

    def test_set_generator_fuel_handles_negative_fuel_input(self, room_state_generator, game_state, room_data):
        """Should clamp negative fuel to 0."""
        game_state['facility']['storage']['medarial'] = 100
        room_state_generator['fuel_amount'] = 30

        result = RoomManager.set_generator_fuel(room_state_generator, -10, game_state, room_data)

        assert result is True
        assert room_state_generator['fuel_amount'] == 0
        # Should have freed up 30 units of fuel back to storage
        assert game_state['facility']['storage']['medarial'] == 130

    def test_set_generator_fuel_decreases_fuel_correctly(self, room_state_generator, game_state, room_data):
        """Should correctly decrease fuel and return fuel to storage."""
        game_state['facility']['storage']['medarial'] = 50
        room_state_generator['fuel_amount'] = 40

        result = RoomManager.set_generator_fuel(room_state_generator, 10, game_state, room_data)

        assert result is True
        assert room_state_generator['fuel_amount'] == 10
        # Decreased by 30, so 30 should be returned to storage
        assert game_state['facility']['storage']['medarial'] == 80

    def test_set_generator_fuel_initializes_storage_if_missing(self, room_state_generator, game_state, room_data):
        """Should initialize storage for fuel type if it doesn't exist."""
        # Remove the fuel type from storage
        del game_state['facility']['storage']['medarial']
        room_state_generator['fuel_amount'] = 0

        result = RoomManager.set_generator_fuel(room_state_generator, 25, game_state, room_data)

        assert result is True
        # Fuel gets clamped to 0 since no storage available
        assert room_state_generator['fuel_amount'] == 0
        # Storage is initialized and set to 0 (since 0 units were consumed)
        assert game_state['facility']['storage']['medarial'] == 0

    def test_set_generator_fuel_handles_zero_fuel_request(self, room_state_generator, game_state, room_data):
        """Should handle setting fuel to 0."""
        game_state['facility']['storage']['medarial'] = 50
        room_state_generator['fuel_amount'] = 30

        result = RoomManager.set_generator_fuel(room_state_generator, 0, game_state, room_data)

        assert result is True
        assert room_state_generator['fuel_amount'] == 0
        assert game_state['facility']['storage']['medarial'] == 80

    ### get_room_power_draw() tests ###

    def test_get_room_power_draw_returns_zero_for_offline_room(self, room_state_base, game_state, room_data):
        """Offline rooms should draw no power."""
        room_state_base['online'] = False

        draw = RoomManager.get_room_power_draw(room_state_base, game_state, room_data)

        assert draw == 0

    def test_get_room_power_draw_includes_per_space_scaling(self, room_state_base, game_state, room_data):
        """Should include per_space scaling in power draw calculation."""
        # total space is 100, per_space is 0.5, so 100 * 0.5 = 50
        # passive is 10
        # total should be 60
        draw = RoomManager.get_room_power_draw(room_state_base, game_state, room_data)

        assert draw == 60

    def test_get_room_power_draw_handles_missing_online_field(self, room_state_base, game_state, room_data):
        """Should default online to True if field is missing."""
        del room_state_base['online']

        draw = RoomManager.get_room_power_draw(room_state_base, game_state, room_data)

        # Should still calculate as if online
        assert draw == 60

    def test_get_room_power_draw_handles_zero_space(self, room_state_base, game_state, room_data):
        """Should correctly calculate draw with zero total space."""
        game_state['facility']['space']['total'] = 0

        draw = RoomManager.get_room_power_draw(room_state_base, game_state, room_data)

        # Only passive draw (10)
        assert draw == 10

    ### get_room_power_generation() tests ###

    def test_get_room_power_generation_returns_zero_for_non_generator(self, room_state_base, room_data):
        """Non-generator rooms should generate no power."""
        generated = RoomManager.get_room_power_generation(room_state_base, room_data)

        assert generated == 0

    def test_get_room_power_generation_returns_zero_for_offline_generator(self, room_state_generator, room_data):
        """Offline generators should generate no power."""
        room_state_generator['online'] = False

        generated = RoomManager.get_room_power_generation(room_state_generator, room_data)

        assert generated == 0

    def test_get_room_power_generation_with_no_fuel(self, room_state_generator, room_data):
        """Should disable generation for a fueled generator when fuel is 0."""
        room_state_generator['fuel_amount'] = 0

        generated = RoomManager.get_room_power_generation(room_state_generator, room_data)

        assert generated == 0

    def test_get_room_power_generation_handles_deleted_fuel_amount(self, room_state_generator, room_data):
        """Should disable generation for a fueled generator when fuel_amount key is missing."""
        del room_state_generator['fuel_amount']

        generated = RoomManager.get_room_power_generation(room_state_generator, room_data)

        assert generated == 0

    def test_get_room_power_generation_with_fuel(self, room_state_generator, room_data):
        """Should calculate generation including fuel contribution."""
        room_state_generator['fuel_amount'] = 30

        # base is 100, per_fuel is 10, fuel is 30
        # total: 100 + (10 * 30) = 400
        generated = RoomManager.get_room_power_generation(room_state_generator, room_data)

        assert generated == 400

    def test_get_room_power_generation_handles_missing_online_field(self, room_state_generator, room_data):
        """Should default online to True if field is missing."""
        del room_state_generator['online']
        room_state_generator['fuel_amount'] = 10

        generated = RoomManager.get_room_power_generation(room_state_generator, room_data)

        # Should calculate as if online
        assert generated == 200  # 100 + (10 * 10)

    def test_get_room_power_generation_handles_missing_fuel_amount(self, room_state_generator, room_data):
        """Should default fuel_amount to 0 if field is missing."""
        del room_state_generator['fuel_amount']

        generated = RoomManager.get_room_power_generation(room_state_generator, room_data)

        # Should treat as 0 fuel
        assert generated == 0

    ### recalculate_facility_power() tests ###

    def test_recalculate_facility_power_with_single_generator(self, game_state, room_state_generator, room_data):
        """Should correctly calculate power with a single generator."""
        room_state_generator['fuel_amount'] = 20
        game_state['facility']['rooms'] = [room_state_generator]

        RoomManager.recalculate_facility_power(game_state, room_data)

        # Generator generates: 100 + (10 * 20) = 300
        # Generator draws: 5 (passive) + 0.1 * 100 (per_space) = 15
        # available: 300 - 15 = 285
        assert game_state['facility']['power']['total'] == 300
        assert game_state['facility']['power']['available'] == 285

    def test_recalculate_facility_power_with_multiple_generators(self, game_state, room_state_generator, room_data):
        """Should sum power from multiple generators."""
        gen1 = room_state_generator.copy()
        gen1['fuel_amount'] = 10

        # Create second generator
        gen2 = {
            'id': 'another-gen',
            'type': 'generator',
            'online': True,
            'fuel_amount': 15,
        }

        game_state['facility']['rooms'] = [gen1, gen2]

        # Manually add the second generator to room data
        room_data['facility']['rooms']['generator']['another-gen'] = {
            'id': 'another-gen',
            'type': 'generator',
            'power': {
                'passive': 5,
                'per_space': 0.1,
            },
            'generator': {
                'generates': {
                    'base': 100,
                    'per_fuel': 10,
                },
                'consumes': {
                    'id': 'medarial',
                    'max_amount': 50,
                }
            }
        }

        RoomManager.recalculate_facility_power(game_state, room_data)

        # gen1: 100 + (10 * 10) = 200
        # gen2: 100 + (10 * 15) = 250
        # total generated: 450
        assert game_state['facility']['power']['total'] == 450

    def test_recalculate_facility_power_with_consumer_room(self, game_state, room_state_base, room_state_generator, room_data):
        """Should subtract power consumption from available power."""
        room_state_generator['fuel_amount'] = 1
        game_state['facility']['rooms'] = [room_state_generator, room_state_base]

        RoomManager.recalculate_facility_power(game_state, room_data)

        # Generator generates: 100 + (10 * 1) = 110
        # Generator draws: 5 + (0.1 * 100) = 15
        # Base draws: 10 + (0.5 * 100) = 60
        # available: 110 - 15 - 60 = 35
        assert game_state['facility']['power']['total'] == 110
        assert game_state['facility']['power']['available'] == 35

    def test_recalculate_facility_power_resets_values(self, game_state, room_state_generator, room_data):
        """Should reset power values at the start of calculation."""
        game_state['facility']['power']['total'] = 999
        game_state['facility']['power']['available'] = 999
        game_state['facility']['rooms'] = [room_state_generator]

        RoomManager.recalculate_facility_power(game_state, room_data)

        # Values should be recalculated, not have 999 in them
        assert game_state['facility']['power']['total'] != 999

    def test_recalculate_facility_power_ignores_offline_generators(self, game_state, room_state_generator, room_state_base, room_data):
        """Should not count offline generators in total power."""
        room_state_generator['online'] = False
        room_state_generator['fuel_amount'] = 100
        game_state['facility']['rooms'] = [room_state_generator, room_state_base]

        RoomManager.recalculate_facility_power(game_state, room_data)

        # Offline generator shouldn't contribute to total
        assert game_state['facility']['power']['total'] == 0

    def test_recalculate_facility_power_counts_offline_generator_consumption(self, game_state, room_state_generator, room_data):
        """Should not count power draw from offline generators."""
        room_state_generator['online'] = False
        room_state_generator['fuel_amount'] = 100
        game_state['facility']['rooms'] = [room_state_generator]

        RoomManager.recalculate_facility_power(game_state, room_data)

        # Offline generator shouldn't draw power
        assert game_state['facility']['power']['available'] == 0

    def test_recalculate_facility_power_with_negative_available(self, game_state, room_state_base, room_data):
        """Should correctly calculate negative available power (power deficit)."""
        # Create a generator that produces very little
        room_state_base['online'] = True

        game_state['facility']['rooms'] = [room_state_base]
        # Reduce total space so per_space draw is minimal
        game_state['facility']['space']['total'] = 0

        RoomManager.recalculate_facility_power(game_state, room_data)

        # No generators, only base room consuming 10 power
        assert game_state['facility']['power']['total'] == 0
        assert game_state['facility']['power']['available'] == -10

    def test_recalculate_facility_power_with_empty_rooms_list(self, game_state, room_data):
        """Should handle empty rooms list."""
        game_state['facility']['rooms'] = []

        RoomManager.recalculate_facility_power(game_state, room_data)

        assert game_state['facility']['power']['total'] == 0
        assert game_state['facility']['power']['available'] == 0

    def test_recalculate_facility_power_complex_scenario(self, game_state, room_state_generator, room_state_base, room_state_crafting, room_data):
        """Should correctly calculate complex scenario with multiple room types."""
        room_state_generator['fuel_amount'] = 25

        game_state['facility']['rooms'] = [
            room_state_generator,
            room_state_base,
            room_state_crafting,
        ]

        RoomManager.recalculate_facility_power(game_state, room_data)

        # Generator produces: 100 + (10 * 25) = 350
        # Generator draws: 5 + (0.1 * 100) = 15
        # Base draws: 10 + (0.5 * 100) = 60
        # Crafting draws: 20 (no per_space for crafting)
        # available: 350 - 15 - 60 - 20 = 255
        assert game_state['facility']['power']['total'] == 350
        assert game_state['facility']['power']['available'] == 255
