import git
from pathlib import Path

class GitManager:
    def __init__(self, repo_path: str = "."):
        self.repo = git.Repo(repo_path)

    def sync(self, message: str, remote_name: str = "mura"):
        """
        Stages all changes, commits, and pushes to remote.
        """
        try:
            self.repo.git.add(A=True)
            self.repo.index.commit(message)
            origin = self.repo.remote(name=remote_name)
            origin.push()
            print(f"Changes pushed to {remote_name} successfully.")
        except Exception as e:
            print(f"Git error: {e}")

    def get_status(self):
        return self.repo.git.status()
