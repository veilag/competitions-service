from typing import Annotated
from aiogram.types import Update
from aiogram.utils.web_app import WebAppInitData
from .config import Config
from .service.auth.deps import authorize_user_connection
from .sockets import SocketBroker, StandData, authorize_stand
from .service import templates_router, event_socket_router, user_router, competition_router
from .database import init_db, init_db_in_dev, engine
from .bot import bot, dp
from fastapi import FastAPI, WebSocket, Depends

app = FastAPI(
    title="API для олимпиады",
    description="API доступен только с определенных доменов (Не касается тестирования и отладки)",
    version=Config.VERSION,
    contact={
        "name": Config.Credentials.CONTACT_NAME,
        "url": Config.Credentials.CONTACT_SITE,
        "email": Config.Credentials.CONTACT_EMAIL
    },
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1
    }
)

socket_broker = SocketBroker()
socket_broker.register_router(event_socket_router)

app.state.broker = socket_broker

app.include_router(user_router)
app.include_router(competition_router)
app.include_router(templates_router)

WEBHOOK_PATH = f"/bot/{Config.TELEGRAM_TOKEN}"
WEBHOOK_URL = f"{Config.SERVER_DOMAIN}{WEBHOOK_PATH}"


@app.on_event("startup")
async def on_startup():
    if Config.MODE == "PROD":
        await init_db()
        return

    await init_db_in_dev()

    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(
            url=WEBHOOK_URL
        )


@app.post(
    path=WEBHOOK_PATH,
    include_in_schema=False
)
async def bot_webhook(update: dict):
    update = Update.model_validate(update, context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)


@app.websocket("/connect_user")
async def handle_connection(
    websocket: WebSocket,
    auth_data: Annotated[WebAppInitData, Depends(authorize_user_connection)]
):
    telegram_data, _ = auth_data
    await socket_broker.connect(websocket, telegram_data)
    await socket_broker.handle_websocket(websocket)


@app.websocket("/connect_stand")
async def handle_stand_connection(
    websocket: WebSocket,
    auth_data: Annotated[StandData, Depends(authorize_stand)]
):
    await socket_broker.connect_stand(websocket, auth_data)
    await socket_broker.handle_websocket(websocket)


@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
    await engine.dispose()