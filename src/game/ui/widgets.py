import logging
from typing import Optional
from textual.widgets import Static, ListView, ListItem, Label
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


class RoomsList(ListView):
    """Widget to display scrollable list of facility rooms."""

    def __init__(self, state: GameState):
        super().__init__()
        self.g = state
        self.state = state.state
        self.data = state.data

    def _format_room_label(self, room: dict) -> tuple[str, str]:
        """Return the label text and room type for a room entry."""
        room_data = RoomManager.get_room_data(room, self.data)
        is_online = room.get('online', True)

        # Get room display info
        display_name = room_data['display']['name']
        room_type = room['type']

        # Format power info based on room type
        if room_type == 'generator':
            power_gen = RoomManager.get_room_power_generation(room, self.data)
            power_info = f"{power_gen:>4} pwr "
        else:
            power_draw = RoomManager.get_room_power_draw(
                room,
                self.state,
                self.data
            )
            power_info = f"{power_draw:>4} draw"

        # Build display text with status
        status = " [reverse]OFF[/]" if not is_online else ""
        dim_start = "[dim]" if not is_online else ""
        dim_end = "[/dim]" if not is_online else ""
        label_text = f"{dim_start}{display_name:<28} {power_info}{status}{dim_end}"
        return label_text, room_type

    def _build_room_item(self, idx: int, room: dict) -> ListItem:
        """Construct a ListItem for a room entry."""
        label_text, room_type = self._format_room_label(room)
        return ListItem(
            Label(label_text),
            classes=f"room-item room-type-{room_type}",
            id=f"room-item-{idx}"
        )

    def compose(self):
        """Compose the list of room items."""
        rooms = self.state['facility']['rooms']
        for idx, room in enumerate(rooms):
            yield self._build_room_item(idx, room)

    def refresh_room_item(self, index: int) -> None:
        """Refresh a specific room list item from the current state."""
        rooms = self.state['facility']['rooms']
        if index is None or not (0 <= index < len(rooms)):
            return

        room = rooms[index]
        label_text, room_type = self._format_room_label(room)

        # Get the list item by its index, then update its label with the new text
        item = self.children[index]
        if item is None:
            return

        label = item.query_one(Label)
        label.update(label_text)

    def get_selected_room(self) -> Optional[dict]:
        """Get the currently selected room."""
        rooms = self.state['facility']['rooms']
        if self.index is not None and 0 <= self.index < len(rooms):
            return rooms[self.index]
        return None


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
