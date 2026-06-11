from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, sessionmaker

import json
import pika
import traceback

from app.config import (
    DATABASE_URL,
    RABBITMQ_HOST,
    RABBITMQ_USER,
    RABBITMQ_PASS,
    EXCHANGE_NAME,
    ROUTING_KEY
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def publish_student_registered(mahasiswa_data):
    try:
        credentials = pika.PlainCredentials(
            RABBITMQ_USER,
            RABBITMQ_PASS
        )

        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=5672,
                credentials=credentials
            )
        )

        channel = connection.channel()

        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type='direct',
            durable=True
        )

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY,
            body=json.dumps(mahasiswa_data)
        )

        connection.close()

        print("[RABBITMQ] Event berhasil dikirim")

    except Exception as e:
        print(f"[RABBITMQ ERROR] {repr(e)}")
        traceback.print_exc()

class Mahasiswa(Base):
    __tablename__ = "tabel_mahasiswa"

    nim = Column(String(20), primary_key=True)
    nama = Column(String(100), nullable=False)
    kelas = Column(String(50), nullable=False)
    prodi = Column(String(100), nullable=False)

Base.metadata.create_all(bind=engine)

class MahasiswaRequest(BaseModel):
    nim: str
    nama: str
    kelas: str
    prodi: str

app = FastAPI(
    title="SIAKAD Service"
)

@app.post("/api/v1/mahasiswa")
def create_mahasiswa(mahasiswa: MahasiswaRequest):

    db = SessionLocal()

    existing = (
        db.query(Mahasiswa)
        .filter(Mahasiswa.nim == mahasiswa.nim)
        .first()
    )

    if existing:
        db.close()

        return {
            "status": "error",
            "message": "NIM sudah terdaftar"
        }

    new_mahasiswa = Mahasiswa(
        nim=mahasiswa.nim,
        nama=mahasiswa.nama,
        kelas=mahasiswa.kelas,
        prodi=mahasiswa.prodi
    )

    db.add(new_mahasiswa)
    db.commit()

    publish_student_registered({
        "nim": mahasiswa.nim,
        "nama": mahasiswa.nama,
        "kelas": mahasiswa.kelas,
        "prodi": mahasiswa.prodi
    })

    db.close()

    return {
        "status": "success",
        "message": "Data mahasiswa berhasil disimpan"
    }