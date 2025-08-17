# proxy_addon.py (Final Confirmed Version - HTML Template Fix)

import os
import sys
import time
from mitmproxy import http, ctx

# ==============================================================================
# ★★★ 重要なパス設定 ★★★
# このスクリプト自身の絶対パスを取得し、その親ディレクトリ（プロジェクトルート）を
# Pythonのモジュール検索パスに追加します。
# これにより、mitmwebから実行されても、同じディレクトリにある 'models.py' を
# 確実に見つけられるようになります。
# ==============================================================================
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# パスを追加した直後に、モジュールをインポートします
try:
    from models import DatabaseManager
    MODELS_AVAILABLE = True
except ImportError:
    ctx.log.error("CRITICAL: proxy_addon.py could not find or import 'models.py'. DB functions disabled.")
    DatabaseManager = None
    MODELS_AVAILABLE = False


class FilterManager:
    """設定ファイルを管理し、URLのブロック判定を行うクラス。"""
    def __init__(self, root_dir):
        self.project_root = root_dir
        self.config_dir = os.path.join(self.project_root, 'config')
        self.domains_path = os.path.join(self.config_dir, "blocked_domains.txt")
        self.last_modified_time = 0
        self.blocked_domains = set()
        self.load_rules(is_initial_load=True)

    def _get_mtime(self):
        try:
            return os.path.getmtime(self.domains_path)
        except (FileNotFoundError, OSError):
            return 0

    def load_rules(self, is_initial_load=False):
        try:
            if not os.path.exists(self.domains_path):
                self.blocked_domains = set()
                return

            with open(self.domains_path, 'r', encoding='utf-8') as f:
                self.blocked_domains = {line.strip().lower() for line in f if line.strip() and not line.startswith('#')}
            self.last_modified_time = self._get_mtime()
            log_prefix = "Initial" if is_initial_load else "Reloaded"
            ctx.log.info(f"A.R.G.U.S. Rules: {len(self.blocked_domains)} domains {log_prefix}.")
        except Exception as e:
            ctx.log.error(f"Error loading domain rules: {e}")

    def check_for_rule_updates(self):
        if time.time() - getattr(self, '_last_check', 0) > 2:
            self._last_check = time.time()
            if self._get_mtime() != self.last_modified_time:
                ctx.log.info("Rule file change detected! Reloading...")
                self.load_rules()

    def should_block(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host.lower()
        for domain in self.blocked_domains:
            if host == domain or host.endswith('.' + domain):
                return f"Blocked by domain rule: {domain}"
        return None

class ArgusProxyAddon:
    def __init__(self):
        ctx.log.info("Initializing A.R.G.U.S. Proxy Addon...")
        self.filter_manager = FilterManager(root_dir=project_root)
        
        if MODELS_AVAILABLE:
            db_path = os.path.join(project_root, "argus.db")
            self.db = DatabaseManager(db_path=db_path)
            ctx.log.info(f"Database connection enabled: {db_path}")
        else:
            self.db = None
        
        ctx.log.info("A.R.G.U.S. Proxy Addon is now active.")

    def tick(self):
        self.filter_manager.check_for_rule_updates()

    def request(self, flow: http.HTTPFlow):
        block_reason = self.filter_manager.should_block(flow)
        if block_reason:
            ctx.log.info(f"BLOCKED: {flow.request.url} ({block_reason})")
            # ★★★ 修正ポイント ★★★
            # _create_blocked_responseにプロジェクトルートを渡すように変更
            flow.response = self._create_blocked_response(flow, block_reason, self.filter_manager.project_root)
    
    def response(self, flow: http.HTTPFlow):
        if not self.db: return
        is_blocked = bool(flow.response and "X-Argus-Block-Reason" in flow.response.headers)
        reason = flow.response.headers.get("X-Argus-Block-Reason", "") if is_blocked else ""
        self.db.add_log(flow, is_blocked, reason)

    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★★★ ここが修正されたブロックページ生成関数です ★★★
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    def _create_blocked_response(self, flow: http.HTTPFlow, reason: str, root_dir: str) -> http.Response:
        """
        templates/blocked_page.htmlを読み込んで、ブロック画面を生成します。
        """
        # テンプレートファイルの絶対パスを構築
        template_path = os.path.join(root_dir, 'templates', 'blocked_page.html')
        
        # ファイルが存在しない場合の、最低限のフォールバック用HTML
        html_content = f"<h1>Access Denied by A.R.G.U.S.</h1><p>Reason: {reason}</p>"
        
        try:
            # テンプレートファイルを読み込む
            with open(template_path, 'r', encoding='utf-8') as f:
                # 内容を読み込み、プレースホルダーを実際の値に置き換える
                html_content = f.read().replace("{{ REASON }}", reason).replace("{{ BLOCKED_URL }}", flow.request.pretty_url)
        except FileNotFoundError:
            # ファイルが見つからなかった場合は警告ログを出す
            ctx.log.warn(f"Block page template not found at '{template_path}'. Using fallback HTML.")
        except Exception as e:
            # その他のエラーが発生した場合
            ctx.log.error(f"Error reading block page template: {e}")

        # HTTPレスポンスを作成して返す
        headers = {"Content-Type": "text/html; charset=utf-8", "X-Argus-Block-Reason": reason}
        return http.Response.make(403, html_content.encode('utf-8'), headers)

# mitmproxyにこのアドオンを登録
addons = [ArgusProxyAddon()]