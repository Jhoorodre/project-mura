from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Label, Input, ContentSwitcher, DataTable, Log
from textual.message import Message
from mura_cli.core.manager import ProjectManager
from mura_cli.core.fetcher import MetadataFetcher
from mura_cli.core.importer import DriveImporter
from mura_cli.core.merger import ChapterMerger
import asyncio

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
        self.app.switch_to("manage")

class AddMangaForm(Static):
    """A form to add a new manga."""
    
    class MangaAdded(Message):
        """Sent when a manga is added."""
        pass

    def compose(self) -> ComposeResult:
        with Vertical(id="form-container"):
            yield Label("Add New Manga")
            yield Input(placeholder="Manga Slug (e.g. oshi-no-ko)", id="manga-id")
            yield Button("Auto-Fill (AniList/Baka)", variant="primary", id="btn-autofill")
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Section (activos/joints/terminados)", id="section", value="activos")
            yield Input(placeholder="Tags (comma separated)", id="tags")
            yield Input(placeholder="Cover Path/URL", id="portada")
            with Horizontal():
                yield Button("Save", variant="success", id="btn-save")
                yield Button("Cancel", variant="error", id="btn-cancel")
            yield Static("", id="status-msg")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-autofill":
            m_id = self.query_one("#manga-id").value
            if not m_id:
                self.query_one("#status-msg").update("Please enter a slug first.")
                return
            
            self.query_one("#status-msg").update("Searching all APIs...")
            # Run fetch in thread to avoid UI freeze
            loop = asyncio.get_event_loop()
            metadata = await loop.run_in_executor(None, fetcher.auto_fill, m_id, m_id)
            
            if metadata:
                self.query_one("#title").value = metadata.get("title", "")
                self.query_one("#tags").value = ",".join(metadata.get("genres", []))
                self.query_one("#portada").value = metadata.get("portada", "")
                self.query_one("#status-msg").update(f"Found on {metadata['source']}!")
            else:
                self.query_one("#status-msg").update("Metadata not found.")
        
        elif event.button.id == "btn-save":
            m_id = self.query_one("#manga-id").value
            title = self.query_one("#title").value
            sec = self.query_one("#section").value
            tags = [t.strip() for t in self.query_one("#tags").value.split(",") if t.strip()]
            portada = self.query_one("#portada").value
            
            manager.add_manga(m_id, title, sec, tags, portada)
            self.app.notify(f"Manga {title} added!")
            self.post_message(self.MangaAdded())
        
        elif event.button.id == "btn-cancel":
            self.app.switch_to("list")

class ManageMangaScreen(Static):
    """Screen to manage a specific manga (Drive import, edit, etc)."""

    def compose(self) -> ComposeResult:
        with Vertical(id="manage-container"):
            yield Label("Manage Manga", id="manage-title")
            yield Label("Google Drive Folder ID:")
            yield Input(placeholder="Paste Drive ID here", id="drive-id")
            yield Button("Import Chapters from Drive", variant="primary", id="btn-import")
            with Horizontal(id="action-buttons"):
                yield Button("Rebuild Site", variant="warning", id="btn-rebuild")
                yield Button("Sync to GitHub", variant="default", id="btn-sync")
            yield Label("Operation Log:")
            yield Log(id="op-log")
            yield Button("Back to List", id="btn-back")

    def update_info(self) -> None:
        m_id = getattr(self.app, "selected_manga_id", "None")
        self.query_one("#manage-title").update(f"Managing: [b]{m_id}[/b]")

    async def run_process(self, cmd: list, task_name: str):
        log = self.query_one("#op-log")
        log.write(f"> Starting {task_name}...\n")
        try:
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

        if event.button.id == "btn-import":
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
            # Using absolute path to venv jekyll or system jekyll
            await self.run_process(["bundle", "exec", "jekyll", "build"], "Jekyll Build")
            
        elif event.button.id == "btn-sync":
            # Call mura sync command from venv
            await self.run_process(["./.venv/bin/mura", "sync"], "Git Sync")

        elif event.button.id == "btn-back":
            self.app.switch_to("list")

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
            self.app.switch_to("list")

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
    }
    Input {
        margin: 0 0 1 0;
        background: #24283b;
        color: #c0caf5;
    }
    Button {
        margin-right: 1;
    }
    #status-msg, #merge-status {
        color: #7aa2f7;
        margin-top: 1;
    }
    #manage-title {
        font-size: 150%;
        margin-bottom: 1;
        color: #bb9af7;
    }
    #op-log {
        height: 10;
        border: inset #3b4261;
        background: #16161e;
        color: #c0caf5;
        margin: 1 0;
    }
    #action-buttons {
        margin-top: 1;
        height: auto;
    }
    """

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("n", "switch_to('add')", "New Manga"),
        ("l", "switch_to('list')", "List Mangas"),
        ("m", "switch_to('merge')", "Merge Tool"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with ContentSwitcher(initial="list"):
            yield MangaListScreen(id="list")
            yield AddMangaForm(id="add")
            yield ManageMangaScreen(id="manage")
            yield MergeScreen(id="merge")
        yield Footer()

    def switch_to(self, target: str) -> None:
        self.query_one(ContentSwitcher).current = target
        if target == "list":
            self.query_one(MangaListScreen).refresh_list()
        elif target == "manage":
            self.query_one(ManageMangaScreen).update_info()

    def on_add_manga_form_manga_added(self, message: AddMangaForm.MangaAdded) -> None:
        self.switch_to("list")

if __name__ == "__main__":
    app = MuraTUI()
    app.run()
