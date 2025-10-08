from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

# Token from env or fallback
AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "my-secret-token")

app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    text: str


@app.post("/send-message")
async def send_message(
    request: MessageRequest,
    authorization: Optional[str] = Header(None)
):
    print(request)
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    print("recieved:" , request)
    # Do nothing, just return 200 OK
    return {"detail": "OK"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)