from fastapi import FastAPI

app = FastAPI(title="catalog-service", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "catalog-service"}

@app.get("/")
def root():
    return {"message": f"catalog-service is running"}