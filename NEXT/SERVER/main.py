from __future__ import annotations

import fastapi as fa
import uvicorn
import util

if __name__ == "__main__":
    uvicorn.run('app:app', host="0.0.0.0", port=util.DEFAULT_SERVER_PORT)
