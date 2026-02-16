from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import psycopg2
import psycopg2.extras
from config import get_db_config, USE_PRODUCTION
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# データベース接続を取得
def get_db_connection():
    config = get_db_config()
    if USE_PRODUCTION:
        # PostgreSQL (Supabase) - 接続文字列で接続
        return psycopg2.connect(config)
    else:
        # MySQL (XAMPP) - 辞書形式で接続
        return mysql.connector.connect(**config)

# 冷蔵庫選択画面(ハリボテ)
@app.route('/')
def fridge_select():
    return render_template('fridge_select.html')

# 調味料一覧画面(メイン)
@app.route('/items')
def items_list():
    conn = get_db_connection()
    if USE_PRODUCTION:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor(dictionary=True)
    
    # ソートパラメータを取得
    sort_by = request.args.get('sort', 'expiry')  # デフォルトは期限順
    
    # ソート条件を構築
    if sort_by == 'quantity':
        # 残量順: なし(4) → 少ない(3) → 半分(2) → 満タン(1)
        order_clause = "ORDER BY quantity_level DESC, expiry_date, purchase_date DESC"
    else:
        # 期限順: 期限切れ → 1週間以内 → それ以降
        # 期限未設定の場合は購入日でソート
        # PostgreSQL対応版
        order_clause = """
            ORDER BY 
                CASE 
                    WHEN expiry_date IS NULL THEN 2
                    WHEN expiry_date < CURRENT_DATE THEN 0
                    WHEN expiry_date <= CURRENT_DATE + INTERVAL '7 days' THEN 1
                    ELSE 2
                END,
                expiry_date,
                purchase_date DESC
        """
    
    # 調味料を取得
    query = f"""
        SELECT 
            id,
            name,
            container_type,
            quantity_level,
            purchase_date,
            opened_date,
            expiry_date,
            created_at
        FROM items
        WHERE fridge_id = 1
        {order_clause}
    """
    
    cursor.execute(query)
    items = cursor.fetchall()
    
    # 各調味料に追加情報を付与
    today = datetime.now().date()
    for item in items:
        # 容器タイプのテキスト
        container_types = {1: '液体', 2: 'チューブ', 3: '粉末'}
        item['container_type_text'] = container_types.get(item['container_type'], '不明')
        
        # 賞味期限のステータス
        if item['expiry_date']:
            if item['expiry_date'] < today:
                item['expiry_status'] = 'expired'  # 期限切れ
                item['expiry_class'] = 'text-danger'
                item['expiry_icon'] = '❌'
            elif item['expiry_date'] <= today + timedelta(days=7):
                item['expiry_status'] = 'warning'  # 1週間以内
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
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', items=items, current_sort=sort_by)

# 残量をワンタップで更新
@app.route('/update_quantity/<int:item_id>/<int:new_level>', methods=['POST'])
def update_quantity(item_id, new_level):
    if new_level not in [1, 2, 3, 4]:
        flash('無効な残量レベルです', 'error')
        return redirect(url_for('items_list'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "UPDATE items SET quantity_level = %s WHERE id = %s"
    cursor.execute(query, (new_level, item_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('残量を更新しました', 'success')
    return redirect(url_for('items_list'))

# 調味料削除(確認ダイアログはJavaScriptで実装)
@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "DELETE FROM items WHERE id = %s"
    cursor.execute(query, (item_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('調味料を削除しました', 'success')
    return redirect(url_for('items_list'))

# 調味料登録画面
@app.route('/register')
def register():
    return render_template('register.html')

# 調味料登録処理
@app.route('/register', methods=['POST'])
def register_post():
    name = request.form.get('name')
    container_type = request.form.get('container_type', 1, type=int)
    quantity_level = request.form.get('quantity_level', 1, type=int)
    purchase_date = request.form.get('purchase_date') or datetime.now().date()
    opened_date = request.form.get('opened_date') or None
    expiry_date = request.form.get('expiry_date') or None
    
    # バリデーション
    if not name or len(name) > 50:
        flash('調味料名は必須です(50文字以内)', 'error')
        return redirect(url_for('register'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO items (fridge_id, name, container_type, quantity_level, purchase_date, opened_date, expiry_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (1, name, container_type, quantity_level, purchase_date, opened_date, expiry_date))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('調味料を登録しました', 'success')
    return redirect(url_for('items_list'))

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
    conn.close()
    
    if not item:
        flash('調味料が見つかりません', 'error')
        return redirect(url_for('items_list'))
    
    return render_template('edit.html', item=item)

# 調味料更新処理
@app.route('/edit/<int:item_id>', methods=['POST'])
def edit_post(item_id):
    name = request.form.get('name')
    container_type = request.form.get('container_type', type=int)
    quantity_level = request.form.get('quantity_level', type=int)
    purchase_date = request.form.get('purchase_date')
    opened_date = request.form.get('opened_date') or None
    expiry_date = request.form.get('expiry_date') or None
    
    # バリデーション
    if not name or len(name) > 50:
        flash('調味料名は必須です(50文字以内)', 'error')
        return redirect(url_for('edit', item_id=item_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        UPDATE items 
        SET name = %s, container_type = %s, quantity_level = %s, 
            purchase_date = %s, opened_date = %s, expiry_date = %s
        WHERE id = %s
    """
    cursor.execute(query, (name, container_type, quantity_level, purchase_date, opened_date, expiry_date, item_id))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('調味料を更新しました', 'success')
    return redirect(url_for('items_list'))

# 共有設定画面(ハリボテ)
@app.route('/share_settings')
def share_settings():
    return render_template('share_settings.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)