-- =============================================
-- 店舗在庫管理システム データベーススキーマ (MySQL)
-- =============================================
-- データベース: fridge_app
-- 作成日: 2025-02-15
-- 更新日: 2026-02-26 (店舗在庫管理システムに変更)
-- =============================================

-- 既存のテーブルを削除(開発時のリセット用)
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS shopping_list;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS user_fridges;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS fridges;

-- =============================================
-- 1. fridgesテーブル(店舗情報)
-- =============================================
CREATE TABLE fridges (
    fridge_id INT AUTO_INCREMENT PRIMARY KEY,
    fridge_name VARCHAR(50) NOT NULL COMMENT '店舗名',
    fridge_icon VARCHAR(10) DEFAULT '🏪' COMMENT '絵文字アイコン',
    password_hash VARCHAR(255) NOT NULL COMMENT '4桁パスワードのハッシュ',
    owner_user_id INT NULL COMMENT '作成者ID（Phase2実装予定）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_owner (owner_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================
-- 2. usersテーブル(ユーザー情報) ※Phase2で実装
-- =============================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================
-- 3. user_fridgesテーブル(ユーザー店舗関連) ※Phase2で実装
-- =============================================
CREATE TABLE user_fridges (
    user_id INT NOT NULL,
    fridge_id INT NOT NULL,
    role VARCHAR(20) DEFAULT 'member',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, fridge_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (fridge_id) REFERENCES fridges(fridge_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================
-- 4. categoriesテーブル(カテゴリ)
-- =============================================
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fridge_id INT NOT NULL DEFAULT 1,
    name VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fridge (fridge_id),
    FOREIGN KEY (fridge_id) REFERENCES fridges(fridge_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================
-- 5. itemsテーブル(在庫情報)
-- =============================================
CREATE TABLE items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fridge_id INT NOT NULL DEFAULT 1,
    category_id INT NOT NULL DEFAULT 1,
    name VARCHAR(50) NOT NULL COMMENT '商品名',
    container_type INT NOT NULL COMMENT '容器タイプ',
    quantity_level INT NOT NULL DEFAULT 1 COMMENT '残量レベル',
    opened_date DATE NULL COMMENT '開封日',
    expiry_date DATE NULL COMMENT '賞味期限',
    memo TEXT NULL COMMENT 'メモ（発注先、ロット番号など）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_fridge (fridge_id),
    INDEX idx_category (category_id),
    INDEX idx_expiry (expiry_date),
    INDEX idx_quantity (quantity_level),
    FOREIGN KEY (fridge_id) REFERENCES fridges(fridge_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================
-- 6. shopping_listテーブル(発注リスト)
-- =============================================
CREATE TABLE shopping_list (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fridge_id INT NOT NULL DEFAULT 1,
    item_id INT NULL COMMENT '元在庫ID（自動追加時のみ）',
    item_name VARCHAR(50) NOT NULL COMMENT '商品名',
    memo TEXT NULL COMMENT 'メモ（発注先、納期など）',
    is_checked BOOLEAN DEFAULT FALSE COMMENT '発注済みフラグ',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fridge (fridge_id),
    INDEX idx_item (item_id),
    FOREIGN KEY (fridge_id) REFERENCES fridges(fridge_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================
-- 初期データ
-- =============================================

-- デフォルト店舗（パスワード: 1234）
INSERT INTO fridges (fridge_id, fridge_name, fridge_icon, password_hash) VALUES
(1, '渋谷店', '🏪', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqgOdP/C3.');

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