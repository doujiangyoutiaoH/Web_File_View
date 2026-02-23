from fastapi.testclient import TestClient
from backend.app.main import app
import io


def run_demo():
    client = TestClient(app)

    # 1) Create admin test user via dev_login
    r = client.get("/dev_login?username=admin@example.com&admin=true")
    print("dev_login ->", r.status_code)
    if r.is_error:
        raise RuntimeError(f"dev_login failed: {r.status_code} {r.text}")

    # 2) Upload a small dummy PDF
    pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r = client.post("/admin/upload", files=files)
    print("upload ->", r.status_code, r.text)
    if r.is_error:
        raise RuntimeError(f"upload failed: {r.status_code} {r.text}")
    doc = r.json()
    doc_id = doc.get("id")
    print("Uploaded doc id:", doc_id)

    # 3) Fetch view page and validate watermark text presence
    r = client.get(f"/view/{doc_id}")
    print("view ->", r.status_code)
    if r.is_error:
        raise RuntimeError(f"view failed: {r.status_code}")
    text = r.text
    # print a short snippet for inspection
    print(text[:400])
    if "admin@example.com" in text:
        print("Watermark present in view page (username found)")
    else:
        print("Watermark not found in view page")

    # 4) Fetch raw PDF bytes
    r = client.get(f"/files/{doc_id}/pdf")
    print("pdf ->", r.status_code, "content-type:", r.headers.get("content-type"))
    if r.is_error:
        raise RuntimeError(f"pdf fetch failed: {r.status_code}")
    print("pdf length:", len(r.content))


if __name__ == "__main__":
    run_demo()
from fastapi.testclient import TestClient
from backend.app.main import app
import io


def run_demo():
    client = TestClient(app)

    # 1) Create admin test user via dev_login
    r = client.get("/dev_login?username=admin@example.com&admin=true")
    if r.status_code not in (200, 307, 302):
        print("dev_login failed", r.status_code, r.text)
        return

    # 2) Upload a small dummy PDF
    pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r = client.post("/admin/upload", files=files)
    print("upload status:", r.status_code, r.text)
    if r.status_code != 200:
        print("Upload failed")
        return
    doc = r.json()
    doc_id = doc.get("id")
    print("Uploaded doc id:", doc_id)

    # 3) Fetch view page and validate watermark text presence
    r = client.get(f"/view/{doc_id}")
    print("view status:", r.status_code)
    if r.status_code != 200:
        print("View page failed")
        return
    text = r.text
    if "admin@example.com" in text:
        print("Watermark present in view page (username found)")
    else:
        print("Watermark not found in view page")

    # 4) Fetch raw PDF bytes
    r = client.get(f"/files/{doc_id}/pdf")
    print("pdf fetch status:", r.status_code, "content-type:", r.headers.get("content-type"))
    if r.status_code == 200:
        print("pdf length:", len(r.content))


if __name__ == "__main__":
    run_demo()

