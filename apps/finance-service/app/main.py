from fastapi import FastAPI, Request, HTTPException, Response
import psycopg2
from psycopg2.extras import RealDictCursor
import xml.etree.ElementTree as ET
import os
import time
import logging

# Setup Logging profesional biar kelihatan di terminal Docker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FinanceService")

app = FastAPI(title="Finance Service (Consumer XML - PostgreSQL)", version="1.1.0")

DB_HOST = os.getenv("FINANCE_DB_HOST", "localhost")
DB_USER = os.getenv("FINANCE_DB_USER", "finance_user")
DB_PASSWORD = os.getenv("FINANCE_DB_PASSWORD", "finance_password")
DB_NAME = os.getenv("FINANCE_DB_NAME", "campus_finance_db")

def get_pg_connection():
    return psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursor_factory=RealDictCursor
    )

@app.on_event("startup")
def startup_event():
    """Otomatis bikin tabel saat container up"""
    logger.info("Menunggu database PostgreSQL siap...")
    time.sleep(5)
    try:
        conn = get_pg_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tabel_tagihan (
                student_nim VARCHAR(20) PRIMARY KEY,
                student_name VARCHAR(100) NOT NULL,
                amount_bill BIGINT NOT NULL,
                payment_status VARCHAR(20) NOT NULL
            );
            """)
        conn.commit()
        conn.close()
        logger.info("[DATABASE] PostgreSQL 'tabel_tagihan' Berhasil Diinisialisasi.")
    except Exception as e:
        logger.error(f"[DATABASE ERROR] Gagal inisialisasi: {str(e)}")

@app.get("/")
def index():
    return {"status": "Finance Service is running", "database_host": DB_HOST}

@app.get("/api/v1/finance/invoices")
def get_all_invoices():
    """ENDPOINT DEMO DOSEN: Menampilkan seluruh data tagihan yang sukses tersinkronisasi"""
    try:
        conn = get_pg_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM tabel_tagihan;")
            records = cursor.fetchall()
        conn.close()
        return {"total_data": len(records), "data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data: {str(e)}")

@app.post("/api/v1/finance/sync")
async def sync_finance_invoice(request: Request):
    """Menerima & memproses payload XML berdasarkan Kontrak Bab 5"""
    body = await request.body()
    logger.info(f"Menerima kiriman payload tagihan baru (XML raw size: {len(body)} bytes)")
    
    try:
        root = ET.fromstring(body)
        student_nim = root.find('student_nim').text
        student_name = root.find('student_name').text
        amount_bill = int(root.find('amount_bill').text)
        payment_status = root.find('payment_status').text
    except (ET.ParseError, AttributeError, ValueError) as e:
        logger.warning(f"Bad Request 400: Skema XML tidak valid -> {str(e)}")
        raise HTTPException(status_code=400, detail=f"XML Parsing Error / Invalid Schema: {str(e)}")
    
    try:
        conn = get_pg_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
            INSERT INTO tabel_tagihan (student_nim, student_name, amount_bill, payment_status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (student_nim) 
            DO UPDATE SET student_name = EXCLUDED.student_name, 
                          amount_bill = EXCLUDED.amount_bill, 
                          payment_status = EXCLUDED.payment_status;
            """, (student_nim, student_name, amount_bill, payment_status))
        conn.commit()
        conn.close()
        
        logger.info(f"[SUCCESS] NIM {student_nim} berhasil masuk ke PostgreSQL!")
        xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<response>
    <status>success</status>
    <message>Invoice for {student_nim} successfully synced.</message>
</response>"""
        return Response(content=xml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Internal Error 500: Gagal ke database -> {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database Finance Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)