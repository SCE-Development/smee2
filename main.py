from fastapi import FastAPI
from fastapi import WebSocket
from fastapi import Request
from fastapi import HTTPException
import uvicorn
import json

app = FastAPI()

connected_clients = {}
@app.get("/")
def root():
    return({ "message": "Welcome to the server!" })


@app.post("/webhook/{id}")
async def webhook(id: str, request: Request):
    data = await request.json()
    client = connected_clients.get(id)
    
    if client is not None:
         await client.send_text(json.dumps(data))
    else:
         raise HTTPException(status_code=404, detail="No client connected for this ID")


@app.websocket("/tunnel/{id}")
async def tunnel(id: str, websocket: WebSocket):
    await websocket.accept()
    connected_clients[id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
    except Exception:
            if connected_clients.get(id) is websocket:
                connected_clients.pop(id)

if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, reload=True)
