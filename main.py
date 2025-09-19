import os
import time
from dotenv import load_dotenv
from Function.GmailMonitor import GmailMonitor
from Function.LineApi import  LineApi

def main():
    # 環境変数を読み込み
    load_dotenv()
    
    # 設定取得
    target_email = os.getenv("TARGET_EMAIL")
    
    # 必須設定の確認
    if not target_email:
        print("❌ TARGET_EMAIL環境変数が設定されていません")
        print("📝 .envファイルに TARGET_EMAIL=your_email@gmail.com を追加してください")
        return
    
    try:
        # クラスのインスタンス作成
        monitor = GmailMonitor()
        lineApi = LineApi()

        
        print(f"📱 {target_email} からのメール監視開始...")
        print("⏹️  停止するには Ctrl+C を押してください")
        print("📧 新着メールはリッチなFlex Messageで通知されます")
        
        while True:
            try:
                # Flex Message対応の新しいメソッドを使用
                new_emails =  monitor.check_new_emails_with_flex(
                        sender_email=target_email,
                        line_api=lineApi,
                    )
                
                if new_emails > 0:
                    print("🔔 新しいメールが届きました！Flex Message送信完了")

                else:
                    # 現在時刻を表示（動作確認用）
                    current_time = time.strftime("%H:%M:%S")
                    print(f"📭 新着メールなし ({current_time})")
                
                time.sleep(30)  # 30秒ごとにチェック
                
            except Exception as e:
                print(f"❌ メールチェック中にエラー: {e}")
                print("🔄 30秒後に再試行します...")
                time.sleep(30)
                
    except KeyboardInterrupt:
        print("\n⏹️  メール監視を停止しました")
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        print("💡 設定を確認してください")

if __name__ == '__main__':
    main()