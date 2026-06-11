import json
import pika
import requests
import traceback
import os
import time

from dotenv import load_dotenv

load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")

EXCHANGE_NAME = os.getenv("EXCHANGE_NAME")
QUEUE_NAME = os.getenv("QUEUE_NAME")
ROUTING_KEY = os.getenv("ROUTING_KEY")

FINANCE_URL = os.getenv("FINANCE_URL")
LIBRARY_URL = os.getenv("LIBRARY_URL")

def transform_to_canonical(raw_data):

    return {
        "studentId": raw_data["nim"],
        "fullName": raw_data["nama"],
        "className": raw_data["kelas"],
        "major": raw_data["prodi"],
        "status": "ACTIVE"
    }


def canonical_to_finance_xml(canonical):

    return f"""
<finance_invoice>
    <student_nim>{canonical["studentId"]}</student_nim>
    <student_name>{canonical["fullName"]}</student_name>
    <amount_bill>5000000</amount_bill>
    <payment_status>UNPAID</payment_status>
</finance_invoice>
"""


def canonical_to_library_json(canonical):

    return {
        "nim": canonical["studentId"],
        "nama_lengkap": canonical["fullName"],
        "status_akses": canonical["status"]
    }


def process_message(body):

    print("\n========================================")
    print("[WORKER] Message diterima")

    raw_data = json.loads(body)

    print("[RAW DATA]")
    print(raw_data)

    canonical = transform_to_canonical(raw_data)

    print("\n[CANONICAL MODEL]")
    print(canonical)

    finance_xml = canonical_to_finance_xml(canonical)

    try:

        response = requests.post(
            FINANCE_URL,
            data=finance_xml,
            headers={
                "Content-Type": "application/xml"
            },
            timeout=10
        )

        print(
            f"[FINANCE] Status = {response.status_code}"
        )

    except Exception as e:

        print(
            f"[FINANCE ERROR] {repr(e)}"
        )

    library_json = canonical_to_library_json(canonical)

    try:

        response = requests.post(
            LIBRARY_URL,
            json=library_json,
            timeout=10
        )

        print(
            f"[LIBRARY] Status = {response.status_code}"
        )

    except Exception as e:

        print(
            f"[LIBRARY ERROR] {repr(e)}"
        )


def callback(ch, method, properties, body):

    try:

        process_message(body)

        ch.basic_ack(
            delivery_tag=method.delivery_tag
        )

        print(
            "[SUCCESS] Message ACK"
        )

    except Exception as e:

        print(
            f"[WORKER ERROR] {repr(e)}"
        )

        traceback.print_exc()

        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False
        )


def main():

    print(
        f"[WORKER] Menghubungkan ke RabbitMQ ({RABBITMQ_HOST})..."
    )

    while True:

        try:

            credentials = pika.PlainCredentials(
                RABBITMQ_USER,
                RABBITMQ_PASS
            )

            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=5672,
                    credentials=credentials,
                    heartbeat=600
                )
            )

            print(
                "[WORKER] Berhasil terkoneksi ke RabbitMQ"
            )

            break

        except Exception as e:

            print(
                f"[WORKER] RabbitMQ belum siap: {repr(e)}"
            )

            time.sleep(5)

    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="direct",
        durable=True
    )

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True
    )

    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=QUEUE_NAME,
        routing_key=ROUTING_KEY
    )

    print(
        "[WORKER] Menunggu pesan dari RabbitMQ..."
    )

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback
    )

    channel.start_consuming()


if __name__ == "__main__":
    main()