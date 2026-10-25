"""Preview a model in a browser or VS Code, optionally rebuilding on save."""

import argparse
import http.client
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from validate import load_model, select_models, validate_model


def source_bytes(path: Path) -> bytes | None:
    """Handle temporary removal during an editor's atomic save."""
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def wait_for_changes(
    path: Path, previous: bytes | None,
    connected: threading.Event | None = None,
    process: subprocess.Popen | None = None,
):
    """Debounce saves and compare content, including same-size rapid edits."""
    pending = previous
    changed_at = time.monotonic()
    while True:
        time.sleep(0.2)
        if process is not None and process.poll() is not None:
            raise RuntimeError("The viewer stopped. Restart the preview command.")
        if connected is not None and connected.is_set():
            connected.clear()
            yield previous
        current = source_bytes(path)
        if current != pending:
            pending = current
            changed_at = time.monotonic()
        if pending != previous and time.monotonic() - changed_at >= 0.4:
            previous = pending
            yield pending


def start_viewer(port: int) -> tuple[subprocess.Popen, threading.Event]:
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(
                f"Port {port} is in use. Choose --port <number> or use --vscode "
                "to connect to an existing OCP viewer."
            )
    process = subprocess.Popen(
        [sys.executable, "-u", "-m", "ocp_viewer", "--host", "127.0.0.1", "--port", str(port)],
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    connected = threading.Event()

    def read_output():
        # OCP Viewer 1.2 announces registration after accepting a browser socket.
        # It does not buffer models sent before registration, so wait for this.
        for line in process.stdout:
            if "Browser as viewer client registered" in line:
                connected.set()
            print(line, end="", flush=True)

    threading.Thread(target=read_output, daemon=True).start()
    try:
        deadline = time.monotonic() + 30
        # A local viewer must bypass any system HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("The viewer exited during startup. Check the output above.")
            try:
                with opener.open(f"http://127.0.0.1:{port}/viewer", timeout=0.5):
                    return process, connected
            except (urllib.error.URLError, TimeoutError, http.client.HTTPException):
                time.sleep(0.2)
        raise RuntimeError("The viewer did not start within 30 seconds.")
    except BaseException:
        stop_viewer(process)
        raise


def stop_viewer(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def render(path: Path, show, color: str | None = None) -> bool:
    try:
        model = load_model(path)
        summary = validate_model(model)
        options = {"colors": [color]} if color else {}
        show(model, names=[path.parent.name], **options)
        print(f"[PREVIEW] {path.parent.name}: {summary}", flush=True)
        return True
    except Exception as exc:
        print(f"[FAIL] {path.parent.name}: {exc}", file=sys.stderr, flush=True)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview a CadQuery model without exporting files")
    parser.add_argument("model", help="Model directory name, for example phone-stand")
    parser.add_argument("--watch", action="store_true", help="Rebuild when the selected model.py is saved")
    parser.add_argument("--vscode", action="store_true", help="Use an existing OCP CAD Viewer instead of starting a browser viewer")
    parser.add_argument("--port", type=int, default=3939, help="Viewer port (default: 3939)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically")
    parser.add_argument("--color", help="Preview color, for example '#FFD51C'; does not set filament color")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    try:
        path = select_models([args.model])[0]
    except ValueError as exc:
        parser.error(str(exc))
    try:
        if args.vscode:
            from ocp_vscode import set_port, show
        else:
            from ocp_viewer import set_port, show
    except ImportError as exc:
        parser.exit(1, f"Missing preview dependency: {exc}\nRun: python -m pip install -r requirements-preview.txt\n")

    process = None
    connected = None
    try:
        if not args.vscode:
            process, connected = start_viewer(args.port)
            url = f"http://127.0.0.1:{args.port}"
            print(f"[VIEWER] {url}", flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            print("[WAIT] Open the viewer page to display the model.", flush=True)
            while not connected.wait(timeout=0.2):
                if process.poll() is not None:
                    raise RuntimeError("The viewer stopped before the browser connected.")
            connected.clear()
        set_port(args.port)
        previous = source_bytes(path)
        success = render(path, show, args.color)
        if not success and not args.watch:
            raise SystemExit(1)
        if args.watch:
            print(f"[WATCH] {path} (Ctrl+C to stop). Failed builds keep the last valid preview.", flush=True)
            for _ in wait_for_changes(path, previous, connected, process):
                render(path, show, args.color)
        elif process is not None:
            print("[READY] Preview is running. Press Ctrl+C to close the viewer.", flush=True)
            while process.poll() is None:
                if connected.wait(timeout=0.2):
                    connected.clear()
                    render(path, show, args.color)
            raise RuntimeError("The viewer stopped. Restart the preview command.")
    except KeyboardInterrupt:
        print("\n[STOP] Preview stopped.", flush=True)
    except Exception as exc:
        parser.exit(1, f"[FAIL] {exc}\n")
    finally:
        if process is not None:
            stop_viewer(process)


if __name__ == "__main__":
    main()
