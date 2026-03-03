from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import psycopg2
import psycopg2.extras
from config import get_db_config, USE_PRODUCTION
from datetime import datetime, timedelta
import pytz
import os
import bcrypt

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# デバッグ情報を出力
print("=" * 60)
print("🔍 デバッグ情報 - アプリ起動時")
print("=" * 60)
print(f"USE_PRODUCTION: {USE_PRODUCTION}")
print(f"DATABASE_URL環境変数: {os.environ.get('DATABASE_URL', '❌ 未設定')}")
print(f"PRODUCTION環境変数: {os.environ.get('PRODUCTION', '❌ 未設定')}")
print(f"実際の接続先設定:")
config = get_db_config()
if isinstance(config, str):
    masked_config = config.replace(config.split(':')[2].split('@')[0], '***PASSWORD***')
    print(f"  PostgreSQL: {masked_config}")
else:
    print(f"  MySQL: host={config.get('host')}, database={config.get('database')}")
print("=" * 60)
print()

# データベース接続を取得
def get_db_connection():
    config = get_db_config()
    if USE_PRODUCTION:
        print("🔗 PostgreSQLに接続しています...")
        return psycopg2.connect(config)
    else:
        print("🔗 MySQL(XAMPP)に接続しています...")
        return mysql.connector.connect(**config)


# 日本時間（JST）の現在日付を取得
def get_japan_time():
    """日本時間（JST）の現在日付を取得"""
    jst = pytz.timezone('Asia/Tokyo')
    return datetime.now(jst).date()

# カテゴリ一覧を取得
def get_categories(conn, store_id):
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM categories WHERE fridge_id = %s ORDER BY id"
    cursor.execute(query, (store_id,))
    categories = cursor.fetchall()
    cursor.close()
    
    return categories

# =============================================
# 店舗管理
# =============================================

# 店舗選択画面
@app.route('/')
def store_select():
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM fridges ORDER BY created_at"
    cursor.execute(query)
    stores = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('store_select.html', stores=stores, show_back_button=False)

# 店舗作成画面
@app.route('/create_store')
def create_store():
    return render_template('create_store.html', show_back_button=True)

# 店舗作成処理
@app.route('/create_store', methods=['POST'])
def create_store_post():
    store_name = request.form.get('store_name')
    store_icon = request.form.get('store_icon', '🏪')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')
    
    # バリデーション
    if not store_name or len(store_name) > 50:
        flash('店舗名は必須です（50文字以内）', 'error')
        return redirect(url_for('create_store'))
    
    if not password or len(password) != 4 or not password.isdigit():
        flash('パスワードは4桁の数字で入力してください', 'error')
        return redirect(url_for('create_store'))
    
    if password != password_confirm:
        flash('パスワードが一致しません', 'error')
        return redirect(url_for('create_store'))
    
    # パスワードをハッシュ化
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 店舗を作成
    query = "INSERT INTO fridges (fridge_name, fridge_icon, password_hash) VALUES (%s, %s, %s)"
    cursor.execute(query, (store_name, store_icon, password_hash))
    conn.commit()
    
    # 作成した店舗のIDを取得
    if USE_PRODUCTION:
        cursor.execute("SELECT lastval()")
    else:
        cursor.execute("SELECT LAST_INSERT_ID()")
    store_id = cursor.fetchone()[0]
    
    # デフォルトカテゴリを作成
    categories = ['食材', 'パック・容器', '調味料']
    query = "INSERT INTO categories (fridge_id, name) VALUES (%s, %s)"
    for cat_name in categories:
        cursor.execute(query, (store_id, cat_name))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash(f'店舗「{store_name}」を作成しました', 'success')
    return redirect(url_for('store_select'))

# 店舗削除画面
@app.route('/store/<int:store_id>/delete')
def delete_store_confirm(store_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM fridges WHERE fridge_id = %s"
    cursor.execute(query, (store_id,))
    store = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not store:
        flash('店舗が見つかりません', 'error')
        return redirect(url_for('store_select'))
    
    return render_template('delete_store.html', store=store, show_back_button=True)

# 店舗編集画面
@app.route('/store/<int:store_id>/edit')
def edit_store(store_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM fridges WHERE fridge_id = %s"
    cursor.execute(query, (store_id,))
    store = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not store:
        flash('店舗が見つかりません', 'error')
        return redirect(url_for('store_select'))
    
    return render_template('edit_store.html', store=store, show_back_button=False)

# 店舗情報更新処理
@app.route('/store/<int:store_id>/update_info', methods=['POST'])
def update_store_info(store_id):
    store_name = request.form.get('store_name')
    store_icon = request.form.get('store_icon', '🏪')
    
    # バリデーション
    if not store_name or len(store_name) > 50:
        flash('店舗名は必須です（50文字以内）', 'error')
        return redirect(url_for('edit_store', store_id=store_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "UPDATE fridges SET fridge_name = %s, fridge_icon = %s WHERE fridge_id = %s"
    cursor.execute(query, (store_name, store_icon, store_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('店舗情報を更新しました', 'success')
    return redirect(url_for('edit_store', store_id=store_id))

# 店舗削除処理
@app.route('/store/<int:store_id>/delete', methods=['POST'])
def delete_store_post(store_id):
    password = request.form.get('password')
    confirm_text = request.form.get('confirm_text')
    
    # 確認テキストチェック
    if confirm_text != '削除':
        flash('確認テキストが正しくありません', 'error')
        return redirect(url_for('delete_store_confirm', store_id=store_id))
    
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # 店舗情報を取得
    query = "SELECT * FROM fridges WHERE fridge_id = %s"
    cursor.execute(query, (store_id,))
    store = cursor.fetchone()
    
    if not store:
        flash('店舗が見つかりません', 'error')
        conn.close()
        return redirect(url_for('store_select'))
    
    # パスワード確認
    if not bcrypt.checkpw(password.encode('utf-8'), store['password_hash'].encode('utf-8')):
        flash('パスワードが正しくありません', 'error')
        conn.close()
        return redirect(url_for('delete_store_confirm', store_id=store_id))
    
    # 店舗を削除（CASCADE削除により関連データも削除）
    cursor = conn.cursor()
    query = "DELETE FROM fridges WHERE fridge_id = %s"
    cursor.execute(query, (store_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash(f'店舗「{store["fridge_name"]}」を削除しました', 'success')
    return redirect(url_for('store_select'))

# =============================================
# 在庫管理
# =============================================

# 在庫一覧画面
@app.route('/store/<int:store_id>/inventory')
def inventory_list(store_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # カテゴリ一覧を取得
    categories = get_categories(conn, store_id)
    
    # カテゴリIDを取得
    category_id = request.args.get('category', None, type=int)
    if category_id is None and categories:
        category_id = categories[0]['id']
    
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
    
    # 在庫を取得
    query = f"""
        SELECT id, name, quantity_level, opened_date, expiry_date, memo, created_at
        FROM items
        WHERE fridge_id = %s AND category_id = %s
        {order_clause}
    """
    cursor.execute(query, (store_id, category_id))
    items = cursor.fetchall()
    
    # 各在庫に追加情報を付与
    today = get_japan_time()
    for item in items:
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
        if item.get('opened_date'):
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
        
        # 発注リストに追加ボタンを表示するか
        item['show_add_to_list'] = (
            item['quantity_level'] >= 3 or 
            (item['expiry_date'] and item['expiry_date'] < today)
        )
    
    # 発注リストに登録済みのitem_idを取得
    query_shopping = "SELECT item_id FROM shopping_list WHERE fridge_id = %s AND item_id IS NOT NULL"
    cursor.execute(query_shopping, (store_id,))
    shopping_items = cursor.fetchall()
    shopping_item_ids = [item['item_id'] for item in shopping_items]
    
    # 各アイテムが発注リストに登録済みかチェック
    for item in items:
        item['in_shopping_list'] = item['id'] in shopping_item_ids
    
    cursor.close()
    conn.close()
    
    return render_template('inventory_list.html', 
                         items=items, 
                         categories=categories,
                         current_category=category_id,
                         current_sort=sort_by,
                         store_id=store_id,
                         show_back_button=True)

# 残量をワンタップで更新
@app.route('/store/<int:store_id>/update_quantity/<int:item_id>/<int:new_level>', methods=['POST'])
def update_quantity(store_id, item_id, new_level):
    if new_level not in [1, 2, 3, 4]:
        flash('無効な残量レベルです', 'error')
        return redirect(url_for('inventory_list', store_id=store_id))
    
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # アイテムのcategory_idを取得
    query = "SELECT category_id FROM items WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (item_id, store_id))
    item = cursor.fetchone()
    category_id = item['category_id'] if item else 1
    
    # 残量を更新
    query = "UPDATE items SET quantity_level = %s WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (new_level, item_id, store_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    # 現在のソート順を取得
    current_sort = request.args.get('sort', 'expiry')
    
    flash('残量を更新しました', 'success')
    return redirect(url_for('inventory_list', store_id=store_id, category=category_id, sort=current_sort))

# 在庫削除
@app.route('/store/<int:store_id>/delete_item/<int:item_id>', methods=['POST'])
def delete_item(store_id, item_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # アイテムのcategory_idを取得
    query = "SELECT category_id FROM items WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (item_id, store_id))
    item = cursor.fetchone()
    category_id = item['category_id'] if item else 1
    
    # 削除
    cursor = conn.cursor()
    query = "DELETE FROM items WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (item_id, store_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    # 現在のソート順を取得
    current_sort = request.args.get('sort', 'expiry')
    
    flash('在庫を削除しました', 'success')
    return redirect(url_for('inventory_list', store_id=store_id, category=category_id, sort=current_sort))

# 在庫登録画面
@app.route('/store/<int:store_id>/add_item')
def add_item(store_id):
    conn = get_db_connection()
    categories = get_categories(conn, store_id)
    
    # 現在選択中のカテゴリIDを取得
    current_category = request.args.get('category', None, type=int)
    if current_category is None and categories:
        current_category = categories[0]['id']
    
    # カテゴリ名を取得
    category_name = '在庫'
    for cat in categories:
        if cat['id'] == current_category:
            category_name = cat['name']
            break
    
    conn.close()
    
    return render_template('add_item.html', 
                         categories=categories, 
                         current_category=current_category,
                         category_name=category_name,
                         store_id=store_id,
                         show_back_button=True)

# 在庫登録処理
@app.route('/store/<int:store_id>/add_item', methods=['POST'])
def add_item_post(store_id):
    name = request.form.get('name')
    category_id = request.form.get('category_id', 1, type=int)
    quantity_level = request.form.get('quantity_level', 1, type=int)
    opened_date = request.form.get('opened_date') or None
    expiry_date = request.form.get('expiry_date') or None
    memo = request.form.get('memo') or None
    
    # バリデーション
    if not name or len(name) > 50:
        flash('商品名は必須です(50文字以内)', 'error')
        return redirect(url_for('add_item', store_id=store_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO items (fridge_id, category_id, name, container_type, quantity_level, opened_date, expiry_date, memo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (store_id, category_id, name, 1, quantity_level, opened_date, expiry_date, memo))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('在庫を登録しました', 'success')
    return redirect(url_for('inventory_list', store_id=store_id, category=category_id))

# 在庫編集画面
@app.route('/store/<int:store_id>/edit_item/<int:item_id>')
def edit_item(store_id, item_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM items WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (item_id, store_id))
    item = cursor.fetchone()
    
    cursor.close()
    
    if not item:
        conn.close()
        flash('在庫が見つかりません', 'error')
        return redirect(url_for('inventory_list', store_id=store_id))
    
    categories = get_categories(conn, store_id)
    
    # カテゴリ名を取得
    category_name = '在庫'
    for cat in categories:
        if cat['id'] == item['category_id']:
            category_name = cat['name']
            break
    
    conn.close()
    
    return render_template('edit_item.html', 
                         item=item, 
                         categories=categories, 
                         category_name=category_name, 
                         store_id=store_id,
                         show_back_button=True)

# 在庫更新処理
@app.route('/store/<int:store_id>/edit_item/<int:item_id>', methods=['POST'])
def edit_item_post(store_id, item_id):
    name = request.form.get('name')
    category_id = request.form.get('category_id', type=int)
    quantity_level = request.form.get('quantity_level', type=int)
    opened_date = request.form.get('opened_date') or None
    expiry_date = request.form.get('expiry_date') or None
    memo = request.form.get('memo') or None
    
    # バリデーション
    if not name or len(name) > 50:
        flash('商品名は必須です(50文字以内)', 'error')
        return redirect(url_for('edit_item', store_id=store_id, item_id=item_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        UPDATE items 
        SET category_id = %s, name = %s, container_type = %s, quantity_level = %s, opened_date = %s, expiry_date = %s, memo = %s
        WHERE id = %s AND fridge_id = %s
    """
    cursor.execute(query, (category_id, name, 1, quantity_level, opened_date, expiry_date, memo, item_id, store_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    # 現在のソート順を取得
    current_sort = request.args.get('sort', 'expiry')
    
    flash('在庫を更新しました', 'success')
    return redirect(url_for('inventory_list', store_id=store_id, category=category_id, sort=current_sort))

# =============================================
# 発注リスト機能
# =============================================

# 発注リスト画面
@app.route('/store/<int:store_id>/orders')
def order_list(store_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM shopping_list WHERE fridge_id = %s ORDER BY created_at"
    cursor.execute(query, (store_id,))
    items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('order_list.html', items=items, store_id=store_id, show_back_button=True)

# 発注リストに追加
@app.route('/store/<int:store_id>/add_to_order/<int:item_id>', methods=['POST'])
def add_to_order(store_id, item_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # 在庫情報を取得
    query = "SELECT name, memo, category_id FROM items WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (item_id, store_id))
    item = cursor.fetchone()
    
    if item:
        # 発注リストに追加
        cursor = conn.cursor()
        query = "INSERT INTO shopping_list (fridge_id, item_id, item_name, memo) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (store_id, item_id, item['name'], item['memo']))
        conn.commit()
        flash(f'{item["name"]}を発注リストに追加しました', 'success')
        category_id = item['category_id']
    else:
        category_id = 1
    
    cursor.close()
    conn.close()
    
    # 現在のソート順を取得
    current_sort = request.args.get('sort', 'expiry')
    
    return redirect(url_for('inventory_list', store_id=store_id, category=category_id, sort=current_sort))

# 発注リスト手動登録画面
@app.route('/store/<int:store_id>/add_order')
def add_order_manual(store_id):
    return render_template('add_order_manual.html', store_id=store_id, show_back_button=True)

# 発注リスト手動登録処理
@app.route('/store/<int:store_id>/add_order', methods=['POST'])
def add_order_manual_post(store_id):
    item_name = request.form.get('item_name')
    memo = request.form.get('memo') or None
    
    # バリデーション
    if not item_name or len(item_name) > 50:
        flash('商品名は必須です(50文字以内)', 'error')
        return redirect(url_for('add_order_manual', store_id=store_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "INSERT INTO shopping_list (fridge_id, item_name, memo) VALUES (%s, %s, %s)"
    cursor.execute(query, (store_id, item_name, memo))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash(f'{item_name}を発注リストに追加しました', 'success')
    return redirect(url_for('order_list', store_id=store_id))

# 発注リストのチェック状態を切り替え
@app.route('/store/<int:store_id>/toggle_order_check/<int:order_id>', methods=['POST'])
def toggle_order_check(store_id, order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "UPDATE shopping_list SET is_checked = NOT is_checked WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (order_id, store_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('order_list', store_id=store_id))

# 発注完了（チェック済みアイテム削除）
@app.route('/store/<int:store_id>/finish_order', methods=['POST'])
def finish_order(store_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "DELETE FROM shopping_list WHERE fridge_id = %s AND is_checked = TRUE"
    cursor.execute(query, (store_id,))
    deleted_count = cursor.rowcount
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash(f'チェック済みの{deleted_count}件を削除しました', 'success')
    return redirect(url_for('order_list', store_id=store_id))

# 発注品入荷画面
@app.route('/store/<int:store_id>/receive_from_order/<int:order_id>')
def receive_from_order(store_id, order_id):
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM shopping_list WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (order_id, store_id))
    order_item = cursor.fetchone()
    
    if not order_item:
        cursor.close()
        conn.close()
        flash('発注リストに見つかりません', 'error')
        return redirect(url_for('order_list', store_id=store_id))
    
    # カテゴリ一覧を取得
    categories = get_categories(conn, store_id)
    
    cursor.close()
    conn.close()
    
    return render_template('receive_from_order.html', 
                         order_item=order_item, 
                         categories=categories,
                         store_id=store_id,
                         show_back_button=True)

# 発注品入荷登録処理
@app.route('/store/<int:store_id>/receive_from_order/<int:order_id>', methods=['POST'])
def receive_from_order_post(store_id, order_id):
    name = request.form.get('name')
    category_id = request.form.get('category_id', type=int)
    quantity_level = request.form.get('quantity_level', type=int)
    opened_date = request.form.get('opened_date') or None
    expiry_date = request.form.get('expiry_date') or None
    memo = request.form.get('memo') or None
    
    # バリデーション
    if not name or len(name) > 50:
        flash('商品名は必須です(50文字以内)', 'error')
        return redirect(url_for('receive_from_order', store_id=store_id, order_id=order_id))
    
    # category_idが指定されていない場合、この店舗の最初のカテゴリを取得
    if not category_id:
        conn = get_db_connection()
        if USE_PRODUCTION:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cursor = conn.cursor(dictionary=True)
        
        query = "SELECT id FROM categories WHERE fridge_id = %s ORDER BY id LIMIT 1"
        cursor.execute(query, (store_id,))
        result = cursor.fetchone()
        category_id = result['id'] if result else 1
        cursor.close()
        conn.close()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 在庫を登録（category_idを含める）
    query = """
        INSERT INTO items (fridge_id, category_id, name, container_type, quantity_level, opened_date, expiry_date, memo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (store_id, category_id, name, 1, quantity_level, opened_date, expiry_date, memo))
    
    # 発注リストから削除
    query = "DELETE FROM shopping_list WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (order_id, store_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('在庫を登録しました', 'success')
    return redirect(url_for('order_list', store_id=store_id))

# =============================================
# カテゴリ管理
# =============================================

# カテゴリ新規作成API
@app.route('/store/<int:store_id>/add_category', methods=['POST'])
def add_category(store_id):
    name = request.form.get('name')
    
    if not name or len(name) > 50:
        flash('カテゴリ名は必須です（50文字以内）', 'error')
        return redirect(url_for('inventory_list', store_id=store_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "INSERT INTO categories (fridge_id, name) VALUES (%s, %s)"
    cursor.execute(query, (store_id, name))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash(f'カテゴリ「{name}」を作成しました', 'success')
    return redirect(url_for('inventory_list', store_id=store_id))

# カテゴリ削除API
@app.route('/store/<int:store_id>/delete_category', methods=['POST'])
def delete_category(store_id):
    category_id = request.form.get('category_id', type=int)
    
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # カテゴリ名を取得
    query = "SELECT name FROM categories WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (category_id, store_id))
    category = cursor.fetchone()
    
    if not category:
        flash('カテゴリが見つかりません', 'error')
        conn.close()
        return redirect(url_for('inventory_list', store_id=store_id))
    
    category_name = category['name']
    
    # カテゴリ数をチェック
    query = "SELECT COUNT(*) as count FROM categories WHERE fridge_id = %s"
    cursor.execute(query, (store_id,))
    result = cursor.fetchone()
    
    if result['count'] <= 1:
        flash('最後のカテゴリは削除できません', 'error')
        conn.close()
        return redirect(url_for('inventory_list', store_id=store_id))
    
    # このカテゴリのアイテムを全て削除
    cursor = conn.cursor()
    query = "DELETE FROM items WHERE category_id = %s AND fridge_id = %s"
    cursor.execute(query, (category_id, store_id))
    deleted_items = cursor.rowcount
    
    # カテゴリを削除
    query = "DELETE FROM categories WHERE id = %s AND fridge_id = %s"
    cursor.execute(query, (category_id, store_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash(f'カテゴリ「{category_name}」と{deleted_items}件のアイテムを削除しました', 'success')
    return redirect(url_for('inventory_list', store_id=store_id))

# =============================================
# その他
# =============================================

# 店舗設定画面(ハリボテ)
@app.route('/store/<int:store_id>/settings')
def store_settings(store_id):
    return render_template('store_settings.html', store_id=store_id, show_back_button=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)