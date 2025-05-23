## 學習目標

* 熟悉在 Google Cloud Run 上部署容器與自動擴展，並包含安全的金鑰管理。
* 使用 Cloud Monitoring 與 Grafana 實作效能監控與成本控管。

---

## 任務概覽

1. **應用程式容器化**：將 Streamlit Agent 打包為 Docker 映像，透過 Secret Manager 安全管理 `credentials.json`／`token.json`，並部署至 Cloud Run。
2. **效能監控**：設定 Cloud Monitoring 與 Grafana。
3. **環境設定**：安裝 Google Cloud SDK，處理 Docker 映像的驗證設定。

---

## 前置作業：安裝與設定 Google Cloud SDK

* 依照 [官方說明](https://cloud.google.com/sdk/docs/install) 安裝。
* **macOS（使用 Homebrew）：** `brew install --cask google-cloud-sdk`
* 初始化：`gcloud init`（登入、設定或建立專案，例如 `adk-learning-journey`）
* 設定專案：`gcloud config set project adk-learning-journey`
* Docker 認證設定：`gcloud auth configure-docker`
* 啟用所需 API：

  ```bash
  gcloud services enable secretmanager.googleapis.com \
      artifactregistry.googleapis.com \
      run.googleapis.com \
      iam.googleapis.com \
      cloudbuild.googleapis.com \
      logging.googleapis.com \
      monitoring.googleapis.com
  # 如需額外 API（如 Calendar、Gemini），請一併啟用
  # gcloud services enable calendar-json.googleapis.com
  # gcloud services enable generativelanguage.googleapis.com
  ```

---

## 部署步驟（詳細）

### 1. 準備應用程式與安全設定

* **requirements.txt**：確認所有必要套件皆已列入（如 `google-cloud-secret-manager` 等）。
* **敏感檔案**：`credentials.json` 與 `token.json` 不可納入 Git 儲存庫或 Docker 映像。請加入 `.gitignore`。

#### 使用 Secret Manager

A. **上傳 credentials.json**

```bash
gcloud secrets create calendar-credentials \
    --project="adk-learning-journey" \
    --replication-policy="automatic" \
    --description="Google Calendar API 的 OAuth 用戶端憑證"
gcloud secrets versions add calendar-credentials \
    --project="adk-learning-journey" \
    --data-file="path/to/credentials.json"
```

B. **上傳 token.json**

```bash
gcloud secrets create calendar-token \
    --project="adk-learning-journey" \
    --replication-policy="automatic" \
    --description="Google Calendar API 的使用者 OAuth token"
gcloud secrets versions add calendar-token \
    --project="adk-learning-journey" \
    --data-file="path/to/token.json"
```

C. **修改應用程式以從 Secret Manager 讀取檔案**

程式碼應從 Secret Manager 載入 `credentials.json` 與 `token.json`（參見 [範例](https://github.com/wisehuang/adk-learning-journey/blob/main/meeting_workflow/common/google_auth.py)）。

---

### 2. Docker 打包

範例 Dockerfile（重點如下）：

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
ENV PYTHONUNBUFFERED 1
ENV GOOGLE_CLOUD_PROJECT "adk-learning-journey"
ENV PORT 8080
CMD streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
```

> 小提示：部署至 Cloud Run 時可用 `--set-env-vars` 參數覆寫專案 ID，以增加移植性。

---

### 3. 建置並測試 Docker 映像

```bash
docker build -t $IMAGE_URI .
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT="adk-learning-journey" \
  -e PORT="8080" \
  $IMAGE_URI
# 開啟 http://localhost:8080 驗證本地服務
```

---

### 4. 將映像推送至 Artifact Registry（或 GCR）

* 建立儲存庫（若尚未建立）：

  ```bash
  gcloud artifacts repositories create $REPO \
    --project="adk-learning-journey" \
    --repository-format=docker \
    --location=$REGION
  ```

* 推送映像：

  ```bash
  docker push $IMAGE_URI
  ```

---

### 5. 部署至 Cloud Run

A. **建立服務帳戶（SA）：**

```bash
gcloud iam service-accounts create meeting-workflow \
  --project="adk-learning-journey" \
  --description="Meeting Workflow Streamlit Agent 專用服務帳戶" \
  --display-name="Meeting Workflow"
```

B. **授予服務帳戶 Secret Manager 存取權限：**

```bash
gcloud projects add-iam-policy-binding adk-learning-journey \
  --member="serviceAccount:meeting-workflow@adk-learning-journey.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

C. **部署至 Cloud Run：**

```bash
gcloud run deploy meeting-scheduler \
  --image gcr.io/adk-learning-journey/meeting-workflow \
  --platform managed \
  --service-account meeting-workflow@adk-learning-journey.iam.gserviceaccount.com \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=adk-learning-journey"
```

---

### 6. 驗證部署結果

* 部署完成後，開啟 `gcloud` 顯示的 Cloud Run 網址以測試服務。
* 在 Google Cloud Console > Cloud Run > 選擇服務 > 查看日誌，確認環境變數、密鑰存取、應用啟動等是否有錯誤。
