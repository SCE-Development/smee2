import collections
import logging
import collections

from fastapi import FastAPI, WebSocket, Request, HTTPException, Response
import prometheus_client
import uvicorn
import yaml

from args import get_args
from metrics import MetricsHandler


args = get_args()

logging.basicConfig(
    # in mondo we trust
    format="%(asctime)s.%(msecs)03dZ %(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.ERROR - (args.verbose * 10),
)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI()

clients = collections.defaultdict(list)

subscribers = {}
# see if __name__ == '__server__' section for setting this value
API_KEY = None

@app.post("/webhook/{subscription_id}")
async def webhook(subscription_id: str, request: Request):
    if subscription_id is None:
        logger.error(
            "Invalid subscription '%s', connection not accepted", subscription_id
        )
        MetricsHandler.failed_connections.labels(
            subscription_id=subscription_id,
            reason="no_subscription_id",
        ).inc()
        raise HTTPException(
            status_code=404,
            detail="subscripiton id was empty. expecting soemthing like /webhook/1234",
        )
    header_val = request.headers.get("X-API-Key")

    data = await request.json()
    logger.debug("Data pushed to webhook %s, received: %s", subscription_id, data)

    subscribers[subscription_id] = data

    for client in clients.get(subscription_id, []):
        await client.send_json(data)

    number_of_clients = len(clients.get(subscription_id, []))
    message = f"forwarded to {len(number_of_clients)} client(s) for subscription {subscription_id}"
    logger.debug(message)
    return {"message": message}


@app.websocket("/tunnel/{subscription_id}")
async def websocket_endpoint(subscription_id: str, websocket: WebSocket):
    api_key_from_header = websocket.headers.get("X-API-Key")

    if API_KEY is not None and api_key_from_header != API_KEY:
        logger.error('/tunnel recieved invalid X-API-Key of "%s"', api_key_from_header)
        MetricsHandler.failed_connections.labels(
            subscription_id=subscription_id,
            reason="bad_api_key",
        ).inc()
        await websocket.close(code=1008)
        return

    await websocket.accept()

    MetricsHandler.connected_clients.labels(subscription_id).inc()

    clients[subscription_id].append(websocket)

    logger.debug(
        f"Websocket connection successfully established at id: {subscription_id}"
    )

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text("Message received")
    except Exception:
        logger.exception("ok")
        MetricsHandler.failed_connections.labels(
            subscription_id=subscription_id,
            reason="websocket_receive_failed",
        ).inc()
        MetricsHandler.connected_clients.labels(subscription_id).dec()
    finally:
        clients[subscription_id].remove(websocket)
        if not clients[subscription_id]:
            clients.pop(subscription_id, None)

        logger.debug(f"Websocket connection disconnected at id: {subscription_id}")


@app.get("/metrics")
def get_metrics():
    return Response(
        content=prometheus_client.generate_latest(),
        media_type="text/plain",
    )


# we have a separate __name__ check here due to how FastAPI starts
# a server. the file is first ran (where __name__ == "__main__")
# and then calls `uvicorn.run`. the call to run() reruns the file,
# this time __name__ == "server". the separate __name__ if statement
# is so the thread references the same instance as the global
# metrics_handler referenced by the rest of the file. otherwise,
# the thread interacts with an instance different than the one the
# server uses
if __name__ == "server":
    MetricsHandler.init()
    try:
        with open(args.config, "r") as stream:
            data = yaml.safe_load(stream)
            API_KEY = data.get("api_key", None)
        logger.info(f'loaded api key from {args.config}')
    except Exception:
        logging.warning("unable to open yaml file, smee2 is not checking for api keys")

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        timeout_graceful_shutdown=1,
    )
