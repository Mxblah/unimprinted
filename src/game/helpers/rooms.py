import logging

log = logging.getLogger(__name__)


class RoomManager:
    """Manages room state operations and validations for the facility."""

    # Room types that cannot be toggled
    IMMUTABLE_TYPES: set[str] = {"base"}

    @classmethod
    def get_room_data(cls, room: dict, data: dict, key: str = "") -> dict:
        """Helper function to get the room data definition for a given room state.

        Args:
            room (dict): The room state dict.
            data (dict): The game data dict.
            key (str, optional): An optional key to specify a sub-section of the room data (e.g. 'power' or 'generator').

        Returns:
            dict: The room data definition.
        """
        room_data = data['facility']['rooms'][room['type']][room['id']]
        return room_data.get(key, {}) if (key != "") else room_data

    @classmethod
    def is_toggleable(cls, room_type: str) -> bool:
        """Check if a room type can be toggled online/offline.

        Args:
            room_type (str): The type of room (base, generator, crafting, etc.)

        Returns:
            bool: True if the room can be toggled, False otherwise.
        """
        return room_type not in cls.IMMUTABLE_TYPES

    @classmethod
    def toggle_room(cls, room: dict, state: dict, data: dict) -> bool:
        """Toggle a room between online and offline states.

        Args:
            room (dict): The room state dict to toggle.
            state (dict): The game state dict.
            data (dict): The game data dict.

        Returns:
            bool: True if toggle was successful, False if room cannot be toggled.
        """
        room_type: str = room.get('type')  # type: ignore (will always be string if data is valid)

        # Fail to toggle if not allowed
        if not cls.is_toggleable(room_type):
            log.warning(
                f"Cannot toggle room {room.get('id')} - "
                f"rooms of type '{room_type}' are immutable"
            )
            return False

        # If toggling a generator offline, clear its fuel
        if room_type == 'generator' and room.get('online', True):
            cls.set_generator_fuel(room, 0, state, data)

        # Flip the bool
        room['online'] = not room.get('online', True)
        log.debug(
            f"Room {room.get('id')} toggled to "
            f"{'online' if room['online'] else 'offline'}"
        )
        return True

    @classmethod
    def set_generator_fuel(cls, room: dict, fuel: int, state: dict, data: dict) -> bool:
        """Set the fuel level for a generator room.

        Args:
            room (dict): The room state dict (must be a generator).
            fuel (int): The fuel amount to set.
            state (dict): The game state dict.
            data (dict): The game data dict.

        Returns:
            bool: True if fuel was set successfully, False otherwise.
        """

        if room.get('type') != 'generator':
            log.warning(f"Cannot set fuel for non-generator room {room.get('id')}")
            return False

        # Verify we have enough fuel in storage
        gen = cls.get_room_data(room, data, 'generator')
        fuel_type = gen.get('consumes', {}).get('id')
        max_fuel = gen.get('consumes', {}).get('max_amount', 0)
        available_fuel = state['facility']['storage'].setdefault(fuel_type, 0)

        # Clamp fuel to valid range
        clamped_fuel = max(0, min(fuel, max_fuel, available_fuel))

        if clamped_fuel != fuel:
            log.debug(
                f"Generator {room.get('id')} fuel clamped "
                f"from {fuel} to {clamped_fuel}"
            )

        # Set fuel and remove the amount used from storage (or put it back if the fuel amount decreased)
        diff: int = clamped_fuel - room.get('fuel_amount', 0)
        room['fuel_amount'] = clamped_fuel
        state['facility']['storage'][fuel_type] -= diff
        log.debug(
            f"{room.get('id')}: fuel set to {clamped_fuel}"
            f"Consumed from storage: {diff} / Remaining: {state['facility']['storage'][fuel_type]}"
        )
        return True

    @classmethod
    def get_room_power_draw(
        cls,
        room: dict,
        state: dict,
        data: dict
    ) -> int:
        """Calculate the total power draw for a room.

        Handles passive draw, active draw, per_space scaling, etc.

        Args:
            room (dict): The room state dict.
            state (dict): The game state dict.
            data (dict): The game data dict.

        Returns:
            int: Total power draw as an integer.
        """

        # Offline rooms draw no power
        is_online = room.get('online', True)
        if not is_online:
            return 0

        # Init values, get room data
        total_space = state['facility']['space'].get('total', 0)
        power = cls.get_room_data(room, data, 'power')
        total_draw = 0

        # Passive power draw
        total_draw += power.get('passive', 0)

        # Per-space scaling
        if 'per_space' in power:
            total_draw += int(power['per_space'] * total_space)

        # Per-thread draw (for crafting rooms)
        if 'per_thread' in power:
            # TODO: Get active thread count once crafting is implemented
            pass

        # Note: active draw is not handled here, as it's consumed upon the player taking an action rather than a constant draw.

        log.debug(f"{room['id']}: drawing {total_draw} power")
        return total_draw

    @classmethod
    def get_room_power_generation(
        cls,
        room: dict,
        data: dict,
    ) -> int:
        """Calculate the total power generation for a generator room.

        Args:
            room (dict): The room state dict.
            data (dict): The game data dict.

        Returns:
            int: Total power generation as an integer, or 0 if not a generator.
        """

        # Only generators generate power
        if room.get('type') != 'generator':
            return 0

        # ... and only if they're online
        is_online = room.get('online', True)
        if not is_online:
            return 0

        # Calculate power
        gen = cls.get_room_data(room, data, 'generator')
        base_power = gen.get('generates', {}).get('base', 0)
        per_fuel = gen.get('generates', {}).get('per_fuel', 0)
        fuel_amount = room.get('fuel_amount', 0)

        # Fueled generators cannot generate power without fuel
        if fuel_amount <= 0 and cls.get_room_data(room, data, 'generator').get('type') == 'fueled':
            log.debug(f"{room['id']} is a fueled generator with no fuel. Setting generated power to 0.")
            generated_power = 0
        else:
            generated_power: int = int(base_power + (per_fuel * fuel_amount))

        log.debug(f"{room['id']}: generating {generated_power} power with {fuel_amount} fuel")
        return generated_power

    @classmethod
    def recalculate_facility_power(cls, state: dict, data: dict) -> None:
        """Recalculate all facility power values after state changes.

        Updates:
        - facility.power.total (generated power)
        - facility.power.available (generated - consumed)
        - facility.storage (consumes fuel from storage)

        Args:
            state (dict): The game state dict.
            data (dict): The game data dict.
        """
        # Reset power values
        state['facility']['power']['total'] = 0
        state['facility']['power']['available'] = 0

        for room in state['facility']['rooms']:
            room_type = room.get('type')
            room_id = room.get('id')

            # Power generation from generators
            if room_type == 'generator' and room.get('online', True):
                generated: int = cls.get_room_power_generation(room, data)
                state['facility']['power']['total'] += generated
                state['facility']['power']['available'] += generated

            # Power consumption from all online rooms
            if room.get('online', True):
                draw: int = cls.get_room_power_draw(room, state, data)
                state['facility']['power']['available'] -= draw
                if draw > 0:
                    log.debug(f"Available after {room_id}: {state['facility']['power']['available']}")

        # Add generated power to available
        log.debug(
            f"Power calculation complete: "
            f"total={state['facility']['power']['total']}, "
            f"available={state['facility']['power']['available']}"
        )
