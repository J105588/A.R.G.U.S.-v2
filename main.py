# main.py (Final Complete Version)

import os
from flask import Flask, jsonify, render_template, request, abort
from models import DatabaseManager

# --- アプリケーションのセットアップ ---
# プロジェクトルートを基準にtemplateとstaticフォルダの絶対パスを指定
# これにより、どこから実行してもパスがずれる問題を防ぎます。
project_root = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(project_root, 'templates')
static_dir = os.path.join(project_root, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# --- データベースと設定ファイルのパスをセットアップ ---
# プロジェクトルートにデータベースファイル（argus.db）を作成
db_path = os.path.join(project_root, 'argus.db')
db = DatabaseManager(db_path=db_path)

# configフォルダへの絶対パス
config_dir = os.path.join(project_root, 'config')
BLOCKED_DOMAINS_FILE = os.path.join(config_dir, 'blocked_domains.txt')


# --- メインのWebページ ---

@app.route('/')
def index():
    """監視ダッシュボードのメインページを返します。"""
    # templates/index.html をレンダリングします。
    # このHTMLは内部で static/js/app.js と static/css/style.css を読み込みます。
    return render_template('index.html')


# --- APIエンドポイント (監視画面のJavaScriptから呼び出されます) ---

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """データベースから最新のログを取得してJSON形式で返します。"""
    try:
        logs = db.get_logs(limit=250) # 最新250件を取得
        return jsonify(logs)
    except Exception as e:
        print(f"Error in get_logs: {e}")
        return jsonify({"error": "Failed to retrieve logs"}), 500


@app.route('/api/logs', methods=['DELETE'])
def clear_logs():
    """データベースの全ログをクリアします。"""
    try:
        db.clear_logs()
        return jsonify({'status': 'success', 'message': 'All logs cleared.'})
    except Exception as e:
        print(f"Error in clear_logs: {e}")
        return jsonify({"error": "Failed to clear logs"}), 500


@app.route('/api/rules/domains', methods=['GET'])
def get_domain_rules():
    """ブロック対象ドメインのリストをファイルから読み込んで返します。"""
    if not os.path.exists(BLOCKED_DOMAINS_FILE):
        return jsonify([]) # ファイルが存在しない場合は空のリストを返す
    
    try:
        with open(BLOCKED_DOMAINS_FILE, 'r', encoding='utf-8') as f:
            # コメント行 ('#') と空行を除外してリスト化
            domains = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return jsonify(domains)
    except Exception as e:
        print(f"Error in get_domain_rules: {e}")
        return jsonify({"error": "Failed to read domain rules"}), 500


@app.route('/api/rules/domains', methods=['POST'])
def add_domain_rule():
    """新しいドメインをブロックリストに追加します。"""
    data = request.get_json()
    if not data or 'domain' not in data or not data['domain'].strip():
        abort(400, 'JSON data with a non-empty "domain" key is required.')
    
    domain_to_add = data['domain'].strip().lower()
    
    try:
        # フォルダが存在しない場合は作成
        os.makedirs(config_dir, exist_ok=True)
        
        # 既存ルールを読み込み、重複をチェック
        existing_domains = set()
        if os.path.exists(BLOCKED_DOMAINS_FILE):
            with open(BLOCKED_DOMAINS_FILE, 'r', encoding='utf-8') as f:
                existing_domains = {line.strip().lower() for line in f}

        if domain_to_add in existing_domains:
            return jsonify({'status': 'skipped', 'message': f'Domain "{domain_to_add}" already exists.'}), 200

        # ファイルの末尾に新しいドメインを追記
        # ファイル末尾に改行がない場合でも大丈夫なように、追記前に改行を入れます。
        with open(BLOCKED_DOMAINS_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n{domain_to_add}")
            
    except Exception as e:
        print(f"Error in add_domain_rule: {e}")
        return jsonify({"error": f"Failed to add domain rule: {e}"}), 500
            
    return jsonify({'status': 'success', 'domain': domain_to_add}), 201


# --- Flaskアプリの実行 ---

if __name__ == '__main__':
    # host='0.0.0.0' で、PCのIPアドレスを指定してもアクセス可能になります。
    # debug=True は開発中にエラー詳細が表示されて便利です。
    app.run(host='0.0.0.0', port=5000, debug=True)