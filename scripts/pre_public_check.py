from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log"}
FORBIDDEN_EXACT_NAMES = {".env"}
FORBIDDEN_CONTENT = {
    "caminho pessoal do Windows": re.compile(re.escape("C:" + "\\Users\\"), re.IGNORECASE),
    "símbolo de senha legada": re.compile("LEGACY_" + "DEFAULT_PASSWORD"),
    "sequência contínua com tamanho de código de pagamento": re.compile(r"(?<!\\d)(?:\\d{44}|\\d{47}|\\d{48})(?!\\d)"),
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def main() -> int:
    problems: list[str] = []

    for path in tracked_files():
        rel = path.relative_to(ROOT)
        lower_name = path.name.lower()

        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f"arquivo sensível rastreado: {rel}")
        if lower_name in FORBIDDEN_EXACT_NAMES or lower_name.startswith(".env."):
            problems.append(f"arquivo de ambiente rastreado: {rel}")
        if any(part.lower() in {"backups", "logs"} for part in rel.parts[:-1]):
            problems.append(f"diretório operacional rastreado: {rel}")

        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for description, pattern in FORBIDDEN_CONTENT.items():
            if pattern.search(text):
                problems.append(f"{description}: {rel}")

    if problems:
        print("Falha na verificação pré-publicação:")
        for problem in sorted(set(problems)):
            print(f"- {problem}")
        return 1

    print("Verificação pré-publicação: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
