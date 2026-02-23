import os
import aiofiles
from pathlib import Path
import logging
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None
import logging

BASE_DATA_DIR = Path(os.getenv("DATA_DIR", ".")) / "data"
FILES_DIR = BASE_DATA_DIR / "files"

FILES_DIR.mkdir(parents=True, exist_ok=True)

async def save_upload(filename: str, fileobj) -> str:
    # store under files/<unique name> (use original name for clarity)
    dest = FILES_DIR / filename
    # ensure no overwrite: if exists, append timestamp
    if dest.exists():
        from time import time
        dest = FILES_DIR / f"{int(time())}_{filename}"

    total = 0
    async with aiofiles.open(dest, 'wb') as out:
        while True:
            chunk = await fileobj.read(1024 * 64)
            if not chunk:
                break
            await out.write(chunk)
            total += len(chunk)

    pages = None
    try:
        if fitz is not None:
            # open saved file synchronously to count pages
            doc = fitz.open(str(dest))
            pages = doc.page_count
            doc.close()
    except Exception:
        pages = None

    logging.getLogger("docpreview.storage").info("Saved upload %s (%d bytes, pages=%s) -> %s", filename, total, pages, dest)
    return {"path": str(dest), "size": total, "pages": pages}

