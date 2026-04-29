from fastapi import FastAPI

app = FastAPI(title="Cardiac Matchmaker API")

@app.get("/health")
def health():
    return {"status": "ok"}
