import psycopg2
from credentials import Credentials

# Подключение к БД

DB_PARAMS = {
    "host": "aws-0-eu-west-1.pooler.supabase.com",
    "dbname": "postgres",
    "user": Credentials.USER.value,
    "password": Credentials.PASSWORD.value,
    "port": 5432,
    "sslmode": "require"
}


def get_conn():
    return psycopg2.connect(**DB_PARAMS)
