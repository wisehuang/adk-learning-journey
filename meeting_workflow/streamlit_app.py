#!/usr/bin/env python3
"""
Meeting Workflow ADK - Streamlit Web Interface
會議排程系統的網頁界面
"""

import streamlit as st
import datetime
import json
from meeting_workflow_adk import process_meeting_request

# 設置頁面
st.set_page_config(
    page_title="ADK 會議排程系統",
    page_icon="📅",
    layout="wide"
)

# 頁面標題
st.title("🤖 Google ADK 會議排程系統")
st.markdown("使用多代理協作安排會議、處理衝突並發送通知")

# 側邊欄 - 介紹與說明
with st.sidebar:
    st.header("👋 歡迎使用")
    st.markdown("""
    這個系統使用 Google ADK (Agent Development Kit) 架構構建，
    包含多個專責代理協作處理會議排程流程：
    
    1. **驗證代理** - 確認參與者電子郵件格式
    2. **排程代理** - 處理 Google Calendar 整合與衝突解決
    3. **通知代理** - 生成並發送會議通知
    
    請於右側填寫會議資訊進行排程。
    """)
    
    st.markdown("---")
    st.markdown("Powered by Google ADK and Gemini")

# 主要表單
with st.form("meeting_form"):
    st.subheader("會議資訊")
    
    # 會議主題
    summary = st.text_input("會議主題", "產品開發討論")
    
    # 會議日期與時間
    col1, col2 = st.columns(2)
    with col1:
        meeting_date = st.date_input("會議日期", datetime.datetime.now() + datetime.timedelta(days=1))
    with col2:
        meeting_time = st.time_input("會議時間", datetime.time(14, 0))
    
    # 組合日期與時間
    meeting_datetime = datetime.datetime.combine(meeting_date, meeting_time)
    
    # 會議時長
    duration = st.slider("會議時長 (分鐘)", 15, 180, 60, step=15)
    
    # 參與者
    attendees = st.text_area(
        "參與者電子郵件 (每行一個)",
        "alice@example.com\nbob@example.com"
    )
    
    # 會議描述
    description = st.text_area("會議描述", "討論下一季產品開發計劃與進度追蹤")
    
    # 提交按鈕
    submit_button = st.form_submit_button("排程會議")

# 處理表單提交
if submit_button:
    with st.spinner("正在處理會議排程..."):
        # 準備參與者列表
        attendee_list = [email.strip() for email in attendees.split("\n") if email.strip()]
        
        # 創建查詢內容
        query = f"""安排會議：
        主題：{summary}
        時間：{meeting_datetime.isoformat()}
        時長：{duration}分鐘
        參與者：{', '.join(attendee_list)}
        描述：{description}
        """
        
        # 處理請求
        context = {"query": query}
        try:
            result = process_meeting_request(context)
            
            # 處理結果顯示
            if result.get("status") == "success":
                st.success("✅ 會議排程成功！")
                st.json(result)
                
            elif result.get("status") == "conflict":
                st.warning("⚠️ 發現時間衝突")
                st.write(result.get("message", ""))
                
                # 顯示替代時間選項
                if result.get("suggestions"):
                    st.subheader("可選替代時間")
                    for i, alt_time in enumerate(result.get("suggestions", [])):
                        dt = datetime.datetime.fromisoformat(alt_time)
                        st.write(f"{i+1}. {dt.strftime('%Y-%m-%d %H:%M')} ({dt.strftime('%A')})")
                    
                    st.info("請選擇替代時間並重新提交")
                
            else:
                st.error("❌ 排程失敗")
                st.write(result.get("message", "未知錯誤"))
                
        except Exception as e:
            st.error(f"處理過程中發生錯誤: {str(e)}")

# 展示當前進程
st.markdown("---")
st.subheader("系統進程")
col1, col2, col3 = st.columns(3)
with col1:
    st.info("驗證代理 ➡️ 檢查參與者資料")
with col2:
    st.info("排程代理 ➡️ 與日曆 API 整合")
with col3:
    st.info("通知代理 ➡️ 準備並發送通知") 