"""Tests for UI messages."""

import pytest
from src.game.ui.messages import RoomSelected, FuelAdjusted


class Test_RoomSelected:
    """Tests for RoomSelected message."""

    def test_room_selected_creation(self):
        """Test RoomSelected message can be created with room_index."""
        msg = RoomSelected(room_index=2)
        assert msg.room_index == 2

    def test_room_selected_different_indices(self):
        """Test RoomSelected works with various indices."""
        for idx in [0, 1, 5, 100]:
            msg = RoomSelected(idx)
            assert msg.room_index == idx


class Test_FuelAdjusted:
    """Tests for FuelAdjusted message."""

    def test_fuel_adjusted_creation(self):
        """Test FuelAdjusted message can be created with room_index and fuel_amount."""
        msg = FuelAdjusted(room_index=1, fuel_amount=50)
        assert msg.room_index == 1
        assert msg.fuel_amount == 50

    @pytest.mark.parametrize("room_idx, fuel", [
        (0, 0),
        (1, 100),
        (5, 999),
        (10, 0),
    ])
    def test_fuel_adjusted_various_values(self, room_idx, fuel):
        """Test FuelAdjusted works with various fuel amounts."""
        msg = FuelAdjusted(room_idx, fuel)
        assert msg.room_index == room_idx
        assert msg.fuel_amount == fuel
