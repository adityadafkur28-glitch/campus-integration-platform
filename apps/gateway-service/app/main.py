from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Campus Integration Gateway"
)

SIAKAD_URL = os.getenv("SIAKAD_URL")
FINANCE_URL = os.getenv("FINANCE_URL")
LIBRARY_URL = os.getenv("LIBRARY_URL")


class MahasiswaRequest(BaseModel):
    nim: str
    nama: str
    kelas: str
    prodi: str


@app.get("/")
def root():
    return {
        "message": "Campus Integration Gateway Running"
    }


@app.post("/api/v1/mahasiswa")
def create_mahasiswa(mahasiswa: MahasiswaRequest):

    response = requests.post(
        f"{SIAKAD_URL}/api/v1/mahasiswa",
        json=mahasiswa.model_dump()
    )

    return response.json()


@app.get("/finance/health")
def finance_health():

    return {
        "service": "finance",
        "status": "reachable"
    }


@app.get("/library/health")
def library_health():

    return {
        "service": "library",
        "status": "reachable"
    }