from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.text import Text
from rich.align import Align
from rich import box
from rich.columns import Columns
from rich.live import Live
from rich.layout import Layout
from contextlib import contextmanager
import time

console = Console()

BRAND_COLOR = "bold cyan"
ACCENT = "bold green"
WARN = "bold yellow"
ERROR = "bold red"
MUTED = "dim white"
SUCCESS = "bold green"


def show_banner():
    banner_text = Text()
    banner_text.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n", style="bold cyan")
    banner_text.append("┃                                                                   ┃\n", style="bold cyan")
    banner_text.append("┃", style="bold cyan")
    banner_text.append("       SISREG  ·  Notificador de Fila de Espera          ", style="bold white")
    banner_text.append("┃\n", style="bold cyan")
    banner_text.append("┃", style="bold cyan")
    banner_text.append("       Automação Inteligente de Agendamentos              ", style="dim cyan")
    banner_text.append("┃\n", style="bold cyan")
    banner_text.append("┃                                                                   ┃\n", style="bold cyan")
    banner_text.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", style="bold cyan")
    console.print()
    console.print(Align.center(banner_text))
    console.print()


def show_config_summary(user: str, date_range: str, instance: str):
    table = Table(box=box.ROUNDED, border_style="dim cyan", show_header=False, padding=(0, 2))
    table.add_column("Campo", style="bold white", width=20)
    table.add_column("Valor", style="cyan")
    table.add_row("Usuário", user)
    table.add_row("Período de Busca", date_range)
    table.add_row("Instância WhatsApp", instance)

    panel = Panel(
        table,
        title="[bold white]Configuração[/]",
        border_style="dim cyan",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def step_header(step_number: int, title: str, description: str = ""):
    console.print()
    step_text = Text()
    step_text.append(f"  ▸ ETAPA {step_number}  ", style="black on cyan bold")
    step_text.append(f"  {title}", style="bold white")
    console.print(step_text)
    if description:
        console.print(f"    {description}", style=MUTED)
    console.print()


def step_done(message: str):
    console.print(f"    [bold green]✓[/] {message}")


def step_info(message: str):
    console.print(f"    [dim cyan]→[/] {message}", style=MUTED)


def step_warn(message: str):
    console.print(f"    [bold yellow]![/] {message}")


def step_error(message: str):
    console.print(f"    [bold red]✗[/] {message}")


@contextmanager
def spinner(message: str):
    with console.status(f"    [cyan]{message}[/]", spinner="dots", spinner_style="cyan"):
        yield


def show_data_table(records: list[dict]):
    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style="dim cyan",
        header_style="bold cyan",
        row_styles=["", "dim"],
        padding=(0, 1),
        show_lines=False,
    )
    table.add_column("#", style="dim white", width=4, justify="right")
    table.add_column("Paciente", style="bold white", max_width=30)
    table.add_column("Procedimento", style="white", max_width=35)
    table.add_column("Telefone", style="cyan", width=18)
    table.add_column("Data", style="yellow", width=12)
    table.add_column("Hora", style="yellow", width=10)

    for i, r in enumerate(records, 1):
        nome = r.get("nome", "—")
        if len(nome) > 28:
            nome = nome[:27] + "…"
        proc = r.get("procedimento", "—")
        if len(proc) > 33:
            proc = proc[:32] + "…"
        table.add_row(
            str(i),
            nome,
            proc,
            r.get("telefone", "—"),
            r.get("data", "—"),
            r.get("hora", "—"),
        )

    panel = Panel(
        table,
        title=f"[bold white]Agendamentos Encontrados — {len(records)} registro(s)[/]",
        border_style="cyan",
        padding=(1, 1),
    )
    console.print(panel)
    console.print()


def create_send_progress(total: int):
    progress = Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn("[bold white]{task.description}"),
        BarColumn(bar_width=30, style="dim white", complete_style="cyan", finished_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
    return progress


def show_message_sent(name: str, phone: str):
    console.print(f"    [green]✓[/] Mensagem enviada → [bold white]{name}[/]  [dim cyan]({phone})[/]")


def show_message_failed(name: str, phone: str, error: str):
    console.print(f"    [red]✗[/] Falha ao enviar → [bold white]{name}[/]  [dim red]({error})[/]")


def show_summary(total: int, sent: int, failed: int, elapsed: float):
    console.print()

    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    table = Table(box=box.ROUNDED, border_style="dim cyan", show_header=False, padding=(0, 3))
    table.add_column("Métrica", style="bold white", width=25)
    table.add_column("Valor", style="cyan", justify="right")
    table.add_row("Registros extraídos", f"[bold cyan]{total}[/]")
    table.add_row("Mensagens enviadas", f"[bold green]{sent}[/]")
    if failed > 0:
        table.add_row("Falhas no envio", f"[bold red]{failed}[/]")
    table.add_row("Tempo total", f"[bold white]{time_str}[/]")

    status = "[bold green]CONCLUÍDO COM SUCESSO[/]" if failed == 0 else "[bold yellow]CONCLUÍDO COM AVISOS[/]"

    panel = Panel(
        Align.center(table),
        title=f"[bold white]Relatório Final[/]",
        subtitle=status,
        border_style="green" if failed == 0 else "yellow",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def show_no_records():
    panel = Panel(
        Align.center(Text("Nenhum agendamento pendente de notificação encontrado.", style="yellow")),
        border_style="yellow",
        padding=(1, 3),
    )
    console.print(panel)
    console.print()


def show_goodbye():
    console.print()
    console.print(Align.center(Text("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim cyan")))
    console.print(Align.center(Text("Automação finalizada  ·  SISREG Notificador", style="dim white")))
    console.print(Align.center(Text("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="dim cyan")))
    console.print()
