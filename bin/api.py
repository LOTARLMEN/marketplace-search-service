import uvicorn

from src.fastapi import create_app

app = create_app()

import os

if __name__ == "__main__":
    port = 8003
    if "KUBERNETES_SERVICE_HOST" in os.environ:
        port = 8000
    uvicorn.run("bin.api:app", host="0.0.0.0", port=port, reload=True)
