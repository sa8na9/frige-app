import os

DB_CONFIG_LOCAL = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'fridge_app',
    'charset': 'utf8mb4'
}

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres.gcxitnxjafuwmahrcgqc:Fridge2026!Secure#@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres'
)

# 🚨 緊急修正: ローカル環境を強制的に有効化
# 元の行をコメントアウト
# USE_PRODUCTION = os.environ.get('PRODUCTION', 'false').lower() == 'true'
USE_PRODUCTION = False

def get_db_config():
    if USE_PRODUCTION:
        return DATABASE_URL
    else:
        return DB_CONFIG_LOCAL