from fastapi import APIRouter
from botscripts.getmusic import query_collection

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

# uvicorn main:app --reload
router = APIRouter(
    prefix="/music",
    tags=["music"],
)

@router.get("/recs/")
async def read_users():
    try:
        results = query_collection("Good Music")
        print(results)
        
        return JSONResponse(results)
    except Exception as e:
        print(e)
        return "Error"
    
    
   