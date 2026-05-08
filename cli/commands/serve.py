import click

from cli.core.daemon import is_pid_alive, read_status, service_url, start_service, stop_service


@click.command()
@click.option("--port", default=None, type=int, help="HTTP service port.")
@click.option("--foreground", is_flag=True, help="Run in foreground.")
@click.option("--profile", default=None, help="Performance profile.")
@click.pass_context
def serve(ctx, port, foreground, profile):
    """Start HTTP API service."""
    port = port or ctx.obj.get("port", 8000)
    result = start_service(port=port, foreground=foreground, profile=profile)
    if not foreground:
        click.echo(f"VonishOCR service started: pid={result} url={service_url(port)}")


@click.command()
def stop():
    """Stop background service."""
    pid = stop_service()
    click.echo(f"Stopped service pid={pid or 'none'}")


@click.command()
def status():
    """Show service status."""
    state = read_status()
    alive = is_pid_alive(state.get("pid"))
    click.echo(f"status={'running' if alive else 'stopped'}")
    click.echo(f"pid={state.get('pid') or '-'}")
    click.echo(f"port={state.get('port') or '-'}")
    if alive:
        click.echo(f"url={service_url(state.get('port'))}")
