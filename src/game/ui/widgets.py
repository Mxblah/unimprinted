import logging
from typing import Optional
from textual.widgets import Static
from textual.reactive import reactive
from src.game.state import GameState
from src.game.helpers.rooms import RoomManager

log = logging.getLogger(__name__)


# Room type to color mappings
ROOM_COLORS = {
    "base": "slategrey",
    "generator": "firebrick",
    "crafting": "gold",
}


class PowerDisplay(Static):
    """Widget to display facility-wide power information and confirm button."""

    def __init__(self, state: GameState):
        super().__init__()
        self.g = state
        self.state = state.state
        self.data = state.data

    def render(self) -> str:
        """Render the power information display."""
        RoomManager.recalculate_facility_power(self.state, self.data)
        power = self.state['facility']['power']
        total_gen = power.get('total', 0)
        available = power.get('available', 0)
        locked = power.get('locked', 0)

        # Determine color based on power status
        status_color = "green" if available >= 0 else "red"

        display = f"""┌{'─' * 78}┐
│ POWER STATUS{' ' * 65}│
│ Generated: {total_gen:>4}  │  Available: [{status_color}]{available:>4}[/{status_color}]  │  Locked: {locked:>4}{' ' * 25}│
│{' ' * 78}│
│ [Press SPACE to toggle rooms | ENTER on generators to adjust fuel]{' ' * 11}│
└{'─' * 78}┘"""
        # TODO: move the control explanation elsewhere; replace with the start day button
        return display


class RoomsList(Static):
    """Widget to display scrollable list of facility rooms."""

    selected_index = reactive(0)

    def __init__(self, state: GameState):
        super().__init__()
        self.g = state
        self.state = state.state
        self.data = state.data

    def render(self) -> str:
        """Render the list of rooms."""
        rooms = self.state['facility']['rooms']
        output = "ROOMS\n" + "─" * 39 + "\n"

        for idx, room in enumerate(rooms):
            room_data = RoomManager.get_room_data(room, self.data)
            is_selected = idx == self.selected_index
            is_online = room.get('online', True)

            # Get room display info
            display_name = room_data['display']['name']
            room_type = room['type']
            color = ROOM_COLORS.get(room_type, "white")

            # Format power info based on room type
            if room_type == 'generator':
                power_gen = RoomManager.get_room_power_generation(room, self.data)
                power_info = f"{power_gen}  pwr"
            else:
                power_draw = RoomManager.get_room_power_draw(
                    room,
                    self.state,
                    self.data
                )
                power_info = f"{power_draw} draw"

            # Styling
            prefix = "► " if is_selected else "  "
            dim = "[dim]" if not is_online else ""
            end_dim = "[/dim]" if not is_online else ""
            status = "(OFF)" if not is_online else ""

            line = f"{prefix}{dim}[{color}]{display_name:<28}[/{color}] {power_info:>8} {status}{end_dim}\n"
            output += line

        return output

    def get_selected_room(self) -> Optional[dict]:
        """Get the currently selected room."""
        rooms = self.state['facility']['rooms']
        if 0 <= self.selected_index < len(rooms):
            return rooms[self.selected_index]
        return None

    def select_room(self, index: int, room_detail: RoomDetail) -> None:
        """Selects a specific room via an index"""

        max_idx = len(self.state['facility']['rooms']) - 1
        if index > max_idx:
            self.selected_index = 0  # wraparound to the start
        elif index < 0:
            self.selected_index = max_idx  # wraparound to the end
        else:
            self.selected_index = index  # valid, inside the list bounds

        # Update detail pane and list
        selected = self.get_selected_room()
        if selected and room_detail:
            room_detail.update_room(selected)
        self.update(self.render())


class RoomDetail(Static):
    """Widget to display detailed information about selected room."""

    def __init__(self, state: GameState):
        super().__init__()
        self.g = state
        self.state = state.state
        self.data = state.data
        self.selected_room: Optional[dict] = None

    def render(self) -> str:
        """Render the detail pane."""
        if not self.selected_room:
            return "(Select a room for additional details)"

        room_data = RoomManager.get_room_data(self.selected_room, self.data)

        display = room_data['display']
        name = display['name']
        description = display['description']
        space = room_data['space']
        is_online = self.selected_room.get('online', True)
        room_type = self.selected_room['type']
        color = ROOM_COLORS.get(room_type, "white")

        # General details
        output = "ROOM DETAILS\n" + "─" * 38 + "\n"
        output += f"[{color}][bold]{name}[/bold][/{color}]\n"
        output += f"{description}\n"
        output += f"\nSpace: {space}\n"
        output += f"Status: {'[green]ONLINE[/green]' if is_online else '[red]OFFLINE[/red]'}\n"

        # Display power consumption
        output += "\n[bold]Power:[/bold]\n"
        power = room_data['power']
        total_space = self.state['facility']['space'].get('total', 0)

        if 'passive' in power:
            output += f"  Passive: {power['passive']}\n"
        if 'per_space' in power:
            scaled_draw = int(power['per_space'] * total_space)
            output += f"  Per Space: {power['per_space']} x {total_space} = {scaled_draw}\n"
        if 'active' in power:
            output += f"  [dim]Active: {power['active']}[/dim]\n"
        if 'per_thread' in power:
            output += f"  [dim]Per Thread: {power['per_thread']}[/dim]\n"

        # Show total draw
        total_draw = RoomManager.get_room_power_draw(
            self.selected_room,
            self.state,
            self.data
        )
        output += f"\n  [bold]Total: {total_draw}[/bold]\n"

        # Generator-specific info
        if room_type == 'generator':
            gen = room_data['generator']
            fuel_type = gen['consumes']['id']
            max_fuel = gen['consumes']['max_amount']
            current_fuel = self.selected_room.get('fuel_amount', 0)
            base_power = gen['generates']['base']
            per_fuel = gen['generates']['per_fuel']
            total_output = base_power + (current_fuel * per_fuel)

            output += "\n[bold]Generator:[/bold]\n"
            output += f"  Fuel Type: {fuel_type}\n"
            output += f"  Current Fuel: {current_fuel} / {max_fuel}\n"
            output += f"  Power Output: {total_output}\n"
            output += "\n[dim]Press ENTER to adjust fuel[/dim]"

        # Common toggle info
        if RoomManager.is_toggleable(room_type):
            output += "\n[dim]Press SPACE to toggle online/offline[/dim]\n"
        else:
            output += "\n[red]This room cannot be toggled[/red]\n"

        return output

    def update_room(self, room: Optional[dict]) -> None:
        """Update the displayed room."""
        self.selected_room = room
        self.update(self.render())

    def set_fuel_amount(self, amount: int) -> None:
        """Set the fuel amount for the selected generator."""
        if self.selected_room and self.selected_room['type'] == 'generator':
            RoomManager.set_generator_fuel(self.selected_room, amount, self.state, self.data)
            self.update(self.render())
