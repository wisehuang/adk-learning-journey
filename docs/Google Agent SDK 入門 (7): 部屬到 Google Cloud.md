# Google Agent SDK 入門 (7): 監控

## 應用程式監控與視覺化

在 Cloud Run 上以 Prometheus 監控 Streamlit 較為複雜，因為 Cloud Run 通常只開放單一主要服務埠口。推薦的方式是直接使用 Google Cloud 原生監控工具。

---

### 收集應用程式指標（使用 Cloud Monitoring）

#### 選項 A：結構化日誌與基於日誌的指標（較簡單）

* 在 Streamlit 應用中利用 Python logging 模組輸出結構化（JSON）日誌。
* Cloud Run 會自動將 `stdout`/`stderr` 輸出轉發到 Cloud Logging，JSON 會被解析成 `jsonPayload`。

範例程式碼：

```python
import logging
import json
from google.cloud.logging.handlers import CloudLoggingHandler
from google.cloud.logging_v2.handlers import setup_logging
import google.cloud.logging

client = google.cloud.logging.Client(project="adk-learning-journey")
handler = CloudLoggingHandler(client, name="streamlit_app")
setup_logging(handler)

def some_function_processing_a_task(task_type, success):
    log_data = {
        "message": f"Processed task of type {task_type}",
        "task_type": task_type,
        "duration_ms": 123,
        "success": success,
        "severity": "INFO" if success else "ERROR"
    }
    print(json.dumps(log_data))
```

* 在 Cloud Monitoring 中建立基於日誌的指標：

  1. 前往 Google Cloud Console → Logging → Log-based Metrics → Create Metric。
  2. 選擇 Counter（計數器）或 Distribution（分佈）指標型態。
  3. 設定過濾條件以符合你的日誌，例如：

     ```
     resource.type="cloud_run_revision"
     resource.labels.service_name="meeting-workflow-agent"
     jsonPayload.task_type="schedule_meeting"
     ```
  4. 設定欄位名稱（如 Distribution 型態使用 `jsonPayload.duration_ms`）、單位（如 ms）、標籤。

#### 選項 B：使用 Cloud Monitoring API（更彈性，程式碼較多）

* 在 requirements.txt 中加入 `google-cloud-monitoring`。
* 在程式中使用 `google.cloud.monitoring_v3` 直接寫入自訂指標。

範例程式碼：

```python
from google.cloud import monitoring_v3
import time
import os

project_id = "adk-learning-journey"
client = monitoring_v3.MetricServiceClient()
project_name = f"projects/{project_id}"

def write_custom_metric(metric_type, value, labels=None):
    series = monitoring_v3.types.TimeSeries()
    series.metric.type = f"custom.googleapis.com/{metric_type}"
    series.resource.type = "cloud_run_revision"
    series.resource.labels["service_name"] = "meeting-workflow-agent"
    series.resource.labels["revision_name"] = os.environ.get("K_REVISION", "unknown")
    series.resource.labels["configuration_name"] = os.environ.get("K_SERVICE", "unknown")
    if labels:
        for k, v in labels.items():
            series.metric.labels[k] = v
    point = monitoring_v3.types.Point()
    point.value.int64_value = int(value)
    now = time.time()
    point.interval.end_time.seconds = int(now)
    point.interval.end_time.nanos = int((now - point.interval.end_time.seconds) * 10**9)
    series.points.append(point)
    client.create_time_series(name=project_name, time_series=[series])

# 使用範例：
# write_custom_metric("streamlit/successful_meetings", 1, {"agent_type": "manager"})
```

---

### 設定 Grafana

* **部署 Grafana：**

  * 選項 1（推薦）：使用 Google Cloud Marketplace 部署到 GKE/GCE（若環境允許）。
  * 選項 2：自行在你的環境安裝 Grafana。

* **連接 Grafana 到 Google Cloud Monitoring：**

  * 登入 Grafana。
  * 前往 Configuration → Data Sources → Add data source。
  * 選擇 "Google Cloud Monitoring"。
  * **驗證方式**：

    * 若在 GCE/GKE 上運行 Grafana，可直接使用附加服務帳號（需 `roles/monitoring.viewer` 權限）。
    * 否則需建立服務帳號、給予 `roles/monitoring.viewer` 權限、下載 JSON 金鑰並上傳到 Grafana。
  * Default Project 設為 `adk-learning-journey`。
  * Save & Test。

---

### 建立 Grafana 儀表板

* Create → Dashboard → Add new panel。
* **查詢：**

  * 選擇 "Google Cloud Monitoring" 資料來源。
  * Service：Cloud Run 或 Custom Metrics。
  * Metric：選擇你的基於日誌指標、Cloud Run 標準指標（如請求數、延遲、實例數量）或自訂指標名稱（如 `custom.googleapis.com/streamlit/request_count`）。
  * 使用查詢編輯器過濾/聚合資料（如依 `service_name`、`revision_name` 或自訂標籤）。
* **視覺化：** 選擇圖表類型。
* **警報：** 在 Grafana 為關鍵指標設置警報規則。

---

### 成本控管與優化

* **監控成本：** 定期檢查 Google Cloud Billing 報告，依服務（Cloud Run、Secret Manager、Logging、Monitoring）過濾費用。
* **設定預算警報：** 在 Billing 裡設預算。
* **優化 Cloud Run 設定：**

  * 根據使用情況（從 Grafana/Monitoring）調整 CPU、記憶體、最小/最大實例數。
  * 流量低時使用 `--min-instances 0` 可降低費用。
* **日誌與監控成本：**

  * 日誌與監控（尤其自訂指標與 API 呼叫）會產生費用。
  * 調整日誌等級，避免記錄過多不必要的資訊。
  * 精確設定基於日誌的指標過濾條件，避免處理過多日誌。
  * 控制自訂指標寫入頻率。
* **Secret Manager 成本：** 依密鑰數量與存取次數計費，僅在應用啟動時讀取密鑰可大幅降低成本。