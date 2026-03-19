# Payment service 
    FastAPI + SQLAlchemy + Postgres 

## Scheme tables in DB
    ![Scheme tables in db](scheme_tables_db.png)
    
## Setup

You'll need Docker and Docker-Compose to run the application. With both dependencies installed, just run on a terminal:

    docker-compose up

## Web Interfaces

REST endpoints bellow:

    http://localhost:8000/docs

    POST /app/create:
        amount
        order_id

    GET /app/status/{bank_order_id}

    POST /app/refund/{bank_order_id}

    GET /health


## Installing  and start local in directory payment_service
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    CMD: uvicorn main:app --reload

## Responses from Bank

    Successful response /app/create:
        {   
            "bank_order_id": "5SDCXVG7889",
            "error_code": "0", 
            "error_description": ""
        }
    Failed response /app/create:
        {
            "error_code": "1", # Любое число, только не "0"
            "error_message": "Message error"
        }
    Successful response /app/status/{bank_order_id}:
        {   
            "bank_order_id": "5SDCXVG7889",
            "error_code": "0", 
            "error_message": "",
            "bank_order_status": "PAID"
        }
    Failed response /app/status/{bank_order_id}:
        {
            "error_code": "1", # Любое число, только не "0"
            "error_message": "Message error",
        }
    Successful response /app/refund/{bank_order_id}:
        {   
            "bank_order_id": "5SDCXVG7889",
            "error_code": "0", 
            "error_description": "",
            "bank_order_status": "REFUNDED"
        }
    Failed response /app/refund/{bank_order_id}:
        {
            "error_code": "1", # Любое число, только не "0"
            "error_description": "Message error",
        }


