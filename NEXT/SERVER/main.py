import portapy_sdk as ppy
import fastapi as fa

app = fa.FastAPI()

@app.get("/sync")
def get_sync():
    return "todo"


