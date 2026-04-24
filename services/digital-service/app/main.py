from fastapi import FastAPI

app = FastAPI(title="digital-service", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "digital-service"}

@app.get("/")
def root():
    return {"message": f"digital-service is running"}