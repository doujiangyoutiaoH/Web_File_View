import requests
import io
import time

BASE = "http://127.0.0.1:8000"

def main():
    sess = requests.Session()
    print("Calling dev_login to create admin and set cookie...")
    r = sess.get(f"{BASE}/dev_login?username=admin@example.com&admin=true", allow_redirects=True)
    print("dev_login status:", r.status_code)
    if r.status_code >= 400:
        print(r.status_code, r.text)
        return

    # small dummy PDF
    pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    print("Uploading test.pdf...")
    r = sess.post(f"{BASE}/admin/upload", files=files)
    print("upload status:", r.status_code, r.text)
    if r.status_code != 200:
        return
    import requests
    import io
    import time
    from datetime import datetime

    BASE = "http://127.0.0.1:8000"
    LOGPATH = "tests/live_client_output.log"


    def append_log(msg: str):
        ts = datetime.utcnow().isoformat()
        line = f"[{ts}] {msg}\n"
        # append to file for later inspection
        with open(LOGPATH, "a", encoding="utf-8") as f:
            f.write(line)
        # also print a short version to console
        print(line, end="")


    def main():
        sess = requests.Session()
        append_log("Starting live demo client")
        try:
            append_log("Calling dev_login to create admin and set cookie...")
            r = sess.get(f"{BASE}/dev_login?username=admin@example.com&admin=true", allow_redirects=True, timeout=10)
            append_log(f"dev_login status: {r.status_code}")
            if r.status_code >= 400:
                append_log(f"dev_login error: {r.status_code} {r.text}")
                return

            # small dummy PDF
            pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
            files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            append_log("Uploading test.pdf...")
            r = sess.post(f"{BASE}/admin/upload", files=files, timeout=30)
            append_log(f"upload status: {r.status_code} {r.text}")
            if r.status_code != 200:
                return
            doc = r.json()
            doc_id = doc.get("id")
            append_log(f"uploaded id: {doc_id}")

            append_log("Fetching viewer page...")
            r = sess.get(f"{BASE}/view/{doc_id}", timeout=10)
            append_log(f"view status: {r.status_code}")
            snippet = r.text[:800].replace('\n', ' ')
            append_log(f"view snippet: {snippet}")

            append_log("Fetching raw PDF bytes...")
            r = sess.get(f"{BASE}/files/{doc_id}/pdf", timeout=20)
            append_log(f"pdf status: {r.status_code} content-type: {r.headers.get('content-type')}")
            append_log(f"pdf len: {len(r.content) if r.status_code == 200 else 0}")

        except Exception as e:
            append_log(f"Exception during demo: {e}")


    if __name__ == '__main__':
        # wait a short moment for server to be ready if started together
        time.sleep(1)
        main()

