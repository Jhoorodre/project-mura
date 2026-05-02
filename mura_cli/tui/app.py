from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

class MuraTUI(App):
    """A Textual app to manage Project Mura."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Project Mura Management Console")
        yield Static("Welcome! (UI under development)")
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

if __name__ == "__main__":
    app = MuraTUI()
    app.run()
