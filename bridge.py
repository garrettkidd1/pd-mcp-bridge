import os, json, subprocess, threading, queue, time
from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse, StreamingResponse

def start_mcp():
    env = os.environ.copy()
    if "PAGERDUTY_USER_API_KEY" not in env:
        raise RuntimeError("Missing PAGERDUTY_USER_API_KEY")
    return subprocess.Popen(
        ["python", "-m", "pagerduty_mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1
    )

mcp = start_mcp()
out_q = queue.Queue()

def reader():
    while True:
        line = mcp.stdout.readline()
        if not line:
            break
        out_q.put(line)

threading.Thread(target=reader, daemon=True).start()
app = FastAPI()

BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN")

def authorized(auth_header: str | None):
    if BRIDGE_TOKEN:
        return auth_header and auth_header.startswith("Bearer ") and auth_header.split(" ",1)[1] == BRIDGE_TOKEN
    return True

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/mcp")
async def mcp_call(req: Request, authorization: str | None = Header(default=None)):
    if not authorized(authorization):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    payload = await req.body()
    mcp.stdin.write(payload.decode() + "\n")
    mcp.stdin.flush()
    deadline = time.time() + 25
    while time.time() < deadline:
        try:
            line = out_q.get(timeout=0.5)
            try:
                return JSONResponse(json.loads(line))
            except:
                continue
        except queue.Empty:
            continue
    return JSONResponse({"error": "timeout"}, status_code=504)

@app.get("/mcp/stream")
async def mcp_stream(authorization: str | None = Header(default=None)):
    if not authorized(authorization):
        return JSONResponse({"error":"unauthorized"}, status_code=401)
    async def gen():
        yield "event: ping\ndata: ok\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")