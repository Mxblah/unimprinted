import logging
from typing import Optional
from textual import events
from textual.containers import Horizontal
from textual.validation import Integer
from textual.widgets import Static, ListView, ListItem, Label, Input
from textual.message import Message
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
└{'─' * 78}┘"""
        # TODO: add the start day button
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
        self.detail_body: Optional[Static] = None
        self.fuel_input: Optional[Input] = None

    class RefreshItem(Message):
        """Message to refresh various parts of the UI after state changes."""

        def __init__(self, refresh_power: bool = False, refresh_room: Optional[dict] = None, state: Optional[dict] = None):
            super().__init__()
            self.refresh_power = refresh_power
            self.room_index = None

            if refresh_room and state:
                try:
                    self.room_index = state['facility']['rooms'].index(refresh_room)
                except ValueError:
                    log.warning(f"RefreshItem created with refresh_room but room id '{refresh_room.get('id', '<unknown>')}' not found in state; room index will not be set.")
            elif refresh_room:
                log.warning("RefreshItem created with refresh_room but no state provided; room index will not be set.")

    def compose(self):
        if not self.selected_room:
            yield Static("(Select a room for additional details)", id="room_detail_placeholder")
            return

        # Shared room details at the top
        self.detail_body_top = Static(self._format_room_text(), id="room_detail_body_top")
        yield self.detail_body_top

        if self.selected_room['type'] == 'generator':
            room_generator = RoomManager.get_room_data(self.selected_room, self.data, 'generator')
            max_fuel = room_generator['consumes']['max_amount']
            current_fuel = self.selected_room.get('fuel_amount', 0)

            # Generator header
            yield Static("[bold]Generator:[/bold]\n  Fuel Type: " + room_generator['consumes']['id'], id="generator_header")

            # Horizontal row for current fuel with inline input
            with Horizontal(classes="auto-size"):
                yield Static("  Current Fuel: ", classes="auto-size")
                self.fuel_input = Input(
                    placeholder=f"0..{max_fuel}",
                    id="fuel_input_inline",
                    disabled=False,
                    value=str(current_fuel),
                    classes="inline-input",
                    validators=[
                        Integer(minimum=0, maximum=max_fuel)
                    ],
                    compact=True,
                )
                yield self.fuel_input
                yield Static(f" / {max_fuel}", classes="auto-size")

            # Power output and hint
            total_output = RoomManager.get_room_power_generation(room_generator, self.data)
            yield Static(f"  Power Output: {total_output}\n\n[dim]Press TAB to adjust fuel[/dim]", id="generator_footer")

        # Toggle/footer info
        if RoomManager.is_toggleable(self.selected_room['type']):
            yield Static("[dim]Press SPACE to toggle online/offline[/dim]", id="room_detail_footer")
        else:
            yield Static("[red]This room cannot be toggled[/red]", id="room_detail_footer")

    def _format_room_text(self) -> str:
        """Provide the formatted text to display for the currently selected room."""
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

        return output

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input is not self.fuel_input:
            return  # not our input, ignore
        if not self.selected_room or self.selected_room['type'] != 'generator':
            return  # we aren't a generator, ignore

        raw_value = event.value.strip()
        if raw_value == "":
            return  # it's empty, ignore
        if event.validation_result and not event.validation_result.is_valid:
            if self.fuel_input is not None:
                # Input field is not a valid integer, so reset it to the current fuel amount
                self.fuel_input.value = str(self.selected_room.get('fuel_amount', 0))
                return

        # Hooray, it's a valid integer! Set the fuel amount to it.
        requested_amount = int(raw_value)
        requested_amount = max(0, requested_amount)
        self.set_fuel_amount(requested_amount)
        if self.fuel_input is not None:
            # Update input field to the clamped/validated value (clears things like leading zeroes)
            self.fuel_input.value = str(requested_amount)

    # Allow escape to unfocus fuel input and return to room list
    def on_key(self, event: events.Key) -> None:
        if event.key == 'escape' and self.fuel_input is not None and self.fuel_input.has_focus:
            if self.app is not None:
                self.app.set_focus(self.app.query_one(RoomsList))
            event.stop()

    def update_room(self, room: Optional[dict]) -> None:
        """Update the displayed room."""
        self.selected_room = room
        self.refresh(recompose=True)

    def focus_fuel_input(self) -> None:
        if self.fuel_input is not None and not self.fuel_input.disabled and self.app is not None:
            self.app.set_focus(self.fuel_input)

    def set_fuel_amount(self, amount: int) -> None:
        """Set the fuel amount for the selected generator."""
        if self.selected_room and self.selected_room['type'] == 'generator':
            if RoomManager.set_generator_fuel(self.selected_room, amount, self.state, self.data):
                RoomManager.recalculate_facility_power(self.state, self.data)
                self.post_message(self.RefreshItem(refresh_power=True, refresh_room=self.selected_room, state=self.state))

                # Also update the generator footer with the new power output
                try:
                    footer = self.query_one("#generator_footer", Static)
                except Exception:
                    footer = None
                if footer is not None:
                    total_output = RoomManager.get_room_power_generation(self.selected_room, self.data)
                    footer.update(f"  Power Output: {total_output}\n\n[dim]Press TAB to adjust fuel[/dim]")
