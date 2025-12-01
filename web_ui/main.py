import asyncio

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List
import json
import UI_bake.core as core

app = FastAPI()
clients: List[WebSocket] = []

# 挂载前端
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
async def index():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# 注册广播钩子
def broadcast(msg: dict):
    dead = []
    for c in clients[:]:
        try:
            # 使用 asyncio.run_coroutine_threadsafe 把异步 send 变成同步
            asyncio.run_coroutine_threadsafe(c.send_text(json.dumps(msg)), asyncio.get_event_loop())
        except Exception:
            dead.append(c)
    for c in dead:
        clients.remove(c)

core.set_broadcast_hook(broadcast)

# 接收前端用户消息
@app.post("/api/chat")
async def chat(req: Request):
    body = await req.json()
    # 直接让 AI1 回复
    core.send_to_ai1(body["text"])
    return {"status": "ok"}

# WebSocket 保持
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.remove(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=12466, reload=True)