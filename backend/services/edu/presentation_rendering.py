"""Render the exact exported PPTX into page images for visual inspection."""

import platform
import shutil
import subprocess
import tempfile
from pathlib import Path


class PresentationRenderError(RuntimeError):
    """Raised when no real Office-compatible renderer can render a PPTX."""


def _render_with_powerpoint(input_path, output_dir, width, height):
    import pythoncom
    import win32com.client

    application = None
    presentation = None
    pythoncom.CoInitialize()
    try:
        application = win32com.client.DispatchEx("PowerPoint.Application")
        application.DisplayAlerts = 0
        presentation = application.Presentations.Open(
            str(input_path),
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )
        pages = []
        for number in range(1, presentation.Slides.Count + 1):
            output_path = output_dir / f"slide-{number:03d}.png"
            presentation.Slides(number).Export(
                str(output_path),
                "PNG",
                width,
                height,
            )
            pages.append(
                {
                    "number": number,
                    "content": output_path.read_bytes(),
                    "width": width,
                    "height": height,
                    "engine": "microsoft-powerpoint",
                }
            )
        return pages
    finally:
        if presentation is not None:
            presentation.Close()
        if application is not None:
            application.Quit()
        pythoncom.CoUninitialize()


def _render_with_libreoffice(input_path, output_dir, width, height):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    pdftoppm = shutil.which("pdftoppm")
    if not soffice or not pdftoppm:
        raise PresentationRenderError(
            "LibreOffice and pdftoppm are required for PPTX page rendering"
        )
    subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(input_path),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    pdf_path = output_dir / f"{input_path.stem}.pdf"
    if not pdf_path.is_file():
        raise PresentationRenderError("LibreOffice did not produce a PDF")
    dpi = max(72, round(width / 13.333))
    prefix = output_dir / "slide"
    subprocess.run(
        [pdftoppm, "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        check=True,
        capture_output=True,
        timeout=120,
    )
    pages = []
    for number, output_path in enumerate(
        sorted(output_dir.glob("slide-*.png")),
        1,
    ):
        pages.append(
            {
                "number": number,
                "content": output_path.read_bytes(),
                "width": width,
                "height": height,
                "engine": "libreoffice",
            }
        )
    if not pages:
        raise PresentationRenderError("PPTX renderer produced no page images")
    return pages


def render_pptx_pages(payload, *, width=1280, height=720):
    """Render PPTX bytes with the platform's real Office-compatible engine."""
    if not isinstance(payload, bytes) or not payload:
        raise PresentationRenderError("PPTX payload is empty")
    with tempfile.TemporaryDirectory(prefix="weagent-pptx-render-") as temp_dir:
        output_dir = Path(temp_dir)
        input_path = output_dir / "presentation.pptx"
        input_path.write_bytes(payload)
        try:
            if platform.system() == "Windows":
                return _render_with_powerpoint(input_path, output_dir, width, height)
            return _render_with_libreoffice(input_path, output_dir, width, height)
        except PresentationRenderError:
            raise
        except Exception as error:
            raise PresentationRenderError(str(error)) from error
