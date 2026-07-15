from fastapi import FastAPI
from fastapi import WebSocket
from fastapi import Request
from fastapi import HTTPException
import uvicorn
import collections

app = FastAPI()
clients = collections.defaultdict(list)

@app.get("/")
def root():
    return({ "message": "Welcome to the server!" })


@app.post("/webhook/{id}")
async def webhook(id: str, request: Request):
    if request.headers.get("X-API-Key") != "hello":
         raise HTTPException(status_code=403, detail="Invalid API key")
         
    data = await request.json()

    for client in clients.get(id, []):
         await client.send_json(data)

    return {"message": "received"}


@app.websocket("/tunnel/{id}")
async def tunnel(id: str, websocket: WebSocket):
    if websocket.headers.get("X-API-Key") != "hello":
         await websocket.close()
         return
    
    await websocket.accept()
    clients[id].append(websocket)
    
    try:
        while True:
            await websocket.receive_text()
    except Exception:
            clients[id].remove(websocket)
            if clients.get(id) is websocket:
                clients.pop(id, None)

if __name__ == "__main__":

    uvicorn.run("server:app", port=5000, reload=True)
