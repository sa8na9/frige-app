from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import psycopg2
import psycopg2.extras
from config import get_db_config, USE_PRODUCTION
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# 🔍 デバッグ情報を出力
print("=" * 60)
print("🔍 デバッグ情報 - アプリ起動時")
print("=" * 60)
print(f"USE_PRODUCTION: {USE_PRODUCTION}")
print(f"DATABASE_URL環境変数: {os.environ.get('DATABASE_URL', '❌ 未設定')}")
print(f"PRODUCTION環境変数: {os.environ.get('PRODUCTION', '❌ 未設定')}")
print(f"実際の接続先設定:")
config = get_db_config()
if isinstance(config, str):
    # PostgreSQL接続文字列の場合はパスワード部分を隠す
    masked_config = config.replace(config.split(':')[2].split('@')[0], '***PASSWORD***')
    print(f"  PostgreSQL: {masked_config}")
else:
    # MySQL設定辞書の場合
    print(f"  MySQL: host={config.get('host')}, database={config.get('database')}")
print("=" * 60)
print()

# データベース接続を取得
def get_db_connection():
    config = get_db_config()
    if USE_PRODUCTION:
        # PostgreSQL (Supabase) - 接続文字列で接続
        print("🔗 PostgreSQLに接続しています...")
        return psycopg2.connect(config)
    else:
        # MySQL (XAMPP) - 辞書形式で接続
        print("🔗 MySQL(XAMPP)に接続しています...")
        return mysql.connector.connect(**config)

# カテゴリ一覧を取得（他の関数から呼び出す用）
def get_categories(conn):
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM categories WHERE fridge_id = 1 ORDER BY id"
    cursor.execute(query)
    categories = cursor.fetchall()
    cursor.close()
    
    return categories

# 冷蔵庫選択画面(ハリボテ)
@app.route('/')
def fridge_select():
    return render_template('fridge_select.html', show_back_button=False)

# 調味料一覧画面(メイン) - カテゴリ対応版
@app.route('/items')
def items_list():
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # カテゴリ一覧を取得
    categories = get_categories(conn)
    
    # カテゴリIDを取得（デフォルトは1：調味料）
    category_id = request.args.get('category', 1, type=int)
    
    # ソートパラメータを取得
    sort_by = request.args.get('sort', 'expiry')
    
    # ソート条件を構築
    if sort_by == 'quantity':
        order_clause = "ORDER BY quantity_level DESC, expiry_date"
    else:
        if USE_PRODUCTION:
            order_clause = """
                ORDER BY 
                    CASE 
                        WHEN expiry_date IS NULL THEN 2
                        WHEN expiry_date < CURRENT_DATE THEN 0
                        WHEN expiry_date <= CURRENT_DATE + INTERVAL '7 days' THEN 1
                        ELSE 2
                    END,
                    expiry_date
            """
        else:
            order_clause = """
                ORDER BY 
                    CASE 
                        WHEN expiry_date IS NULL THEN 2
                        WHEN expiry_date < CURDATE() THEN 0
                        WHEN expiry_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) THEN 1
                        ELSE 2
                    END,
                    expiry_date
            """
    
    # 調味料を取得（カテゴリでフィルタ）
    query = f"""
        SELECT 
            id,
            name,
            container_type,
            quantity_level,
            opened_date,
            expiry_date,
            memo,
            created_at
        FROM items
        WHERE fridge_id = 1 AND category_id = %s
        {order_clause}
    """
    
    cursor.execute(query, (category_id,))
    items = cursor.fetchall()
    
    # 各調味料に追加情報を付与
    today = datetime.now().date()
    for item in items:
        container_types = {1: '液体', 2: 'チューブ', 3: '粉末'}
        item['container_type_text'] = container_types.get(item['container_type'], '不明')
        
        # 賞味期限のステータス
        if item['expiry_date']:
            if item['expiry_date'] < today:
                item['expiry_status'] = 'expired'
                item['expiry_class'] = 'text-danger'
                item['expiry_icon'] = '❌'
            elif item['expiry_date'] <= today + timedelta(days=7):
                item['expiry_status'] = 'warning'
                item['expiry_class'] = 'text-warning'
                item['expiry_icon'] = '⚠️'
            else:
                item['expiry_status'] = 'normal'
                item['expiry_class'] = ''
                item['expiry_icon'] = ''
        else:
            item['expiry_status'] = 'none'
            item['expiry_class'] = ''
            item['expiry_icon'] = ''

        # 開封日からの経過日数
        if item['opened_date']:
            days = (today - item['opened_date']).days
            item['days_since_open'] = days
            if days >= 90:
                item['days_since_open_class'] = 'days-open-danger'
            elif days >= 30:
                item['days_since_open_class'] = 'days-open-warning'
            else:
                item['days_since_open_class'] = 'days-open-normal'
        else:
            item['days_since_open'] = None
            item['days_since_open_class'] = ''
        
        # リストに追加ボタンを表示するか（期限切れ OR 残量無）
        item['show_add_to_list'] = (
            item['quantity_level'] == 4 or 
            (item['expiry_date'] and item['expiry_date'] < today)
        )
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', 
                         items=items, 
                         categories=categories,
                         current_category=category_id,
                         current_sort=sort_by, 
                         show_back_button=True)

# 残量をワンタップで更新
@app.route('/update_quantity/<int:item_id>/<int:new_level>', methods=['POST'])
def update_quantity(item_id, new_level):
    if new_level not in [1, 2, 3, 4]:
        flash('無効な残量レベルです', 'error')
        return redirect(url_for('items_list'))
    
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # アイテムのcategory_idを取得
    query = "SELECT category_id FROM items WHERE id = %s"
    cursor.execute(query, (item_id,))
    item = cursor.fetchone()
    category_id = item['category_id'] if item else 1
    
    # 残量を更新
    query = "UPDATE items SET quantity_level = %s WHERE id = %s"
    cursor.execute(query, (new_level, item_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('残量を更新しました', 'success')
    return redirect(url_for('items_list', category=category_id))

# 調味料削除(確認ダイアログはJavaScriptで実装)
@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # アイテムのcategory_idを取得
    query = "SELECT category_id FROM items WHERE id = %s"
    cursor.execute(query, (item_id,))
    item = cursor.fetchone()
    category_id = item['category_id'] if item else 1
    
    # 削除
    query = "DELETE FROM items WHERE id = %s"
    cursor.execute(query, (item_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('調味料を削除しました', 'success')
    return redirect(url_for('items_list', category=category_id))

# 調味料登録画面
@app.route('/register')
def register():
    conn = get_db_connection()
    categories = get_categories(conn)
    
    # 現在選択中のカテゴリIDを取得（デフォルトは1）
    current_category = request.args.get('category', 1, type=int)
    
    # カテゴリ名を取得
    category_name = '調味料'
    for cat in categories:
        if cat['id'] == current_category:
            category_name = cat['name']
            break
    
    conn.close()
    
    return render_template('register.html', 
                         categories=categories, 
                         current_category=current_category,
                         category_name=category_name,
                         show_back_button=True)

# 調味料登録処理
@app.route('/register', methods=['POST'])
def register_post():
    name = request.form.get('name')
    category_id = request.form.get('category_id', 1, type=int)
    container_type = request.form.get('container_type', 1, type=int)
    quantity_level = request.form.get('quantity_level', 1, type=int)
    opened_date = request.form.get('opened_date') or None
    expiry_date = request.form.get('expiry_date') or None
    memo = request.form.get('memo') or None
    
    # バリデーション
    if not name or len(name) > 50:
        flash('調味料名は必須です(50文字以内)', 'error')
        return redirect(url_for('register'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO items (fridge_id, category_id, name, container_type, quantity_level, opened_date, expiry_date, memo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (1, category_id, name, container_type, quantity_level, opened_date, expiry_date, memo))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('調味料を登録しました', 'success')
    return redirect(url_for('items_list', category=category_id))

# 調味料編集画面
@app.route('/edit/<int:item_id>')
def edit(item_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM items WHERE id = %s"
    cursor.execute(query, (item_id,))
    item = cursor.fetchone()
    
    cursor.close()
    
    if not item:
        conn.close()
        flash('調味料が見つかりません', 'error')
        return redirect(url_for('items_list'))
    
    # connを閉じる前にカテゴリを取得
    categories = get_categories(conn)
    
    # カテゴリ名を取得
    category_name = '調味料'
    for cat in categories:
        if cat['id'] == item['category_id']:
            category_name = cat['name']
            break
    
    conn.close()
    
    return render_template('edit.html', item=item, categories=categories, category_name=category_name, show_back_button=True)

# 調味料更新処理
@app.route('/edit/<int:item_id>', methods=['POST'])
def edit_post(item_id):
    name = request.form.get('name')
    category_id = request.form.get('category_id', type=int)
    container_type = request.form.get('container_type', type=int)
    quantity_level = request.form.get('quantity_level', type=int)
    opened_date = request.form.get('opened_date') or None
    expiry_date = request.form.get('expiry_date') or None
    memo = request.form.get('memo') or None
    
    # バリデーション
    if not name or len(name) > 50:
        flash('調味料名は必須です(50文字以内)', 'error')
        return redirect(url_for('edit', item_id=item_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        UPDATE items 
        SET category_id = %s, name = %s, container_type = %s, quantity_level = %s, opened_date = %s, expiry_date = %s, memo = %s
        WHERE id = %s
    """
    cursor.execute(query, (category_id, name, container_type, quantity_level, opened_date, expiry_date, memo, item_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('調味料を更新しました', 'success')
    return redirect(url_for('items_list', category=category_id))

# 共有設定画面(ハリボテ)
@app.route('/share_settings')
def share_settings():
    return render_template('share_settings.html', show_back_button=True)

# ==================== 買い物リスト機能 ====================

# 買い物リスト画面
@app.route('/shopping_list')
def shopping_list():
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM shopping_list WHERE fridge_id = 1 ORDER BY created_at"
    cursor.execute(query)
    items = cursor.fetchall()
    
    # 容器タイプのテキスト追加
    container_types = {1: '液体', 2: 'チューブ', 3: '粉末'}
    for item in items:
        item['container_type_text'] = container_types.get(item['container_type'], '不明')
    
    cursor.close()
    conn.close()
    
    return render_template('shopping_list.html', items=items, show_back_button=True)

# 買い物リストに追加
@app.route('/add_to_shopping_list/<int:item_id>', methods=['POST'])
def add_to_shopping_list(item_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # 調味料情報を取得
    query = "SELECT name, container_type, memo FROM items WHERE id = %s"
    cursor.execute(query, (item_id,))
    item = cursor.fetchone()
    
    if item:
        # 買い物リストに追加
        query = "INSERT INTO shopping_list (fridge_id, item_name, container_type, memo) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (1, item['name'], item['container_type'], item['memo']))
        conn.commit()
        flash(f'{item["name"]}を買い物リストに追加しました', 'success')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('items_list'))

# 買い物リストのチェック状態を切り替え
@app.route('/toggle_shopping_check/<int:shopping_id>', methods=['POST'])
def toggle_shopping_check(shopping_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "UPDATE shopping_list SET is_checked = NOT is_checked WHERE id = %s"
    cursor.execute(query, (shopping_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('shopping_list'))

# 買い物リストから新規登録画面へ
@app.route('/purchase_from_list/<int:shopping_id>')
def purchase_from_list(shopping_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM shopping_list WHERE id = %s"
    cursor.execute(query, (shopping_id,))
    shopping_item = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not shopping_item:
        flash('買い物リストに見つかりません', 'error')
        return redirect(url_for('shopping_list'))
    
    return render_template('purchase_from_list.html', shopping_item=shopping_item, show_back_button=True)

# 買い物リストから登録処理
@app.route('/purchase_from_list/<int:shopping_id>', methods=['POST'])
def purchase_from_list_post(shopping_id):
    name = request.form.get('name')
    container_type = request.form.get('container_type', type=int)
    quantity_level = request.form.get('quantity_level', type=int)
    opened_date = request.form.get('opened_date') or None
    expiry_date = request.form.get('expiry_date') or None
    memo = request.form.get('memo') or None
    
    # バリデーション
    if not name or len(name) > 50:
        flash('調味料名は必須です(50文字以内)', 'error')
        return redirect(url_for('purchase_from_list', shopping_id=shopping_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 調味料を登録
    query = """
        INSERT INTO items (fridge_id, name, container_type, quantity_level, opened_date, expiry_date, memo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (1, name, container_type, quantity_level, opened_date, expiry_date, memo))
    
    # 買い物リストから削除
    query = "DELETE FROM shopping_list WHERE id = %s"
    cursor.execute(query, (shopping_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('調味料を登録しました', 'success')
    return redirect(url_for('shopping_list'))

# カテゴリ新規作成API
@app.route('/add_category', methods=['POST'])
def add_category():
    name = request.form.get('name')
    
    if not name or len(name) > 50:
        flash('カテゴリ名は必須です（50文字以内）', 'error')
        return redirect(url_for('items_list'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "INSERT INTO categories (fridge_id, name) VALUES (%s, %s)"
    cursor.execute(query, (1, name))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash(f'カテゴリ「{name}」を作成しました', 'success')
    return redirect(url_for('items_list'))

# 買い物リスト手動登録画面
@app.route('/add_shopping_manual')
def add_shopping_manual():
    return render_template('add_shopping_manual.html', show_back_button=True)

# 買い物リスト手動登録処理
@app.route('/add_shopping_manual', methods=['POST'])
def add_shopping_manual_post():
    item_name = request.form.get('item_name')
    container_type = request.form.get('container_type', 1, type=int)
    memo = request.form.get('memo') or None
    
    # バリデーション
    if not item_name or len(item_name) > 50:
        flash('調味料名は必須です(50文字以内)', 'error')
        return redirect(url_for('add_shopping_manual'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "INSERT INTO shopping_list (fridge_id, item_name, container_type, memo) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (1, item_name, container_type, memo))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash(f'{item_name}を買い物リストに追加しました', 'success')
    return redirect(url_for('shopping_list'))

# 買い物終了（チェック済みアイテム削除）
@app.route('/finish_shopping', methods=['POST'])
def finish_shopping():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "DELETE FROM shopping_list WHERE fridge_id = 1 AND is_checked = TRUE"
    cursor.execute(query)
    deleted_count = cursor.rowcount
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash(f'チェック済みの{deleted_count}件を削除しました', 'success')
    return redirect(url_for('shopping_list'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)