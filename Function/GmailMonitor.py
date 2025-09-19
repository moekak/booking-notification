import os
import time
from dotenv import load_dotenv
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import re
from email.utils import parsedate_to_datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# メールの閲覧はできるが、削除や送信はできない
# 現在のスコープを以下に変更
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


class GmailMonitor:
    def __init__(self):
        load_dotenv()
        self.credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE")
        self.service = self._authenticate(self.credentials_file)
        self.last_check = datetime.now()  # 最後にメールをチェックした時刻を記録

    def _authenticate(self, credentials_file):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                creds = flow.run_local_server(port=54561)
            
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        return build('gmail', 'v1', credentials=creds)
    
    # 特定の送信者からの新しいメールをチェック
    def check_new_emails(self, sender_email):
        try:
            # 最後のチェック時刻以降のメールを検索
            query = f'from:{sender_email} after:{int(self.last_check.timestamp())}'
            
            result = self.service.users().messages().list(
                userId='me', 
                q=query
            ).execute()
            
            messages = result.get('messages', [])
            
            if messages:
                print(f"新しいメールを {len(messages)} 件受信しました")
            for message in messages:
                self._process_message(message['id'])
            
            self.last_check = datetime.now()
            return len(messages)
            
        except Exception as error:
            print(f'エラー: {error}')
            return 0

    # メールの詳細を取得して処理
    def _process_message(self, message_id):
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id
            ).execute()
            
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            
            print(f"件名: {subject}")
            print(f"送信者: {sender}")
            print("-" * 50)
            
        except Exception as error:
            print(f'メッセージ処理エラー: {error}')

    def _get_header_value(self, headers, name):
        """ヘッダーから特定の値を取得"""
        return next((h['value'] for h in headers if h['name'] == name), None)

    def _parse_sender(self, sender_full):
        """送信者文字列から名前とメールアドレスを分離"""
        # "Name <email@domain.com>" の形式をパース
        match = re.match(r'^(.*?)\s*<(.+)>$', sender_full)
        if match:
            name = match.group(1).strip().strip('"')
            email = match.group(2).strip()
            return name or email.split('@')[0], email
        else:
            # メールアドレスのみの場合
            return sender_full.split('@')[0], sender_full

    def _parse_date(self, date_str):
        """日付文字列をdatetimeオブジェクトに変換"""
        if not date_str:
            return None
        
        try:
            return parsedate_to_datetime(date_str)
        except:
            return None

    def check_new_emails_with_flex(self, sender_email, line_api):
        """新着メールをチェックしてFlex Messageで通知"""
        try:
            query = f'from:{sender_email} after:{int(self.last_check.timestamp())}'
            
            result = self.service.users().messages().list(
                userId='me', 
                q=query
            ).execute()
            
            messages = result.get('messages', [])
            
            if messages:
                print(f"新しいメールを {len(messages)} 件受信しました")
            for message in messages:
                self._process_message_with_details(message['id'], line_api)
            
            self.last_check = datetime.now()
            return len(messages)
            
        except Exception as error:
            print(f'Gmail APIエラー: {error}')
            return 0

    def _process_message_with_details(self, message_id, line_api):
        """メールの詳細を取得してHTML構造を完全に表示"""
        try:
            print(f"=== メッセージ {message_id} の処理開始 ===")
            
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload'].get('headers', [])
            subject = self._get_header_value(headers, 'Subject') or 'No Subject'
            sender = self._get_header_value(headers, 'From') or 'Unknown'
            
            print(f"件名: {subject}")
            print(f"送信者: {sender}")
            
            payload = message['payload']
            self._debug_payload_structure(payload, level=0)
            
            all_contents = self._extract_all_contents(payload)
            
            print("=== 取得されたすべてのコンテンツ ===")
            for mime_type, content in all_contents.items():
                print(f"\n--- {mime_type} ---")
                print(f"コンテンツ長: {len(content)} 文字")
            
            # HTMLから情報抽出を試行（優先順位付き）
            extraction_success = False
            
            # 1. HTMLコンテンツを優先
            for mime_type in ['text/html', 'text/plain']:
                if mime_type in all_contents:
                    content = all_contents[mime_type]
                    if content.strip():
                        print(f"\n{mime_type} から抽出試行:")
                        booking_info = self._extract_booking_info_from_content(content, mime_type)
                        if booking_info:
                            print(f"抽出成功: {len(booking_info)} 項目")
                            for key, value in booking_info.items():
                                print(f"  {key}: {value}")
                            
                            line_api.send_booking_flex_message(booking_info)
                            extraction_success = True
                            break
                        else:
                            print("このコンテンツからは抽出失敗")
            
            if not extraction_success:
                print("全てのコンテンツからの抽出に失敗")
            
            print(f"=== メッセージ {message_id} の処理完了 ===")
            
        except Exception as error:
            print(f'メッセージ処理エラー: {error}')
            import traceback
            traceback.print_exc()

    def _debug_payload_structure(self, payload, level=0):
        """ペイロード構造を詳細にデバッグ表示"""
        indent = "  " * level
        mime_type = payload.get('mimeType', 'unknown')
        
        print(f"{indent}MIME Type: {mime_type}")
        print(f"{indent}Has parts: {'parts' in payload}")
        print(f"{indent}Has body: {'body' in payload}")
        
        if 'body' in payload:
            body = payload['body']
            print(f"{indent}Body size: {body.get('size', 0)} bytes")
            print(f"{indent}Body has data: {'data' in body}")
            if 'data' in body:
                print(f"{indent}Data length: {len(body['data'])} characters")
        
        if 'parts' in payload:
            print(f"{indent}Parts count: {len(payload['parts'])}")
            for i, part in enumerate(payload['parts']):
                print(f"{indent}=== Part {i} ===")
                self._debug_payload_structure(part, level + 1)

    def _extract_all_contents(self, payload):
        """すべてのコンテンツを抽出して返す"""
        contents = {}
        
        def extract_from_part(part):
            mime_type = part.get('mimeType', 'unknown')
            part_body = part.get('body', {})
            data = part_body.get('data', '')
            
            if data:
                try:
                    decoded = base64.urlsafe_b64decode(data).decode('utf-8')
                    contents[mime_type] = decoded
                    print(f"抽出成功: {mime_type} ({len(decoded)} 文字)")
                except Exception as e:
                    print(f"デコードエラー ({mime_type}): {e}")
                    # 別のエンコーディングを試す
                    try:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        contents[f"{mime_type}_partial"] = decoded
                        print(f"部分デコード成功: {mime_type} ({len(decoded)} 文字)")
                    except:
                        pass
        
        if 'parts' in payload:
            def process_parts(parts):
                for part in parts:
                    if 'parts' in part:
                        process_parts(part['parts'])
                    else:
                        extract_from_part(part)
            process_parts(payload['parts'])
        else:
            extract_from_part(payload)
        
        return contents

    def _html_to_text(self, html_content):
        """HTMLをプレーンテキストに変換"""
        import re
        
        # スクリプトとスタイルを除去
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # テーブル構造を保持しつつHTMLを変換
        # <td> タグの間にスペースを追加
        text = re.sub(r'</td>\s*<td[^>]*>', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'</tr>\s*<tr[^>]*>', '\n', text, flags=re.IGNORECASE)
        
        # 改行を保持するHTMLタグ
        text = re.sub(r'<br[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<div[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        
        # 全てのHTMLタグを除去
        text = re.sub(r'<[^>]+>', '', text)
        
        # HTMLエンティティをデコード
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
            '&yen;': '¥',
        }
        
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
        
        # 複数の改行と空白を整理
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 各行をトリムし、アスタリスクを除去
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                # アスタリスクを除去
                line = line.replace('*', '')
                lines.append(line)
        
        return '\n'.join(lines)

    def _extract_from_text(self, text_content):
        """テキストから予約情報を抽出（改良版）"""
        booking_info = {}
        
        try:
            print("=== テキスト抽出開始 ===")
            print(f"テキスト内容（最初の500文字）:\n{text_content[:500]}")
            
            # より柔軟なパターン
            patterns = {
                'tour_name': [
                    r'booked:\s*([^\n]*(?:Tokyo|Private|Customizable|Tour)[^\n]*)',
                    r'following offer has been booked:\s*([^\n]+)',
                    r'booked:\s*([^\n]{15,})',
                ],
                'options': [
                    r'Option:\s*([^\n]+)',
                    r'(Option:[^\n]+)',
                ],
                'date': [
                    r'Date:\s*([^\n]+)',
                    r'Date\s+([^\n]+)',
                ],
                'price': [
                    r'Price:\s*([^\n]+)',
                    r'Price\s+([^\n]+)',
                ],
                'reference': [
                    r'Reference number:\s*([^\n]+)',
                    r'Reference number\s+([^\n]+)',
                ],
                'customer_name': [
                    r'Main customer:\s*([^\n]+)',
                    r'Customer:\s*([^\n]+)',
                ],
                'phone': [
                    r'Phone:\s*([^\n]+)',
                    r'Phone\s+([^\n]+)',
                ],
                'language': [
                    r'Language:\s*([^\n]+)',
                    r'Language\s+([^\n]+)',
                ],
                'tour_language': [
                    r'Tour language:\s*([^\n]+)',
                    r'Tour language\s+([^\n]+)',
                ],
                'pickup_location': [
                    r'Pickup location:\s*([^\n]+)',
                    r'Pickup:\s*([^\n]+)',
                    r'Pickup location\s+([^\n]+)',
                ]
            }
            
            for field, field_patterns in patterns.items():
                for pattern in field_patterns:
                    match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
                    if match:
                        value = match.group(1).strip()
                        # アスタリスクを除去
                        value = value.replace('*', '')
                        if value and len(value) > 0:
                            booking_info[field] = value
                            print(f"  {field}: {value}")
                            break
                
                if field not in booking_info:
                    print(f"  {field}: 見つからず")
            
            print(f"抽出された情報: {len(booking_info)} 項目")
            
            return booking_info
            
        except Exception as error:
            print(f"テキスト抽出エラー: {error}")
            return {}

    def _extract_booking_info_from_content(self, content, mime_type):
        """コンテンツタイプに応じて予約情報を抽出"""
        booking_info = {}
        
        try:
            if 'html' in mime_type.lower():
                print("HTML解析モード - HTMLをテキストに変換")
                
                # HTMLをテキストに変換
                text_content = self._html_to_text(content)
                print(f"HTML→テキスト変換後の長さ: {len(text_content)} 文字")
                
                # 変換されたテキストから抽出
                booking_info = self._extract_from_text(text_content)
                
            else:
                print("プレーンテキスト解析モード")
                booking_info = self._extract_from_text(content)
            
            return booking_info
            
        except Exception as error:
            print(f"コンテンツ抽出エラー: {error}")
            import traceback
            traceback.print_exc()
            return {}