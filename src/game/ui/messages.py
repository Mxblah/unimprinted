"""Message classes for inter-widget communication in the game UI."""

from textual.message import Message


class RoomSelected(Message):
    """Posted when a room is selected in the RoomsList.

    Attributes:
        room_index: Index of the selected room in facility.rooms list.
    """

    def __init__(self, room_index: int) -> None:
        super().__init__()
        self.room_index = room_index


class FuelAdjusted(Message):
    """Posted when fuel is committed for a generator in RoomDetail.

    Attributes:
        room_index: Index of the room in facility.rooms list.
        fuel_amount: The new fuel amount set for the generator.
    """

    def __init__(self, room_index: int, fuel_amount: int) -> None:
        super().__init__()
        self.room_index = room_index
        self.fuel_amount = fuel_amount
