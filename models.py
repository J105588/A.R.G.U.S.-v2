# models.py (Final Confirmed Version)

import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLAlchemyの基本的なおまじない (新しいバージョンに対応)
Base = declarative_base()

class LogEntry(Base):
    """
    データベースの 'log_entries' テーブルの構造を定義するクラス。
    SQLAlchemyは、このクラス定義を元にテーブルを作成します。
    """
    __tablename__ = 'log_entries'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    method = Column(String(10))
    url = Column(Text)
    host = Column(String(255))
    status_code = Column(Integer, nullable=True)
    content_type = Column(String(255), nullable=True)
    is_blocked = Column(Boolean, default=False)
    block_reason = Column(String(255), nullable=True)

    def to_dict(self):
        """
        オブジェクトを辞書（JSONにしやすい形式）に変換します。
        FlaskがWebブラウザに応答を返す際に使われます。
        """
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z', # タイムゾーン情報(UTC)を付与
            'method': self.method,
            'url': self.url,
            'host': self.host,
            'status_code': self.status_code,
            'content_type': self.content_type,
            'is_blocked': self.is_blocked,
            'block_reason': self.block_reason
        }

class DatabaseManager:
    """
    データベースの接続、セッション管理、操作（追加、取得、削除）をまとめて行うクラス。
    proxy_addon.py と main.py の両方から利用されます。
    """
    def __init__(self, db_path='argus.db'):
        """
        データベースマネージャーを初期化します。
        - db_path: データベースファイルのパス。
        """
        # SQLiteデータベースに接続。ファイルがなければ自動的に作成されます。
        # 'check_same_thread=False' は、FlaskとMitmproxyという異なる
        # コンポーネントから利用されるSQLiteのための重要なおまじないです。
        self.engine = create_engine(f'sqlite:///{db_path}', connect_args={"check_same_thread": False})
        
        # LogEntryで定義したテーブルをデータベースに作成します（もし存在しなければ）。
        Base.metadata.create_all(self.engine)
        
        # データベースとの対話（セッション）の準備
        self.Session = sessionmaker(bind=self.engine)

    def add_log(self, flow, is_blocked, reason=""):
        """mitmproxyのHTTPフローオブジェクトから新しいログをデータベースに追加します。"""
        session = self.Session()
        try:
            # mitmproxyのフローオブジェクトから必要な情報を抽出
            log_data = {
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "host": flow.request.pretty_host,
                "is_blocked": is_blocked,
                "block_reason": reason
            }
            
            # レスポンスが存在する場合のみ、ステータスコードとContent-Typeを取得
            if flow.response:
                log_data["status_code"] = flow.response.status_code
                log_data["content_type"] = flow.response.headers.get('Content-Type', '')
            else:
                log_data["status_code"] = None
                log_data["content_type"] = ''

            new_log = LogEntry(**log_data)
            session.add(new_log)
            session.commit()
        except Exception as e:
            # エラーが発生した場合、コンソールに詳細を出力
            print(f"Database Error on add_log: {e}")
            session.rollback() # 変更を元に戻す
        finally:
            session.close() # セッションを必ず閉じる

    def get_logs(self, limit=250):
        """最新のログを指定された件数だけ取得します。"""
        session = self.Session()
        try:
            # timestampの降順（新しいものが先頭）でソートして取得
            logs = session.query(LogEntry).order_by(LogEntry.timestamp.desc()).limit(limit).all()
            return [log.to_dict() for log in logs]
        except Exception as e:
            print(f"Database Error on get_logs: {e}")
            return [] # エラーの場合は空のリストを返す
        finally:
            session.close()

    def clear_logs(self):
        """'log_entries' テーブルの全てのデータを削除します。"""
        session = self.Session()
        try:
            session.query(LogEntry).delete()
            session.commit()
        except Exception as e:
            print(f"Database Error on clear_logs: {e}")
            session.rollback()
        finally:
            session.close()