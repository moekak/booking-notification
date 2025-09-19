from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
from dotenv import load_dotenv
import os
from datetime import datetime
from linebot.models import (
    FlexSendMessage, BubbleContainer, ImageComponent, BoxComponent,
    TextComponent, IconComponent, ButtonComponent, URIAction, MessageAction,
    SeparatorComponent
)

class LineApi:
    def __init__(self):
        """LINE API クラスの初期化"""
        self.line_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        self.target_user_id = os.getenv('LINE_TARGET_USER_ID')
        
        if not self.line_token or not self.target_user_id:
            print("LINE設定が不完全です")
            self.line_bot_api = None
        else:
            self.line_bot_api = LineBotApi(self.line_token)
            print("LINE API初期化成功")

    def send_booking_flex_message(self, booking_info):
        """Send booking information as Flex Message (Receipt style)"""
        if not self.line_bot_api:
            print("LINE API not initialized")
            return False

        try:
            # 動的にツアー名を取得、フォールバック値を設定
            tour_title = booking_info.get('tour_name', 'Tour Booking')
            tour_option = booking_info.get('options', '')
            
            # 基本的な項目リスト
            detail_items = []
            
            # Date
            detail_items.append(
                BoxComponent(
                    layout="horizontal",
                    contents=[
                        TextComponent(
                            text="Date",
                            size="sm",
                            color="#555555",
                            flex=0
                        ),
                        TextComponent(
                            text=booking_info.get('date', 'Not specified'),
                            size="sm",
                            color="#111111",
                            align="end",
                            wrap=True
                        )
                    ]
                )
            )
            
            # Price
            detail_items.append(
                BoxComponent(
                    layout="horizontal",
                    contents=[
                        TextComponent(
                            text="Price",
                            size="sm",
                            color="#555555",
                            flex=0
                        ),
                        TextComponent(
                            text=booking_info.get('price', 'Not specified'),
                            size="sm",
                            color="#111111",
                            align="end"
                        )
                    ]
                )
            )
            
            # セパレータ
            detail_items.append(SeparatorComponent(margin="xxl"))
            
            # Customer Name
            detail_items.append(
                BoxComponent(
                    layout="horizontal",
                    margin="xxl",
                    contents=[
                        TextComponent(
                            text="Customer",
                            size="sm",
                            color="#555555"
                        ),
                        TextComponent(
                            text=booking_info.get('customer_name', 'Not specified'),
                            size="sm",
                            color="#111111",
                            align="end",
                            wrap=True
                        )
                    ]
                )
            )
            
            # Phone（存在する場合のみ追加）
            if booking_info.get('phone'):
                detail_items.append(
                    BoxComponent(
                        layout="horizontal",
                        contents=[
                            TextComponent(
                                text="Phone",
                                size="sm",
                                color="#555555"
                            ),
                            TextComponent(
                                text=booking_info.get('phone'),
                                size="sm",
                                color="#111111",
                                align="end",
                                wrap=True
                            )
                        ]
                    )
                )
            
            # Language
            detail_items.append(
                BoxComponent(
                    layout="horizontal",
                    contents=[
                        TextComponent(
                            text="Language",
                            size="sm",
                            color="#555555"
                        ),
                        TextComponent(
                            text=booking_info.get('language', 'Not specified'),
                            size="sm",
                            color="#111111",
                            align="end"
                        )
                    ]
                )
            )
            
            # Tour Language
            detail_items.append(
                BoxComponent(
                    layout="horizontal",
                    contents=[
                        TextComponent(
                            text="Tour language",
                            size="sm",
                            color="#555555"
                        ),
                        TextComponent(
                            text=booking_info.get('tour_language', 'Not specified'),
                            size="sm",
                            color="#111111",
                            align="end"
                        )
                    ]
                )
            )
            
            # Pickup Location（存在する場合のみ追加、縦並び）
            if booking_info.get('pickup_location'):
                detail_items.append(
                    BoxComponent(
                        layout="vertical",
                        contents=[
                            TextComponent(
                                text="Pickup",
                                size="sm",
                                color="#555555"
                            ),
                            TextComponent(
                                text=booking_info.get('pickup_location'),
                                size="sm",
                                color="#111111",
                                wrap=True,
                                margin="xs"
                            )
                        ]
                    )
                )
            
            # Create receipt-style Flex Message
            bubble = BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text="NEW BOOKING",
                            weight="bold",
                            color="#1DB446",
                            size="sm"
                        ),
                        TextComponent(
                            text="GetYourGuide",
                            weight="bold",
                            size="xxl",
                            margin="md"
                        ),
                        TextComponent(
                            text=tour_title,  # 動的に取得
                            size="sm",
                            color="#333333",
                            wrap=True,
                            weight="bold",
                            margin="sm"
                        ),
                        # オプション情報がある場合のみ表示
                        *([TextComponent(
                            text=tour_option,
                            size="xs",
                            color="#666666",
                            wrap=True
                        )] if tour_option else []),
                        SeparatorComponent(margin="xxl"),
                        BoxComponent(
                            layout="vertical",
                            margin="xxl",
                            spacing="sm",
                            contents=detail_items
                        ),
                        SeparatorComponent(margin="xxl"),
                        # Reference ID
                        BoxComponent(
                            layout="horizontal",
                            margin="md",
                            contents=[
                                TextComponent(
                                    text="REFERENCE ID",
                                    size="xs",
                                    color="#aaaaaa",
                                    flex=0
                                ),
                                TextComponent(
                                    text=booking_info.get('reference', 'Not specified'),
                                    color="#aaaaaa",
                                    size="xs",
                                    align="end",
                                    wrap=True
                                )
                            ]
                        )
                    ]
                ),
                styles={
                    "footer": {
                        "separator": True
                    }
                }
            )
            
            flex_message = FlexSendMessage(
                alt_text="New Booking Received",
                contents=bubble
            )
            
            self.line_bot_api.push_message(
                self.target_user_id,
                flex_message
            )
            
            print("Booking Flex Message sent successfully")
            return True
            
        except LineBotApiError as e:
            print(f"LINE sending error: {e.message}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False