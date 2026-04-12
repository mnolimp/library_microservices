from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from markupsafe import Markup
from htpy import html, head, title, body, h1, h2, p, button, script

app = FastAPI()

JS_CODE = """
const socket = new WebSocket('ws://web_socket.localhost/ws');
const statusEl = document.getElementById('status');
const msgEl = document.getElementById('message');
const btn = document.getElementById('btn');

socket.onopen = () => {
    statusEl.textContent = 'Рукопожатие состоялось: соединение установлено';
    btn.disabled = false;
};

socket.onmessage = (event) => {
    msgEl.textContent = '';
    msgEl.textContent = event.data;
};

btn.onclick = () => {
    // Генерируем уникальное сообщение (timestamp + random)
    const uniqueMsg = `client_msg_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    socket.send(uniqueMsg);
};
"""

@app.get("/", response_class=HTMLResponse)
async def client_page():
    doc = html[
        head[title["Клиент"]],
        body[
            h1["Была выбрана тема …"],
            h2(id="status"),
            p(id="message"),
            button(id="btn", disabled=True)["Классная тема!"],
            script[Markup(JS_CODE)] 
        ]
    ]
    return HTMLResponse(str(doc))