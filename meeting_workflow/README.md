# Google ADK 會議排程多代理系統

使用 Google Agent Development Kit (ADK) 實現的多代理會議排程系統，通過 Google Calendar API 自動處理會議排程、衝突解決和參與者通知。

## 系統架構

本專案採用 Google ADK 多代理架構，將會議排程拆分為多個專責代理協作完成：

- **驗證代理 (Validator Agent)**: 負責驗證參與者電子郵件格式
- **排程代理 (Scheduler Agent)**: 處理 Google Calendar 整合與衝突解決
- **通知代理 (Notifier Agent)**: 生成並發送會議通知給參與者

各代理透過 ADK 的 SequentialAgent 進行協作，形成完整的處理流程。

## 功能特點

- 📅 Google Calendar API 整合
- 🔍 智能衝突偵測與解決
- 🔄 自動尋找替代時間選項
- ✉️ 自動通知所有會議參與者
- 🤖 基於 Gemini 的多代理協作

## 安裝與配置

### 環境需求

- Python 3.8+
- [Google Cloud 專案](https://console.cloud.google.com/)，啟用 Calendar API
- Google ADK 授權

### 安裝步驟

1. 克隆此倉庫：
```bash
git clone <repository-url>
cd meeting_workflow
```

2. 安裝相依套件：
```bash
pip install -r requirements.txt
```

3. Google Cloud 設定：
   - 創建專案並啟用 Calendar API
   - 設定 OAuth 同意畫面
   - 創建 OAuth 客戶端憑證 (桌面應用)
   - 下載 `credentials.json` 到專案根目錄

## 使用方式

### 命令行使用

```bash
python meeting_workflow_adk.py --summary "產品會議" --time "2023-08-01T14:00:00" --duration 60 --attendees "alice@example.com,bob@example.com" --description "產品開發會議"
```

或直接執行進行範例演示：

```bash
python meeting_workflow_adk.py
```

### 網頁界面

啟動 Streamlit 網頁界面：

```bash
streamlit run streamlit_app.py
```

然後在瀏覽器中開啟顯示的 URL (通常為 http://localhost:8501)

## 專案結構

```
meeting_workflow/
├── meeting_workflow_adk.py  # 主要 ADK 實現
├── streamlit_app.py         # 網頁界面
├── common/                  # 共用工具
│   └── google_auth.py       # Google 認證功能
├── requirements.txt         # 相依套件
└── README.md                # 專案說明
```

## ADK 代理設計

本專案使用 Google ADK 的多代理協作功能，設計如下：

```python
# 驗證代理
validate_agent = Agent(
    name="attendee_validator",
    model="gemini-pro",
    tools=[ValidateAttendeesTool()],
    instruction="驗證會議參與者郵件格式"
)

# 排程代理
scheduling_agent = Agent(
    name="meeting_scheduler", 
    model="gemini-pro",
    tools=[ScheduleMeetingTool()],
    instruction="處理會議排程與衝突解決"
)

# 通知代理
notification_agent = Agent(
    name="notification_sender",
    model="gemini-pro",
    instruction="生成會議通知內容並發送"
)

# 主要工作流
meeting_workflow = SequentialAgent(
    name="meeting_workflow",
    sub_agents=[validate_agent, scheduling_agent, notification_agent],
    instruction="完整會議排程流程"
)
```

## 錯誤處理

系統設計了全面的錯誤處理機制，包括：

- 郵件格式驗證錯誤
- Google Calendar API 錯誤
- 會議時間衝突
- 網絡連接問題

## 擴展功能

專案可進一步擴展：

- 跨時區支援
- 會議室預約整合
- 更多日曆同步選項
- 自然語言輸入 (如："下週一下午排一個小時的產品會議")

## 授權

MIT License 