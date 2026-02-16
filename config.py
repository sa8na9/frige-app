import os

DB_CONFIG_LOCAL = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'fridge_app',
    'charset': 'utf8mb4'
}

# Supabaseのパスワードを環境変数から取得
SUPABASE_PASSWORD = os.environ.get('SUPABASE_PASSWORD', 'Fridge2026!Secure#')

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f'postgresql://postgres.gcxitnxjafuwmahrcgqc:{SUPABASE_PASSWORD}@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres'
)

# 本番環境判定（Render.comではPRODUCTION=trueを設定）
USE_PRODUCTION = os.environ.get('PRODUCTION', 'false').lower() == 'true'

def get_db_config():
    if USE_PRODUCTION:
        return DATABASE_URL
    else:
        return DB_CONFIG_LOCAL