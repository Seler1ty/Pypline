import psycopg2
from credentials import Credentials

# Подключение к БД

conn = psycopg2.connect(
    host = "aws-0-eu-west-1.pooler.supabase.com",
    dbname = "postgres",
    user = Credentials.USER.value,
    password = Credentials.PASSWORD.value,
    port = 5432,
    sslmode = "require"
)
