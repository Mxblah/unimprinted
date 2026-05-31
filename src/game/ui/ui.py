import logging
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from src.game.state import GameState
from src.game.facility import Facility
from src.game.ui.widgets import PowerDisplay, RoomsList, RoomDetail
from src.game.helpers.rooms import RoomManager

log = logging.getLogger(__name__)


class GameUI(App):
    """Main user interface class for the game. Contains the main game loop and all interactive elements.
    """

    # TODO: extract the start-of-day UI to a separate screen or mode, rather than being the whole app
    BINDINGS = [
        Binding("up", "select_room_up", "Up", show=False),
        Binding("down", "select_room_down", "Down", show=False),
        Binding("space", "toggle_room", "Toggle Room", show=False),
        Binding("enter", "enter_room", "Enter Room", show=False),
        Binding("q", "quit", "Quit"),
    ]

    CSS_PATH = "ui.tcss"

    def __init__(self, state: GameState, facility: Facility):
        super().__init__()
        self.state = state.state
        self.data = state.data
        self.g = state
        self.f = facility

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        with Vertical():
            with Horizontal(id="main_container"):
                self.rooms_list = RoomsList(self.g)
                self.rooms_list.id = "rooms_list"
                yield self.rooms_list

                self.room_detail = RoomDetail(self.g)
                self.room_detail.id = "room_detail"
                yield self.room_detail

            self.power_display = PowerDisplay(self.g)
            self.power_display.id = "power_display"
            yield self.power_display

    def on_mount(self) -> None:
        """Initialize the UI after mounting."""
        log.debug("GameUI mounted: initializing display")

        # Show the first room's details and do initial power calculation
        if self.rooms_list:
            first_room = self.rooms_list.get_selected_room()
            if first_room and self.room_detail:
                self.room_detail.update_room(first_room)
        self.power_display.update(self.power_display.render())

    def action_select_room_up(self) -> None:
        """Move selection up in the rooms list."""
        self.rooms_list.select_room(self.rooms_list.selected_index - 1, self.room_detail)

    def action_select_room_down(self) -> None:
        """Move selection down in the rooms list."""
        self.rooms_list.select_room(self.rooms_list.selected_index + 1, self.room_detail)

    def action_toggle_room(self) -> None:
        """Toggle selected room online/offline."""
        selected = self.rooms_list.get_selected_room() if self.rooms_list else None
        if not selected:
            return

        if RoomManager.toggle_room(selected, self.state, self.data):
            # Successfully toggled; recalculate power
            RoomManager.recalculate_facility_power(self.state, self.data)

            # Update displays
            self.rooms_list.update(self.rooms_list.render())
            self.room_detail.update_room(selected)
            self.power_display.update(self.power_display.render())
        else:
            # Room couldn't be toggled
            self.notify(
                f"[red]Cannot toggle {selected['id']}: "
                f"this room type is immutable[/red]"
            )

    def action_enter_room(self) -> None:
        """Handle enter on selected room (adjust fuel for generators, other actions later)."""
        selected = self.rooms_list.get_selected_room() if self.rooms_list else None
        if not selected:
            return

        if selected['type'] == 'generator':
            # TODO
            pass
