import typer
import subprocess
from typing import List, Optional
from mura_cli.core.manager import ProjectManager
from mura_cli.core.git_ops import GitManager
from mura_cli.core.importer import DriveImporter

app = typer.Typer(help="Project Mura Automation Tool")
manager = ProjectManager()
git_manager = GitManager()
drive_importer = DriveImporter()

@app.command()
def add_manga(
    manga_id: str = typer.Argument(..., help="The slug/ID for the manga (e.g. oshi-no-ko)"),
    title: str = typer.Option(..., "--title", "-t", help="The full title of the manga"),
    section: str = typer.Option("activos", "--section", "-s", help="Section: activos, joints, or terminados"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags"),
    portada: str = typer.Option("", "--portada", "-p", help="Path to cover image"),
):
    """
    Adds a new manga to the catalog and Jekyll config.
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    manager.add_manga(manga_id, title, section, tag_list, portada)

@app.command()
def delete_manga(
    manga_id: str = typer.Argument(..., help="The slug/ID of the manga to delete"),
):
    """
    Removes a manga from the catalog and Jekyll config.
    """
    manager.delete_manga(manga_id)

@app.command()
def import_drive(
    folder_id: str = typer.Argument(..., help="The Google Drive folder ID"),
    manga_id: str = typer.Argument(..., help="The slug/ID of the manga"),
):
    """
    Imports all chapters from a Google Drive folder.
    """
    latest = drive_importer.import_chapters(folder_id, manga_id)
    if latest:
        typer.echo(f"Successfully imported chapters. Latest is {latest}.")
        # Optionally update catalog automatically
        cat = manager.load_catalogo()
        for item in cat["items"]:
            if item["mangaId"] == manga_id:
                item["latest"] = f"Capítulo {latest}"
                break
        manager.save_catalogo(cat)

@app.command()
def rebuild():
    """
    Runs Jekyll build to update the static site.
    """
    typer.echo("Building Project Mura...")
    try:
        subprocess.run(["bundle", "exec", "jekyll", "build"], check=True)
        typer.echo("Build complete!")
    except Exception as e:
        typer.echo(f"Build failed: {e}")

@app.command()
def sync(message: str = typer.Option("chore: update site content", "--message", "-m")):
    """
    Commits and pushes changes to the GitHub repository.
    """
    git_manager.sync(message)

@app.command()
def ui():
    """
    Launches the rich Text User Interface (TUI).
    """
    from mura_cli.tui.app import MuraTUI
    tui = MuraTUI()
    tui.run()

if __name__ == "__main__":
    app()
