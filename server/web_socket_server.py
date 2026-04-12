import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        async def sender():
            while True:
                msg = "Это лучшая тема, что есть. Хотя…" if random.random() < 0.65 else "Надо менять тему…"
                await websocket.send_text(msg)
                await asyncio.sleep(random.uniform(2, 5))

        async def receiver():
            while True:
                data = await websocket.receive_text()
                if data and data not in ["Это лучшая тема, что есть. Хотя…", "Надо менять тему…"]:
                    await websocket.send_text("Да? Хорошо. Спасибо за поддержку!")

        # Запускаем отправку и получение параллельно
        await asyncio.gather(sender(), receiver())
    except WebSocketDisconnect:
        print("Клиент отключился")
    except Exception as e:
        print(f"Ошибка соединения: {e}")