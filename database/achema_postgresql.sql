-- =============================================
-- 店舗在庫管理システム データベーススキーマ (PostgreSQL/Supabase)
-- =============================================
-- 作成日: 2025-02-15
-- 更新日: 2026-02-26 (店舗在庫管理システムに変更)
-- =============================================

-- 既存のテーブルを削除(開発時のリセット用)
DROP TABLE IF EXISTS items CASCADE;
DROP TABLE IF EXISTS shopping_list CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS user_fridges CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS fridges CASCADE;

-- =============================================
-- 1. fridgesテーブル(店舗情報)
-- =============================================
CREATE TABLE fridges (
    fridge_id SERIAL PRIMARY KEY,
    fridge_name VARCHAR(50) NOT NULL,
    fridge_icon VARCHAR(10) DEFAULT '🏪',
    password_hash VARCHAR(255) NOT NULL,
    owner_user_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fridges_owner ON fridges(owner_user_id);

COMMENT ON TABLE fridges IS '店舗情報';
COMMENT ON COLUMN fridges.fridge_name IS '店舗名';
COMMENT ON COLUMN fridges.fridge_icon IS '絵文字アイコン';
COMMENT ON COLUMN fridges.password_hash IS '4桁パスワードのハッシュ';
COMMENT ON COLUMN fridges.owner_user_id IS '作成者ID（Phase2実装予定）';

-- =============================================
-- 2. usersテーブル(ユーザー情報) ※Phase2で実装
-- =============================================
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS 'ユーザー情報（Phase2実装予定）';

-- =============================================
-- 3. user_fridgesテーブル(ユーザー店舗関連) ※Phase2で実装
-- =============================================
CREATE TABLE user_fridges (
    user_id INT NOT NULL,
    fridge_id INT NOT NULL,
    role VARCHAR(20) DEFAULT 'member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, fridge_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (fridge_id) REFERENCES fridges(fridge_id) ON DELETE CASCADE
);

COMMENT ON TABLE user_fridges IS 'ユーザー店舗関連（Phase2実装予定）';

-- =============================================
-- 4. categoriesテーブル(カテゴリ)
-- =============================================
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    fridge_id INT NOT NULL DEFAULT 1,
    name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fridge_id) REFERENCES fridges(fridge_id) ON DELETE CASCADE
);

CREATE INDEX idx_categories_fridge ON categories(fridge_id);

COMMENT ON TABLE categories IS '在庫カテゴリ';

-- =============================================
-- 5. itemsテーブル(在庫情報)
-- =============================================
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    fridge_id INT NOT NULL DEFAULT 1,
    category_id INT NOT NULL DEFAULT 1,
    name VARCHAR(50) NOT NULL,
    container_type INT NOT NULL,
    quantity_level INT NOT NULL DEFAULT 1,
    opened_date DATE NULL,
    expiry_date DATE NULL,
    memo TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fridge_id) REFERENCES fridges(fridge_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE INDEX idx_items_fridge ON items(fridge_id);
CREATE INDEX idx_items_category ON items(category_id);
CREATE INDEX idx_items_expiry ON items(expiry_date);
CREATE INDEX idx_items_quantity ON items(quantity_level);

COMMENT ON TABLE items IS '在庫情報';
COMMENT ON COLUMN items.name IS '商品名';
COMMENT ON COLUMN items.container_type IS '容器タイプ';
COMMENT ON COLUMN items.quantity_level IS '残量レベル';
COMMENT ON COLUMN items.opened_date IS '開封日';
COMMENT ON COLUMN items.expiry_date IS '賞味期限';
COMMENT ON COLUMN items.memo IS 'メモ（発注先、ロット番号など）';

-- updated_atの自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_items_updated_at BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- 6. shopping_listテーブル(発注リスト)
-- =============================================
CREATE TABLE shopping_list (
    id SERIAL PRIMARY KEY,
    fridge_id INT NOT NULL DEFAULT 1,
    item_id INT NULL,
    item_name VARCHAR(50) NOT NULL,
    memo TEXT NULL,
    is_checked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fridge_id) REFERENCES fridges(fridge_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
);

CREATE INDEX idx_shopping_fridge ON shopping_list(fridge_id);
CREATE INDEX idx_shopping_item ON shopping_list(item_id);

COMMENT ON TABLE shopping_list IS '発注リスト';
COMMENT ON COLUMN shopping_list.item_id IS '元在庫ID（自動追加時のみ）';
COMMENT ON COLUMN shopping_list.item_name IS '商品名';
COMMENT ON COLUMN shopping_list.memo IS 'メモ（発注先、納期など）';
COMMENT ON COLUMN shopping_list.is_checked IS '発注済みフラグ';

-- =============================================
-- 初期データ
-- =============================================

-- デフォルト店舗（パスワード: 1234）
INSERT INTO fridges (fridge_id, fridge_name, fridge_icon, password_hash) VALUES
(1, '渋谷店', '🏪', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqgOdP/C3.');

-- シーケンスをリセット
SELECT setval('fridges_fridge_id_seq', 1, true);

-- デフォルトカテゴリ
INSERT INTO categories (fridge_id, name) VALUES
(1, '食材'),
(1, 'パック・容器'),
(1, '調味料');

-- =============================================
-- コメント
-- =============================================
-- container_type の値:
--   1: 液体ボトル
--   2: チューブ/袋
--   3: 粉末/固形

-- quantity_level の値:
--   1: 満タン(緑) - 在庫十分
--   2: 半分(黄色) - そろそろ発注
--   3: 少ない(オレンジ) - 至急発注
--   4: なし(赤) - 在庫切れ

-- role の値:
--   'owner': 店長（店舗作成者）
--   'member': スタッフ（共有メンバー）

-- password_hash:
--   bcryptでハッシュ化された4桁パスワード
--   デフォルトパスワード「1234」