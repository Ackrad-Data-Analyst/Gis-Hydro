"""Build a personalized, dependency-free manager PDF and clean release ZIP."""

from __future__ import annotations

import argparse
import hashlib
import re
import textwrap
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INCLUDED_DIRECTORIES = ("config", "docs", "sample_data", "src", "tests", "toolboxes", "tools")
INCLUDED_FILES = (
    ".gitignore", "AGENTS.md", "CHANGELOG.md", "DEVELOPMENT_PLAN.md",
    "ENGINEERING_RULES.md", "PROJECT_SCOPE.md", "README.md", "REQUIREMENTS.md",
    "pyproject.toml",
)
EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".pyt.xml")


def _personalized_message(manager: str, author: str) -> str:
    template = (ROOT / "docs" / "manager_handoff_message.md").read_text(encoding="utf-8")
    return template.replace("[Manager Name]", manager).replace("[Your Name]", author)


def _feedback_response(manager: str, author: str) -> str:
    template = (ROOT / "docs" / "response_to_adolfo_feedback.md").read_text(encoding="utf-8")
    return template.replace("[Manager Name]", manager).replace("[Your Name]", author)


def _plain_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"`([^`]*)`", r"\1", line)
        line = line.replace("| --- |", "|")
        # Core PDF Helvetica is WinAnsi; normalize punctuation deterministically.
        line = line.translate(str.maketrans({"—": "-", "–": "-", "“": '"', "”": '"', "’": "'"}))
        line = line.encode("cp1252", errors="replace").decode("cp1252")
        indent = "  " if line.startswith(("- ", "* ")) else ""
        lines.extend(textwrap.wrap(line, width=92, initial_indent=indent, subsequent_indent=indent) or [""])
    return lines


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(markdown: str, output: Path) -> None:
    """Write a readable multi-page PDF using only the Python standard library."""
    lines = _plain_lines(markdown)
    pages = [lines[index:index + 48] for index in range(0, len(lines), 48)] or [[""]]
    objects: list[bytes] = []
    page_ids: list[int] = []
    content_ids: list[int] = []
    font_id = 3
    next_id = 4
    for _ in pages:
        page_ids.append(next_id); content_ids.append(next_id + 1); next_id += 2
    objects.extend([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{value} 0 R' for value in page_ids)}] /Count {len(pages)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ])
    for page_id, content_id, page in zip(page_ids, content_ids, pages):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        commands = ["BT", "/F1 9 Tf", "48 754 Td", "12 TL"]
        for line in page:
            commands.append(f"({_pdf_escape(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("cp1252", errors="replace")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(pdf)


def _release_files() -> list[Path]:
    files = [ROOT / name for name in INCLUDED_FILES]
    for directory in INCLUDED_DIRECTORIES:
        files.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    return sorted({path for path in files if "__pycache__" not in path.parts and not path.name.endswith(EXCLUDED_SUFFIXES)})


def build_release(manager: str, author: str, output_directory: Path) -> tuple[Path, Path, Path, Path, Path]:
    safe_manager = re.sub(r"[^A-Za-z0-9]+", "_", manager).strip("_")
    markdown = _personalized_message(manager, author)
    message_path = output_directory / f"Manager_Submission_{safe_manager}.md"
    pdf_path = output_directory / f"Manager_Submission_{safe_manager}.pdf"
    zip_path = output_directory / f"Gis-Hydro_Manager_Release_{safe_manager}.zip"
    feedback_message_path = output_directory / f"Feedback_Response_{safe_manager}.md"
    feedback_pdf_path = output_directory / f"Feedback_Response_{safe_manager}.pdf"
    output_directory.mkdir(parents=True, exist_ok=True)
    message_path.write_text(markdown, encoding="utf-8")
    write_pdf(markdown, pdf_path)
    feedback = _feedback_response(manager, author)
    feedback_message_path.write_text(feedback, encoding="utf-8")
    write_pdf(feedback, feedback_pdf_path)
    manifest: list[str] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in _release_files():
            relative = path.relative_to(ROOT)
            archive.write(path, Path("Gis-Hydro") / relative)
            manifest.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  Gis-Hydro/{relative.as_posix()}")
        archive.write(pdf_path, Path("Gis-Hydro") / "Manager_Submission.pdf")
        archive.write(feedback_pdf_path, Path("Gis-Hydro") / "Feedback_Response.pdf")
        archive.writestr("Gis-Hydro/RELEASE_SHA256.txt", "\n".join(manifest) + "\n")
    return message_path, pdf_path, feedback_message_path, feedback_pdf_path, zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "manager_release")
    args = parser.parse_args()
    for path in build_release(args.manager, args.author, args.output.resolve()):
        print(path)


if __name__ == "__main__":
    main()
