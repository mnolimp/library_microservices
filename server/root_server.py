from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from htpy import html, head, title, body, h1, a, br

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" not in accept:
        return HTMLResponse("Недопустимый заголовок Accept. Требуется text/html", status_code=406)

    doc = html[
        head[title["Главный сервер"]],
        body[
            h1["Ваша тема"],
            br,
            a(href="http://client.localhost")["Перейти на сервер-клиент"]
        ]
    ]
    return HTMLResponse(str(doc))