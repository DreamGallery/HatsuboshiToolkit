import time
from rich.console import Console

console = Console()


def info(msg: str):
    console.print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} [bold blue]>>> [Info][/bold blue] {msg}")


def succeed(msg: str):
    console.print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} [bold green]>>> [Succeed][/bold green] {msg}")


def error(msg: str):
    console.print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} [bold red]>>> [Error][/bold red] {msg}")


def warning(msg: str):
    console.print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} [bold yellow]>>> [Warning][/bold yellow] {msg}")
