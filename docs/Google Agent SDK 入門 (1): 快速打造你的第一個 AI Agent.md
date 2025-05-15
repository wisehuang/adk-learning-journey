# Google Agent SDK 入門 (1)：快速打造你的第一個 AI Agent

### 什麼是 Google Agent SDK

Google Agent SDK（又稱 Agent Development Kit, ADK）是一套由 Google 開發、Opensource、以 Python 為主的 SDK，用來簡化和加速 AI Agent 的開發、測試與部署流程。

開發者能夠使用這套 SDK 打造具備記憶、工具調用、任務協調等能力的現代化 AI Agent，ADK 深度整合 Google Gemini、Vertex AI 及各種 Google Cloud services



### 安裝環境與設定 Google Cloud

- 前往 [Google Cloud Console](https://console.cloud.google.com/)，登入或註冊帳戶。

- 建立新專案，並確保已啟用「計費」。

- 在 API 管理中啟用「Vertex AI API」。

- 安裝 Google Cloud CLI（gcloud），[官方下載頁](https://cloud.google.com/sdk/docs/install)。

- 更新 CLI 組件：

   ```bash
   gcloud components update
   ```

- 本機終端機登入 Google 帳號並生成預設憑證（ADC）：

   ```bash
   gcloud auth application-default login 
   ```

   開啟瀏覽器，登入 Google 帳號後完成認證

### 建立 Python 虛擬環境並安裝 ADK

- 在你的專案資料夾下建立虛擬環境：

   ```bash
   python -m venv .venv 
   ```

- 啟動虛擬環境（每次新開終端機都需執行）：

   - macOS/Linux:

      ```bash
      source .venv/bin/activate 
      ```

   - Windows CMD:

      ```bash
      .venv\Scripts\activate.bat 
      ```

   - Windows PowerShell:

      ```bash
      .venv\Scripts\Activate.ps1
      ```

- 安裝 Google Agent SDK（ADK）：

   ```
   pip install google-adk 
   ```

   （如需 Vertex AI 進階功能，可用 `pip install --upgrade --quiet google-cloud-aiplatform[agent_engines,adk]`）

### 建立 project 與設定檔

- 建立 project 與必要檔案：

   ```
   mkdir multi_tool_agent
   cd multi_tool_agent
   touch __init__.py agent.py .env
   ```

   project 結構範例：

   ```
   parent_folder/
     multi_tool_agent/
       __init__.py
       agent.py
       .env
   ```

- 編輯 `.env` 檔案，填入你的 Google Cloud 專案資訊（範例）：

   ```
   GOOGLE_CLOUD_PROJECT="your-project-id"
   GOOGLE_CLOUD_LOCATION="us-central1"
   GOOGLE_GENAI_USE_VERTEXAI="True"
   ```

   或若用 API Key（Google AI Studio）：

   ```
   GOOGLE_GENAI_USE_VERTEXAI=FALSE
   GOOGLE_API_KEY=你的API金鑰
   ```

### 寫你的第一個 Agent

- 在 `agent.py`中撰寫簡單範例（可參考官方 Quickstart）：

   ```python
   from google.adk.agents import Agent
   
   root_agent = Agent(
       name="hello_agent",
       model="gemini-2.5-pro-preview-05-06",
       instruction="你是一個友善的助理，回答用戶問題。"
   )
   ```

- 在 `__init__.py` 加入：

   ```python
   from . import agent 
   ```

   

### 啟動 Agent 開發介面或本地測試

- 回到 parent_folder，啟動開發 UI：

```bash
adk web
```

```bash
parent_folder/  <-- Run 'adk web' here
└── your_agent_folder/
    ├── __init__.py
    └── agent.py
```

用瀏覽器開啟顯示的網址（通常是 http://localhost:8000），即可與 Agent 互動。

- 或直接在終端機測試：

   ```
   adk run multi_tool_agent 
   ```

## 7\. 進階：快速體驗官方範例

- clone 官方範例專案：

   ```
   git clone https://github.com/google/adk-samples.git cd adk-samples/agents 
   ```

- 依各子資料夾 README 操作，快速體驗多種現成 Agent。

## 常見問題與補充

1. 我遇到的問題是找不到可以用的 region 和 model

   - region 使用 `us-central1`

      - 可用的 region list: <https://cloud.google.com/compute/docs/regions-zones?hl=zh-tw>

   - model 使用 `gemini-2.5-pro-preview-05-06`

      - 可用的 model list: <https://cloud.google.com/vertex-ai/generative-ai/docs/models>