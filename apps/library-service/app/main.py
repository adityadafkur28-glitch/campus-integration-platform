from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

class AnggotaPerpus(Base):
    __tablename__ = "tabel_anggota_perpus"

    id_keanggotaan = Column(Integer, primary_key=True, index=True)
    nim = Column(String(20), unique=True, nullable=False)
    nama_lengkap = Column(String(100), nullable=False)
    status_akses = Column(String(20), nullable=False)

Base.metadata.create_all(bind=engine)

class MemberRequest(BaseModel):
    nim: str
    nama_lengkap: str
    status_akses: str

app = FastAPI(
    title="Library Service"
)

@app.post("/api/v1/library/member")
def create_member(member: MemberRequest):

    db = SessionLocal()

    existing_member = (
        db.query(AnggotaPerpus)
        .filter(AnggotaPerpus.nim == member.nim)
        .first()
    )

    if existing_member:
        db.close()
        return {
            "status": "error",
            "message": "NIM sudah terdaftar"
        }

    new_member = AnggotaPerpus(
        nim=member.nim,
        nama_lengkap=member.nama_lengkap,
        status_akses=member.status_akses
    )

    db.add(new_member)
    db.commit()

    db.close()

    return {
        "status": "success",
        "message": "Anggota perpustakaan berhasil dibuat"
    }