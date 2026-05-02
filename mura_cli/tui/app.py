from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, Label, Input, ContentSwitcher, DataTable, Log, TextArea
from textual.message import Message
from mura_cli.core.manager import ProjectManager
from mura_cli.core.fetcher import MetadataFetcher
from mura_cli.core.importer import DriveImporter
from mura_cli.core.merger import ChapterMerger
import asyncio
import pyperclip
from pathlib import Path

manager = ProjectManager()
fetcher = MetadataFetcher()
drive_importer = DriveImporter()
merger = ChapterMerger()

class MangaListScreen(Static):
    """A list view showing all mangas in the catalog."""
    
    def on_mount(self) -> None:
        self.refresh_list()

    def refresh_list(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Title", "Section", "Latest")
        
        cat = manager.load_catalogo()
        for item in cat.get("items", []):
            table.add_row(
                item.get("mangaId", ""),
                item.get("title", ""),
                item.get("seccion", ""),
                item.get("latest", ""),
                key=item.get("mangaId")
            )

    def compose(self) -> ComposeResult:
        yield DataTable(cursor_type="row")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        manga_id = str(event.row_key.value)
        self.app.selected_manga_id = manga_id
        self.app.action_switch_to("manage")

class AddMangaForm(Static):
    """A form to add or edit a manga with full metadata."""
    
    class MangaAdded(Message):
        """Sent when a manga is added."""
        def __init__(self, manga_id: str) -> None:
            self.manga_id = manga_id
            super().__init__()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="form-scroll"):
            with Vertical(id="form-container"):
                yield Label("Manga Information", id="form-title")
                
                with Horizontal(classes="form-row"):
                    with Vertical():
                        yield Label("Slug/ID:")
                        yield Input(placeholder="oshi-no-ko", id="manga-id")
                    with Vertical():
                        yield Label("Auto-Fill Action:")
                        yield Button("Auto-Fill (AniList/Baka)", variant="primary", id="btn-autofill")
                
                yield Label("Title:")
                yield Input(placeholder="Title", id="title")
                
                yield Label("Synopsis:")
                yield TextArea(id="synopsis", show_line_numbers=False)
                
                with Horizontal(classes="form-row"):
                    with Vertical():
                        yield Label("Author(s):")
                        yield Input(placeholder="Author 1, Author 2", id="authors")
                    with Vertical():
                        yield Label("Artist(s):")
                        yield Input(placeholder="Artist 1", id="artists")

                with Horizontal(classes="form-row"):
                    with Vertical():
                        yield Label("Section:")
                        yield Input(placeholder="activos/joints/terminados", id="section", value="activos")
                    with Vertical():
                        yield Label("Year:")
                        yield Input(placeholder="2024", id="year")

                yield Label("Tags (Genres):")
                yield Input(placeholder="Action, Fantasy, Drama", id="tags")
                
                yield Label("Cover Image URL/Path:")
                yield Input(placeholder="assets/img/cover.jpg", id="portada")

                with Horizontal(id="form-actions"):
                    yield Button("Save Manga", variant="success", id="btn-save")
                    yield Button("Cancel", variant="error", id="btn-cancel")
                
                yield Static("", id="status-msg")

    def prefill(self, manga_id: str):
        self.query_one("#form-title").update(f"Editing: [b]{manga_id}[/b]")
        self.query_one("#manga-id").value = manga_id
        self.query_one("#manga-id").disabled = True
        
        cat = manager.load_catalogo()
        m_item = next((i for i in cat["items"] if i["mangaId"] == manga_id), {})
        
        local_data = fetcher.fetch_local(manga_id) or {}
        
        self.query_one("#title").value = m_item.get("title") or local_data.get("title", "")
        self.query_one("#section").value = m_item.get("seccion", "activos")
        self.query_one("#tags").value = ",".join(m_item.get("tags") or local_data.get("genres", []))
        self.query_one("#portada").value = m_item.get("portada") or local_data.get("portada", "")
        
        self.query_one("#synopsis").text = local_data.get("synopsis", "")
        self.query_one("#authors").value = ", ".join(local_data.get("authors", []))
        self.query_one("#artists").value = ", ".join(local_data.get("artists", []))
        self.query_one("#year").value = str(local_data.get("year", ""))

    def reset_form(self):
        self.query_one("#form-title").update("Add New Manga")
        self.query_one("#manga-id").value = ""
        self.query_one("#manga-id").disabled = False
        self.query_one("#title").value = ""
        self.query_one("#synopsis").text = ""
        self.query_one("#authors").value = ""
        self.query_one("#artists").value = ""
        self.query_one("#section").value = "activos"
        self.query_one("#year").value = ""
        self.query_one("#tags").value = ""
        self.query_one("#portada").value = ""
        self.query_one("#status-msg").update("")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-autofill":
            m_id = self.query_one("#manga-id").value
            if not m_id:
                self.query_one("#status-msg").update("Please enter a slug first.")
                return
            
            self.query_one("#status-msg").update("Searching all APIs...")
            loop = asyncio.get_event_loop()
            metadata = await loop.run_in_executor(None, fetcher.auto_fill, m_id, m_id)
            
            if metadata:
                self.query_one("#title").value = metadata.get("title", "")
                self.query_one("#synopsis").text = metadata.get("synopsis", "")
                self.query_one("#authors").value = ", ".join(metadata.get("authors", []))
                self.query_one("#artists").value = ", ".join(metadata.get("artists", []))
                self.query_one("#tags").value = ",".join(metadata.get("genres", []))
                self.query_one("#portada").value = metadata.get("portada", "")
                self.query_one("#year").value = str(metadata.get("year", ""))
                self.query_one("#status-msg").update(f"Found on {metadata['source']}!")
            else:
                self.query_one("#status-msg").update("Metadata not found.")
        
        elif event.button.id == "btn-save":
            m_id = self.query_one("#manga-id").value
            title = self.query_one("#title").value
            sec = self.query_one("#section").value
            tags = [t.strip() for t in self.query_one("#tags").value.split(",") if t.strip()]
            portada = self.query_one("#portada").value
            
            manager.add_manga(
                m_id, title, sec, tags, portada,
                synopsis=self.query_one("#synopsis").text,
                authors=[a.strip() for a in self.query_one("#authors").value.split(",") if a.strip()],
                artists=[a.strip() for a in self.query_one("#artists").value.split(",") if a.strip()],
            )
            self.app.notify(f"Manga {title} saved!")
            self.post_message(self.MangaAdded(m_id))
        
        elif event.button.id == "btn-cancel":
            self.app.action_switch_to("list")

class ManageMangaScreen(Static):
    """Screen to manage a specific manga (Drive import, edit, etc)."""

    def compose(self) -> ComposeResult:
        with Vertical(id="manage-container"):
            yield Label("Manage Manga", id="manage-title")
            
            with Horizontal(id="meta-actions"):
                yield Button("Edit Metadata", variant="primary", id="btn-edit-meta")
                yield Button("Delete Manga", variant="error", id="btn-delete-manga")
            
            yield Label("Google Drive Folder ID:")
            yield Input(placeholder="Paste Drive ID here", id="drive-id")
            yield Button("Import Chapters from Drive", variant="primary", id="btn-import")
            
            with Horizontal(id="action-buttons"):
                yield Button("Rebuild Site", variant="warning", id="btn-rebuild")
                yield Button("Sync to GitHub", variant="default", id="btn-sync")
                
            yield Label("Operation Log:")
            yield Log(id="op-log")
            yield Button("Copy Log to Clipboard", id="btn-copy-log")
            yield Button("Back to List", id="btn-back")

    def update_info(self) -> None:
        m_id = getattr(self.app, "selected_manga_id", "None")
        self.query_one("#manage-title").update(f"Managing: [b]{m_id}[/b]")

    async def run_process(self, cmd: list, task_name: str):
        log = self.query_one("#op-log")
        log.write(f"> Starting {task_name}...\n")
        try:
            # Note: Using absolute path to venv mura if possible
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                log.write(line.decode())
            await process.wait()
            log.write(f"> {task_name} finished.\n")
        except Exception as e:
            log.write(f"Error: {e}\n")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        m_id = getattr(self.app, "selected_manga_id", "")
        log = self.query_one("#op-log")

        if event.button.id == "btn-edit-meta":
            self.app.query_one(AddMangaForm).reset_form()
            self.app.query_one(AddMangaForm).prefill(m_id)
            self.app.action_switch_to("add")

        elif event.button.id == "btn-delete-manga":
            manager.delete_manga(m_id)
            self.app.notify(f"Manga {m_id} deleted.")
            self.app.action_switch_to("list")

        elif event.button.id == "btn-import":
            drive_id = self.query_one("#drive-id").value
            if not drive_id:
                self.app.notify("Please enter a Drive ID", variant="error")
                return
            log.write(f"Starting import for {m_id}...\n")
            
            def do_import():
                return drive_importer.import_chapters(drive_id, m_id)
            
            loop = asyncio.get_event_loop()
            latest = await loop.run_in_executor(None, do_import)
            if latest:
                log.write(f"Import complete! Latest chapter: {latest}\n")
                self.app.notify(f"Imported {m_id} up to cap {latest}")
                cat = manager.load_catalogo()
                for item in cat["items"]:
                    if item["mangaId"] == m_id:
                        item["latest"] = f"Capítulo {latest}"
                        break
                manager.save_catalogo(cat)
        
        elif event.button.id == "btn-rebuild":
            # Using bundle exec jekyll build as requested in plan
            await self.run_process(["bundle", "exec", "jekyll", "build"], "Jekyll Build")
            
        elif event.button.id == "btn-sync":
            # Running CLI sync directly via python module to ensure venv context
            await self.run_process(["./.venv/bin/python3", "-m", "mura_cli.main", "sync"], "Git Sync")

        elif event.button.id == "btn-copy-log":
            log_content = "\n".join(log.lines)
            pyperclip.copy(log_content)
            self.app.notify("Log copied to clipboard!")

        elif event.button.id == "btn-back":
            self.app.action_switch_to("list")

class MergeScreen(Static):
    """Screen for merging folders or JSON files."""

    def compose(self) -> ComposeResult:
        with Vertical(id="merge-container"):
            yield Label("Merge Tool")
            yield Label("Target Folder/File:")
            yield Input(placeholder="e.g. assets/mangas/manga/cap1", id="merge-target")
            yield Label("Source Folders/Files (one per line):")
            yield Input(placeholder="Source 1", id="source-1")
            yield Input(placeholder="Source 2", id="source-2")
            yield Input(placeholder="Source 3", id="source-3")
            yield Button("Run Merge", variant="primary", id="btn-run-merge")
            yield Static("", id="merge-status")
            yield Button("Back to List", id="btn-back-from-merge")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-run-merge":
            target = self.query_one("#merge-target").value
            sources = [
                self.query_one("#source-1").value,
                self.query_one("#source-2").value,
                self.query_one("#source-3").value
            ]
            sources = [s for s in sources if s.strip()]
            
            if not target or not sources:
                self.query_one("#merge-status").update("Target and at least one source required.")
                return
            
            loop = asyncio.get_event_loop()
            if all(s.endswith(".json") for s in sources):
                await loop.run_in_executor(None, merger.merge_json, sources, target)
                self.query_one("#merge-status").update("JSON Merge Complete!")
            else:
                await loop.run_in_executor(None, merger.merge_folders, sources, target)
                self.query_one("#merge-status").update("Folder Merge Complete!")
                
        elif event.button.id == "btn-back-from-merge":
            self.app.action_switch_to("list")

class MuraTUI(App):
    """Main Application for Project Mura Management."""
    
    selected_manga_id = None

    CSS = """
    Screen {
        background: #1a1b26;
    }
    #form-container, #manage-container, #merge-container {
        padding: 1 2;
        border: solid #3b4261;
        margin: 1 2;
        height: auto;
    }
    .form-row {
        height: auto;
        margin-bottom: 1;
    }
    .form-row Vertical {
        width: 1fr;
        height: auto;
        margin-right: 2;
    }
    Input {
        margin: 0;
        background: #24283b;
        color: #c0caf5;
    }
    TextArea {
        height: 6;
        border: solid #3b4261;
        margin-bottom: 0;
    }
    Button {
        margin-right: 1;
    }
    #status-msg, #merge-status {
        color: #7aa2f7;
        margin-top: 1;
    }
    #manage-title {
        text-style: bold;
        margin-bottom: 1;
        color: #bb9af7;
    }
    #op-log {
        height: 10;
        border: tall #3b4261;
        background: #16161e;
        color: #c0caf5;
        margin: 1 0;
    }
    #action-buttons, #meta-actions, #form-actions {
        margin-top: 1;
        height: 3;
    }
    Label {
        text-style: bold;
        color: #9ece6a;
        margin-bottom: 0;
    }
    """

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("n", "new_manga", "New Manga"),
        ("l", "switch_to('list')", "List Mangas"),
        ("m", "switch_to('merge')", "Merge Tool"),
        ("escape", "unfocus", "Unfocus"),
    ]

    def action_unfocus(self) -> None:
        """Removes focus from any active input."""
        self.set_focus(None)

    def compose(self) -> ComposeResult:
        yield Header()
        with ContentSwitcher(initial="list"):
            yield MangaListScreen(id="list")
            yield AddMangaForm(id="add")
            yield ManageMangaScreen(id="manage")
            yield MergeScreen(id="merge")
        yield Footer()

    def action_new_manga(self) -> None:
        self.query_one(AddMangaForm).reset_form()
        self.action_switch_to("add")

    def action_switch_to(self, target: str) -> None:
        self.query_one(ContentSwitcher).current = target
        if target == "list":
            self.query_one(MangaListScreen).refresh_list()
        elif target == "manage":
            self.query_one(ManageMangaScreen).update_info()

    def on_add_manga_form_manga_added(self, message: AddMangaForm.MangaAdded) -> None:
        self.selected_manga_id = message.manga_id
        self.action_switch_to("manage")

if __name__ == "__main__":
    app = MuraTUI()
    app.run()
