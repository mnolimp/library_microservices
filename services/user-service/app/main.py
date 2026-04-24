from fastapi import FastAPI

app = FastAPI(title="user-service", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "user-service"}

@app.get("/")
def root():
    return {"message": f"user-service is running"}