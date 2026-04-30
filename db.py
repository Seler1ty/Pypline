import psycopg2
from credentials import Credentials

# Подключение к БД

conn = psycopg2.connect(
    host = "aws-0-eu-west-1.pooler.supabase.com",
    dbname = "postgres",
    user = Credentials.USER,
    password = Credentials.PASSWORD,
    port = 6543,
    sslmode = "require"
)