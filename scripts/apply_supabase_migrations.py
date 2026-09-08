import psycopg2

password = 'Kairo-Prod-DB_2026!Secured'
sql_path = 'db/migrations/001_initial_schema.sql'

print(f"Reading {sql_path}...")
with open(sql_path, 'r', encoding='utf-8') as f:
    sql_script = f.read()

print("Connecting to live Supabase PostgreSQL (Tokyo)...")
conn = psycopg2.connect(
    host='db.uyxtyqilyuwpxdghceob.supabase.co',
    port=5432,
    user='postgres',
    password=password,
    dbname='postgres',
    connect_timeout=15
)
conn.autocommit = True
cur = conn.cursor()

print("Applying DDL schema & pgvector extensions on Supabase...")
cur.execute(sql_script)
print("Migration applied successfully!")

cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
""")
tables = [r[0] for r in cur.fetchall()]
print("Successfully verified tables in live Supabase:")
for t in tables:
    print(f" - public.{t}")

conn.close()
