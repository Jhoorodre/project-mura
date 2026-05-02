from setuptools import setup, find_packages

setup(
    name="mura-cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "typer[all]",
        "textual",
        "requests",
        "httpx",
        "GitPython",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "mura=mura_cli.main:app",
        ],
    },
)
