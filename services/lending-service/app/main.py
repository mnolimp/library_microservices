from fastapi import FastAPI

app = FastAPI(title="lending-service", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "lending-service"}

@app.get("/")
def root():
    return {"message": f"lending-service is running"}