import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.background import BackgroundTasks
from redis_om import get_redis_connection, HashModel
from starlette.requests import Request
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Should be a different database
redis = get_redis_connection(
    host="redis-19033.c93.us-east-1-3.ec2.cloud.redislabs.com",
    port=19033,
    password="pKgg9kirHYokzKG5mnWYlbaJB0xDO3v7",
    decode_responses=True
)


class Order(HashModel):
    product_id: str
    price: float
    fee: float
    total: float
    quantity: int
    status: str  # pending, completed, refunded

    class Meta:
        database = redis


@app.get("/orders/{pk}")
def get(pk: str):
    order = Order.get(pk)
    # redis.xadd('refund_order', order.dict(), '*')
    return order


@app.post("/orders")
async def create(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()

    req = requests.get(f"http://localhost:8000/products/{body['id']}")
    product = req.json()

    order = Order(
        product_id=body['id'],
        price=product["price"],
        fee=0.2 * product["price"],
        total=1.2 * product["price"],
        quantity=body['quantity'],
        status="pending"
    )
    order.save()

    background_tasks.add_task(order_completed, order)

    return order


def order_completed(order: Order):
    time.sleep(5)
    order.status = "completed"
    order.save()
    redis.xadd('order_completed', order.dict(), '*')
