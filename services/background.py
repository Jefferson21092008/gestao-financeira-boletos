import queue
import threading
import tkinter as tk

def run_background_task(widget: tk.Misc, task, on_done, poll_ms: int = 80) -> None:
    """Executa I/O fora da thread do Tk e entrega o resultado na thread principal.

    Nunca chama métodos Tkinter a partir da thread de trabalho. Isso evita erros
    intermitentes como ``main thread is not in main loop`` em consultas online.
    ``on_done`` recebe ``(result, error)``.
    """
    results: queue.Queue[tuple[object | None, BaseException | None]] = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            results.put((task(), None))
        except BaseException as exc:  # a exceção é entregue ao callback no Tk
            results.put((None, exc))

    def poll() -> None:
        try:
            result, error = results.get_nowait()
        except queue.Empty:
            try:
                if widget.winfo_exists():
                    widget.after(poll_ms, poll)
            except tk.TclError:
                pass
            return
        try:
            if widget.winfo_exists():
                on_done(result, error)
        except tk.TclError:
            pass

    threading.Thread(target=worker, daemon=True).start()
    widget.after(poll_ms, poll)
