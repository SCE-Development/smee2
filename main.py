from fastapi import FastAPI
from fastapi import WebSocket
from fastapi import Request
import uvicorn
import json

app = FastAPI()

connected_clients = []
@app.get("/")
def root():
    return({ "message": "Welcome to the server!" })


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    for client in connected_clients:
        await client.send_text(json.dumps(data))



@app.websocket("/tunnel")
async def tunnel(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except:
            connected_clients.remove(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, reload=True)
