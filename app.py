from fastapi import FastAPI, Response, status, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import mysql.connector
from mysql.connector import Error
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
import os


load_dotenv() 
app = FastAPI()


DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_HOST = "localhost" 

DATABASE_URL = f"mysql+mysqlconnector://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@app.get("/healthz", status_code=200)
async def health_check(response: Response, request: Request):
   
    if await request.body():
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    try:
       
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        if connection.is_connected():
            
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return Response(status_code=status.HTTP_200_OK)

    except mysql.connector.Error:
       
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    except OperationalError:
        
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    except Exception as e:
       
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

@app.put("/healthz")
@app.post("/healthz")
@app.delete("/healthz")
@app.patch("/healthz")
def method_not_allowed():
    return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
