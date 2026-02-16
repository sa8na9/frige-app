-- =============================================
-- 冷蔵庫管理アプリ データベーススキーマ
-- =============================================
-- データベース: fridge_app
-- 作成日: 2025-02-15
-- =============================================

-- 既存のテーブルを削除(開発時のリセット用)
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS user_fridges;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS fridges;

-- =============================================
-- 1. fridgesテーブル(冷蔵庫情報)
-- =============================================
CREATE TABLE fridges (
    fridge_id INT AUTO_INCREMENT PRIMARY KEY,
    fridge_name VARCHAR(50) NOT NULL,
    owner_user_id INT NULL,
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
-- 3. user_fridgesテーブル(ユーザー冷蔵庫関連) ※Phase2で実装
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
-- 4. itemsテーブル(調味料情報)
-- =============================================
CREATE TABLE items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fridge_id INT NOT NULL DEFAULT 1,
    name VARCHAR(50) NOT NULL,
    container_type INT NOT NULL,
    quantity_level INT NOT NULL DEFAULT 1,
    purchase_date DATE DEFAULT (CURRENT_DATE),
    expiry_date DATE NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_fridge (fridge_id),
    INDEX idx_expiry (expiry_date),
    INDEX idx_quantity (quantity_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================
-- 5. shopping_listテーブル(買い物リスト) ※Phase2で実装
-- =============================================
CREATE TABLE shopping_list (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fridge_id INT NOT NULL DEFAULT 1,
    item_name VARCHAR(50) NOT NULL,
    is_purchased BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fridge (fridge_id),
    INDEX idx_purchased (is_purchased)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================
-- コメント
-- =============================================
-- container_type の値:
--   1: 液体ボトル
--   2: チューブ
--   3: 粉末ボトル

-- quantity_level の値:
--   1: 満タン(緑)
--   2: 半分(黄色)
--   3: 少ない(オレンジ)
--   4: なし(赤)

-- role の値:
--   'owner': 冷蔵庫の作成者
--   'member': 共有メンバー