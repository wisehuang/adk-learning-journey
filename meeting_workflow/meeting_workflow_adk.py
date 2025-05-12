#!/usr/bin/env python3
"""
Meeting Workflow ADK Implementation
使用 Google ADK 框架的會議排程多代理系統
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Google ADK 核心導入
from google.adk.tools import BaseTool
from google.adk.agents import Agent, SequentialAgent

# 日曆 API 相關導入
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Google Calendar API 的範圍
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """取得已授權的 Google Calendar 服務"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)

# 定義 ADK 工具 - 驗證參與者工具
class ValidateAttendeesTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="validate_attendees",
            description="驗證參與者郵件格式與權限"
        )
    
    def execute(self, context, attendees: list):
        """驗證參與者電子郵件格式"""
        invalid_emails = []
        for email in attendees:
            if '@' not in email or '.' not in email:
                invalid_emails.append(email)
                
        if invalid_emails:
            return {"valid": False, "invalid_emails": invalid_emails}
        return {"valid": True}

# 定義 ADK 工具 - 排程會議工具
class ScheduleMeetingTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="schedule_meeting",
            description="在 Google 日曆安排會議，處理時間衝突與參與者通知"
        )
    
    def execute(self, context, summary: str, start_time: str, 
               duration_min: int, attendees: list, description: str = None):
        """排程會議並處理時間衝突"""
        try:
            # 初始化日曆服務
            service = get_calendar_service()
            
            # 時間格式轉換
            start = datetime.fromisoformat(start_time)
            end = start + timedelta(minutes=duration_min)
            
            # 建立事件結構
            event = {
                'summary': summary,
                'start': {'dateTime': start.isoformat(), 'timeZone': 'Asia/Taipei'},
                'end': {'dateTime': end.isoformat(), 'timeZone': 'Asia/Taipei'},
                'attendees': [{'email': email} for email in attendees]
            }
            
            if description:
                event['description'] = description
            
            # 檢查衝突
            freebusy = service.freebusy().query(body={
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "items": [{"id": email} for email in attendees]
            }).execute()
            
            # 處理衝突
            conflicts = []
            for attendee, data in freebusy.get('calendars', {}).items():
                if data.get('busy', []):
                    conflicts.append(attendee)
            
            if conflicts:
                alternative_times = self._find_alternative_times(service, start, duration_min, attendees)
                return {
                    "status": "conflict",
                    "message": f"參與者 {', '.join(conflicts)} 時間衝突",
                    "suggestions": alternative_times
                }
            
            # 建立事件
            created_event = service.events().insert(
                calendarId='primary', 
                body=event,
                sendUpdates='all'
            ).execute()
            
            return {
                "status": "success", 
                "event_id": created_event['id'],
                "message": "會議已排程並發送通知"
            }
            
        except HttpError as error:
            logger.error(f"Calendar API error: {error}")
            return {"status": "error", "message": f"API 錯誤: {str(error)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"status": "error", "message": f"未預期錯誤: {str(e)}"}
    
    def _find_alternative_times(self, service, original_start, duration, attendees):
        """智慧尋找替代時間選項"""
        alternatives = []
        current = original_start
        end_range = original_start + timedelta(days=3)
        
        while current < end_range and len(alternatives) < 5:
            # 僅在工作時間內搜尋
            if 9 <= current.hour < 18 and current.weekday() < 5:
                end_time = current + timedelta(minutes=duration)
                try:
                    freebusy = service.freebusy().query(body={
                        "timeMin": current.isoformat(),
                        "timeMax": end_time.isoformat(),
                        "items": [{"id": email} for email in attendees]
                    }).execute()
                    
                    all_available = True
                    for _, data in freebusy.get('calendars', {}).items():
                        if data.get('busy', []):
                            all_available = False
                            break
                    
                    if all_available:
                        alternatives.append(current.isoformat())
                except Exception:
                    pass
            
            current += timedelta(minutes=30)
        
        return alternatives

# 定義 ADK 工具 - 會議通知工具
class SendMeetingNotificationTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="send_meeting_notification",
            description="生成並發送會議通知給所有參與者"
        )
    
    def execute(self, context, event_id: str, summary: str, start_time: str, 
                duration_min: int, attendees: list, description: str = None, 
                is_update: bool = False, is_cancellation: bool = False):
        """生成並發送會議通知"""
        try:
            # 組織時間資訊
            start = datetime.fromisoformat(start_time)
            end = start + timedelta(minutes=duration_min)
            
            # 確定通知類型
            notification_type = "會議邀請"
            if is_update:
                notification_type = "會議更新"
            elif is_cancellation:
                notification_type = "會議取消"
            
            # 生成通知內容
            notification = self._generate_notification(
                notification_type=notification_type,
                summary=summary,
                start=start,
                end=end,
                description=description
            )
            
            # 在實際應用中，這裡會連接到電子郵件服務或其他通知系統
            # 此處僅模擬發送通知
            logger.info(f"發送 {notification_type} 給 {', '.join(attendees)}")
            logger.info(f"通知內容:\n{notification}")
            
            # 如果與 Google Calendar API 整合，可以調用以下代碼
            if not is_cancellation and not is_update:
                # 這部分在 schedule_meeting 工具裡已經完成，此處僅示範
                """
                service = get_calendar_service()
                service.events().insert(
                    calendarId='primary',
                    body=event,
                    sendUpdates='all'
                ).execute()
                """
                pass
            
            return {
                "status": "success",
                "message": f"{notification_type}已發送給所有參與者",
                "recipients": attendees,
                "event_id": event_id
            }
            
        except Exception as e:
            logger.error(f"發送通知錯誤: {e}")
            return {
                "status": "error",
                "message": f"發送通知失敗: {str(e)}"
            }
    
    def _generate_notification(self, notification_type, summary, start, end, description=None):
        """產生格式化的通知內容"""
        template = f"""
        {notification_type}
        ===================
        
        主題: {summary}
        時間: {start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%H:%M')}
        地點: Google Meet (連結將在會議開始前發送)
        
        {description or '無說明'}
        
        請確認您的出席狀態。
        """
        return template

# 定義代理
def create_agents():
    """創建多代理系統"""
    # 驗證代理
    validate_agent = Agent(
        name="attendee_validator",
        model="gemini-pro",
        tools=[ValidateAttendeesTool()],
        instruction="驗證會議參與者郵件格式，確保所有參與者郵件地址符合標準格式"
    )
    
    # 排程代理
    scheduling_agent = Agent(
        name="meeting_scheduler", 
        model="gemini-pro",
        tools=[ScheduleMeetingTool()],
        instruction="處理會議排程與衝突解決，找出最適合的會議時間"
    )
    
    # 通知代理
    notification_agent = Agent(
        name="notification_sender",
        model="gemini-pro",
        tools=[SendMeetingNotificationTool()],
        instruction="生成會議通知內容並發送給參與者，確保所有訊息清晰易懂"
    )
    
    # 使用 SequentialAgent 組裝流程
    meeting_workflow = SequentialAgent(
        name="meeting_workflow",
        sub_agents=[
            validate_agent,
            scheduling_agent,
            notification_agent
        ]
    )
    
    return meeting_workflow

def process_meeting_request(context):
    """處理會議請求"""
    workflow = create_agents()
    
    # Call the agents individually since SequentialAgent doesn't have a run method
    # Step 1: Validate attendees
    attendees = extract_attendees(context["query"])
    validator = workflow.sub_agents[0]
    validation_input = f"驗證這些參與者: {', '.join(attendees)}"
    
    # Use the tool directly instead of going through the agent
    validation_tool = ValidateAttendeesTool()
    validation_result = validation_tool.execute({}, attendees)
    
    if not validation_result.get("valid", False):
        return {
            "status": "error",
            "message": "參與者郵件格式驗證失敗",
            "details": validation_result
        }
    
    # Step 2: Schedule meeting - Extract details and call tool directly
    meeting_details = extract_meeting_details(context["query"])
    scheduler_tool = ScheduleMeetingTool()
    scheduling_result = scheduler_tool.execute(
        {},
        summary=meeting_details.get("summary", "會議"),
        start_time=meeting_details.get("start_time", ""),
        duration_min=meeting_details.get("duration_min", 60),
        attendees=attendees,
        description=meeting_details.get("description", "")
    )
    
    if scheduling_result.get("status") != "success":
        return scheduling_result
    
    # Step 3: Send notifications - Use the notification tool directly
    notifier_tool = SendMeetingNotificationTool()
    notification_result = notifier_tool.execute(
        {},
        event_id=scheduling_result.get("event_id", "unknown"),
        summary=meeting_details.get("summary", "會議"),
        start_time=meeting_details.get("start_time", ""),
        duration_min=meeting_details.get("duration_min", 60),
        attendees=attendees,
        description=meeting_details.get("description", "")
    )
    
    return {
        "status": "success",
        "message": "會議已排程並發送通知",
        "details": {
            "validation": validation_result,
            "scheduling": scheduling_result,
            "notification": notification_result
        }
    }

def extract_meeting_details(query):
    """從查詢中提取會議詳細信息"""
    details = {
        "summary": "",
        "start_time": "",
        "duration_min": 60,
        "description": ""
    }
    
    lines = query.split('\n')
    for line in lines:
        line = line.strip()
        if '主題' in line and ':' in line:
            details["summary"] = line.split(':', 1)[1].strip()
        elif '時間' in line and ':' in line:
            details["start_time"] = line.split(':', 1)[1].strip()
        elif '時長' in line and ':' in line:
            duration_text = line.split(':', 1)[1].strip()
            try:
                details["duration_min"] = int(duration_text.split('分鐘')[0].strip())
            except ValueError:
                pass
        elif '描述' in line and ':' in line:
            details["description"] = line.split(':', 1)[1].strip()
    
    return details

def extract_attendees(query):
    """從查詢中提取參與者郵件地址"""
    lines = query.split('\n')
    for line in lines:
        if '參與者' in line and ':' in line:
            # 提取冒號後的部分，按逗號分割
            attendees_part = line.split(':', 1)[1].strip()
            return [email.strip() for email in attendees_part.split(',')]
    return []

# 主程式範例
if __name__ == "__main__":
    # 解析輸入參數
    import argparse
    parser = argparse.ArgumentParser(description='ADK 會議排程系統')
    parser.add_argument('--summary', type=str, help='會議主題')
    parser.add_argument('--time', type=str, help='開始時間 (ISO 格式)')
    parser.add_argument('--duration', type=int, default=60, help='會議時長 (分鐘)')
    parser.add_argument('--attendees', type=str, help='參與者 (以逗號分隔)')
    parser.add_argument('--description', type=str, help='會議描述')
    args = parser.parse_args()
    
    # 如果沒有提供命令行參數，使用範例參數
    if not all([args.summary, args.time, args.attendees]):
        print("使用範例參數...")
        # 明天下午2點
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
        
        context = {
            "query": f"""安排會議：
            主題：產品開發會議
            時間：{tomorrow.isoformat()}
            時長：60分鐘
            參與者：alice@example.com, bob@example.com
            描述：討論下一季產品開發計劃"""
        }
    else:
        context = {
            "query": f"""安排會議：
            主題：{args.summary}
            時間：{args.time}
            時長：{args.duration}分鐘
            參與者：{args.attendees}
            描述：{args.description or '無'}"""
        }
    
    # 處理會議請求
    result = process_meeting_request(context)
    print(json.dumps(result, indent=2, ensure_ascii=False)) 