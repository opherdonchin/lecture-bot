from __future__ import annotations

import argparse as ap_module
import json as j
import sys as sys_module
import pathlib as pathlib_


def as_text(value: str | list[str] | None) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "".join(value)
    return value


def extract_output_text(output: dict) -> str:
    output_type = output.get("output_type")

    if output_type == "stream":
        return as_text(output.get("text")).strip()

    if output_type in {"display_data", "execute_result"}:
        data = output.get("data", {})
        return as_text(data.get("text/plain")).strip()

    if output_type == "error":
        traceback = output.get("traceback") or []
        if traceback:
            return "\n".join(traceback).strip()

        error_name = output.get("ename", "Error")
        error_value = output.get("evalue", "")
        return f"{error_name}: {error_value}".strip()

    return ""


def convert_ipynb_to_md(source: str | pathlib_.Path, target: str | pathlib_.Path) -> pathlib_.Path:
    source_path = pathlib_.Path(source)
    target_path = pathlib_.Path(target)

    if not source_path.exists():
        raise FileNotFoundError(f"Notebook source file not found: {source_path}")

    notebook = j.loads(source_path.read_text(encoding="utf-8"))
    language = notebook.get("metadata", {}).get("language_info", {}).get("name", "python")

    output_lines: list[str] = []
    for cell_index, cell in enumerate(notebook.get("cells", []), start=1):
        cell_type = cell.get("cell_type", "raw")
        source_text = as_text(cell.get("source")).rstrip()

        if cell_type == "markdown":
            output_lines.append(f"## Markdown Cell {cell_index}")
            output_lines.append("")
            if source_text:
                output_lines.append(source_text)
                output_lines.append("")
            continue

        if cell_type == "code":
            output_lines.append(f"## Code Cell {cell_index}")
            output_lines.append("")
            output_lines.append(f"```{language}")
            output_lines.append(source_text)
            output_lines.append("```")

            outputs = [extract_output_text(output) for output in cell.get("outputs", [])]
            outputs = [output for output in outputs if output]
            if outputs:
                output_lines.append("")
                output_lines.append("### Output")
                output_lines.append("")
                output_lines.append("```text")
                output_lines.append("\n\n".join(outputs))
                output_lines.append("```")

            output_lines.append("")
            continue

        if source_text:
            output_lines.append(f"## {cell_type.title()} Cell {cell_index}")
            output_lines.append("")
            output_lines.append(source_text)
            output_lines.append("")

    markdown = "\n".join(output_lines).strip()
    if markdown:
        markdown += "\n"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(markdown, encoding="utf-8")
    return target_path


def main(argv: list[str] | None = None) -> int:
    parser = ap_module.ArgumentParser(description="Convert a Jupyter notebook to markdown.")
    parser.add_argument("source", help="Path to the source .ipynb file")
    parser.add_argument("target", help="Path to the target .md file")
    args = parser.parse_args(argv)

    try:
        convert_ipynb_to_md(args.source, args.target)
    except Exception as exc:
        print(f"Error: {exc}", file=sys_module.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
