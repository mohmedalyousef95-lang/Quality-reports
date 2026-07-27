import shutil
import subprocess
import tempfile
from pathlib import Path


class PdfConversionError(RuntimeError):
    pass


def convert_pptx_to_pdf(pptx_path: str, timeout: int = 120) -> str:
    """Convert a .pptx file to a pixel-faithful .pdf via headless LibreOffice
    (Impress) and return the path to the generated PDF.

    Each call gets its own throwaway LibreOffice user profile
    (`-env:UserInstallation`) so concurrent requests never fight over the
    same profile lock file — a common source of headless-soffice hangs.
    """
    if shutil.which("soffice") is None:
        raise PdfConversionError("LibreOffice (soffice) غير متوفر في هذه البيئة")

    src = Path(pptx_path)
    outdir = Path(tempfile.mkdtemp(prefix="pdf_out_"))
    profile_dir = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    try:
        result = subprocess.run(
            [
                "soffice",
                "--headless",
                "--norestore",
                f"-env:UserInstallation=file://{profile_dir}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(outdir),
                str(src),
            ],
            capture_output=True,
            timeout=timeout,
        )
        pdf_path = outdir / (src.stem + ".pdf")
        if result.returncode != 0 or not pdf_path.exists():
            detail = result.stderr.decode(errors="ignore")[:500]
            raise PdfConversionError(f"فشل تحويل الملف إلى PDF: {detail}")
        return str(pdf_path)
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)
