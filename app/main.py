from fastapi import FastAPI

app = FastAPI()

@app.get("/")

@app.get("/health")
def give_info():
    return {"status":"ok"}