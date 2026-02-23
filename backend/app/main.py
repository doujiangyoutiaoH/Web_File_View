import os
import io
from fastapi import FastAPI, Request, Depends, UploadFile, File, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import init_db, SessionLocal
from .models import Document, User
from .auth import get_login_url, exchange_code_for_token, create_jwt_for_user, verify_jwt_token, get_or_create_user_from_ms_token, SECRET_KEY
from .storage import save_upload, FILES_DIR
import os
from pathlib import Path
from starlette.requests import Request as StarletteRequest
from datetime import datetime
import jwt

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docpreview")

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login")
def login(next: str = "/"):
    # support return-to via state
    state = next
    url = get_login_url(state=state)
    return RedirectResponse(url)


@app.get("/auth/callback")
def auth_callback(request: Request, code: str = None, state: str = None):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    token = exchange_code_for_token(code)
    user = get_or_create_user_from_ms_token(token)
    jwt_token = create_jwt_for_user({"username": user.username, "display_name": user.display_name})
    # redirect to state (return URL) if present
    redirect_to = state or "/admin"
    response = RedirectResponse(url=redirect_to)
    # set cookie
    response.set_cookie(key="access_token", value=jwt_token, httponly=True, samesite="lax")
    return response


@app.get("/logout")
def logout():
    # clear cookie and redirect to Azure logout for full sign out
    redirect = RedirectResponse(url="/")
    redirect.delete_cookie("access_token")
    try:
        from .auth import get_logout_url
        logout_url = get_logout_url(post_logout_redirect=BASE_URL)
        return RedirectResponse(logout_url)
    except Exception:
        return redirect


# Development helper: create or sign-in a local user without Azure (ONLY for local testing)
@app.get("/dev_login")
def dev_login(username: str = "dev.user@example.com", admin: bool = False):
    # creates a user in the local DB (if missing) and sets JWT cookie for quick testing
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username, display_name=username, is_admin=bool(admin))
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    jwt_token = create_jwt_for_user({"username": user.username, "display_name": user.display_name})
    redirect_to = "/admin" if user.is_admin else "/"
    response = RedirectResponse(url=redirect_to)
    response.set_cookie(key="access_token", value=jwt_token, httponly=True, samesite="lax")
    return response


def get_current_user(request: StarletteRequest):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = verify_jwt_token(token)
    username = data.get("sub")
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.get("/admin", response_class=HTMLResponse)
def admin_ui(request: Request, user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    db = SessionLocal()
    docs = db.query(Document).all()
    db.close()
    return templates.TemplateResponse("admin.html", {"request": request, "docs": docs, "user": user})


@app.post("/admin/upload")
async def upload_doc(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403)
    result = await save_upload(file.filename, file.file)
    save_path = result.get("path") if isinstance(result, dict) else result
    size = result.get("size") if isinstance(result, dict) else None
    pages = result.get("pages") if isinstance(result, dict) else None
    logger.info("User %s uploaded file %s -> %s", user.username, file.filename, save_path)
    db = SessionLocal()
    doc = Document(filename=file.filename, stored_path=save_path, uploaded_by=user.username, size=size, pages=pages)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return {"id": doc.id, "filename": doc.filename, "pages": doc.pages}


@app.post("/admin/docs/{doc_id}/permissions")
def set_permissions(doc_id: int, allowed_users: str = "", user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403)
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        db.close()
        raise HTTPException(status_code=404)
    doc.allowed_users = allowed_users.strip() or None
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return {"id": doc.id, "allowed_users": doc.allowed_users}


@app.post("/admin/docs/{doc_id}/delete")
def delete_doc(doc_id: int, user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403)
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        db.close()
        raise HTTPException(status_code=404)
    try:
        if os.path.exists(doc.stored_path):
            os.remove(doc.stored_path)
    except Exception:
        pass
    db.delete(doc)
    db.commit()
    db.close()
    return {"status": "deleted"}


@app.get("/files/{doc_id}/pages/{pageno}.png")
def serve_page_image(doc_id: int, pageno: int, user: User = Depends(get_current_user)):
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    db.close()
    if not doc:
        raise HTTPException(status_code=404)
    if doc.allowed_users:
        allowed = [u.strip().lower() for u in doc.allowed_users.split(",") if u.strip()]
        if user.username.lower() not in allowed:
            raise HTTPException(status_code=403)

    try:
        import fitz
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        raise HTTPException(status_code=500, detail="Server missing rendering libraries")

    if not os.path.exists(doc.stored_path):
        raise HTTPException(status_code=404)

    try:
        pdf = fitz.open(doc.stored_path)
        if pageno < 1 or pageno > pdf.page_count:
            pdf.close()
            raise HTTPException(status_code=404)
        page = pdf.load_page(pageno - 1)
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_data = pix.tobytes("png")
        pdf.close()

        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        wm_text = f"{user.username} - {datetime.utcnow().isoformat()}"
        font_size = max(20, w // 30)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        overlay = Image.new("RGBA", img.size, (255,255,255,0))
        od = ImageDraw.Draw(overlay)
        text_w, text_h = od.textsize(wm_text, font=font)
        step_y = int(text_h * 4)
        step_x = int(text_w * 3)
        for y in range(-h, h + step_y, step_y):
            for x in range(-w, w + step_x, step_x):
                od.text((x + w//10, y + h//10), wm_text, font=font, fill=(180,180,180,80))

        combined = Image.alpha_composite(img, overlay)
        out_buf = io.BytesIO()
        combined.convert("RGB").save(out_buf, format="PNG")
        out_buf.seek(0)
        return StreamingResponse(out_buf, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error rendering page image: %s", e)
        raise HTTPException(status_code=500, detail="Rendering error")


@app.get("/files/{doc_id}/pdf")
def serve_pdf(doc_id: int, user: User = Depends(get_current_user)):
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    db.close()
    if not doc:
        raise HTTPException(status_code=404)
    file_path = doc.stored_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404)
    # Stream file with inline disposition and auth required
    def iterfile():
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(1024 * 64)
                if not chunk:
                    break
                yield chunk

    headers = {
        "Content-Disposition": f"inline; filename=\"{doc.filename}\"",
        "X-Content-Type-Options": "nosniff",
    }
    logger.info("Serving PDF %s to user %s", file_path, user.username)
    return StreamingResponse(iterfile(), media_type="application/pdf", headers=headers)


@app.get("/view/{doc_id}", response_class=HTMLResponse)
def view_doc(request: Request, doc_id: int, user: User = Depends(get_current_user)):
    # viewer page embeds PDF.js and overlays watermark
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    db.close()
    if not doc:
        raise HTTPException(status_code=404)
    watermark_text = f"{user.username} {datetime.utcnow().isoformat()}"
    logger.info("Rendering viewer for doc %s for user %s", doc_id, user.username)
    return templates.TemplateResponse("viewer.html", {"request": request, "doc": doc, "watermark": watermark_text})

