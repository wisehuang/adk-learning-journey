# Google Agent SDK 入門 (6): 部屬到 Google Cloud

## 學習目標

* 掌握 Google Cloud Run 的容器化部署與自動擴展策略，並進行安全密鑰管理。
* 實現基於 Cloud Monitoring + Grafana 的效能監控及成本控管。

---

## 任務概覽

1. **應用程式容器化**：將 Streamlit Agent 打包為 Docker，安全管理 credentials.json/token.json（用 Secret Manager），並部署至 Cloud Run。
2. **效能監控**：設定 Cloud Monitoring 及 Grafana。
3. **環境配置**：安裝 Google Cloud SDK，處理 Docker 映像檔認證。

---

## 前置準備：Google Cloud SDK 安裝與設定

* 依[官方文件](https://cloud.google.com/sdk/docs/install)安裝。
* **macOS (Homebrew)**：`brew install --cask google-cloud-sdk`
* 初始化：`gcloud init`（登入帳號、設定/建立專案，例如 `adk-learning-journey`）
* 設定專案：`gcloud config set project adk-learning-journey`
* Docker 認證：`gcloud auth configure-docker`
* 啟用 API：

  ```bash
  gcloud services enable secretmanager.googleapis.com \
      artifactregistry.googleapis.com \
      run.googleapis.com \
      iam.googleapis.com \
      cloudbuild.googleapis.com \
      logging.googleapis.com \
      monitoring.googleapis.com
  # 若需其他 API (如 Calendar, Gemini)，請加啟用
  # gcloud services enable calendar-json.googleapis.com
  # gcloud services enable generativelanguage.googleapis.com
  ```

---

## 部署步驟詳解

### 1. 準備應用程式與安全性配置

* **requirements.txt** 檢查必要套件（如 `google-cloud-secret-manager` 等）。
* **敏感檔案處理**：credentials.json、token.json 不可進 Git 或 Docker image，必須納入 `.gitignore`。

#### Secret Manager 操作

A. **上傳 credentials.json**

```bash
gcloud secrets create calendar-credentials \
    --project="adk-learning-journey" \
    --replication-policy="automatic" \
    --description="OAuth client credentials for Google Calendar API"
gcloud secrets versions add calendar-credentials \
    --project="adk-learning-journey" \
    --data-file="path/to/credentials.json"
```

B. **上傳 token.json**

```bash
gcloud secrets create calendar-token \
    --project="adk-learning-journey" \
    --replication-policy="automatic" \
    --description="User OAuth token for Google Calendar API"
gcloud secrets versions add calendar-token \
    --project="adk-learning-journey" \
    --data-file="path/to/token.json"
```

C. **應用程式修改**
程式需從 Secret Manager 讀取 credentials/token（參考 [範例](https://github.com/wisehuang/adk-learning-journey/blob/main/meeting_workflow/common/google_auth.py) ）。

---

### 2. Docker 打包

Dockerfile 範例（精簡重點）：

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

> 建議：Cloud Run 可用 `--set-env-vars` 覆寫專案 ID，提升移植性。

---

### 3. 建置 & 測試 Docker Image

```bash
docker build -t $IMAGE_URI .
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT="adk-learning-journey" \
  -e PORT="8080" \
  $IMAGE_URI
# 確認本機可用 http://localhost:8080
```

---

### 4. 推送 Image 至 Artifact Registry (或 GCR)

* 建立倉庫（若尚未建立）：

  ```bash
  gcloud artifacts repositories create $REPO \
    --project="adk-learning-journey" \
    --repository-format=docker \
    --location=$REGION
  ```

* 推送：

  ```bash
  docker push $IMAGE_URI
  ```

---

### 5. 部署至 Cloud Run

A. **建立 Service Account（SA）**：

```bash
gcloud iam service-accounts create meeting-workflow \
  --project="adk-learning-journey" \
  --description="Service account for Meeting Workflow Streamlit Agent" \
  --display-name="Meeting Workflow"
```

B. **授權 SA 存取 Secret Manager**：

```bash
gcloud projects add-iam-policy-binding adk-learning-journey \
  --member="serviceAccount:meeting-workflow@adk-learning-journey.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

C. **部署至 Cloud Run**：

```bash
gcloud run deploy meeting-scheduler \
  --image gcr.io/adk-learning-journey/meeting-workflow \
  --platform managed \
  --service-account meeting-workflow@adk-learning-journey.iam.gserviceaccount.com \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=adk-learning-journey"
```

---

### 6. 驗證部署

* 部署完成後，於瀏覽器開啟 gcloud 輸出的 Cloud Run URL 測試服務。
* Google Cloud Console > Cloud Run > 選取服務 > Logs，確認是否有錯誤（環境變數、Secret 存取、應用啟動等）。

---

## 其他建議

* 監控與視覺化：設定 Cloud Monitoring + Grafana，收集並呈現指標。
* **遇認證/權限問題**：重跑 `gcloud auth configure-docker`，確認帳號具備 Artifact Registry 權限。