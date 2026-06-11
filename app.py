import io
import os
import textwrap

import altair as alt
import groq
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_utils import convert_df_to_excel, extract_item_analysis, extract_latest_dse_total_data, extract_mcq_analysis

# ==========================================
# 頁面設定 / Page Configuration
# ==========================================
st.set_page_config(page_title="HKDSE Statistical Report Data Extraction | HKDSE學校統計報告 數據提取工具", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")
st.title(
    """
HKDSE學校統計報告 數據提取與分析工具 
# HKDSE School Statistical Report Data Extraction and Analysis Tool
"""
)
st.markdown(
    """
本工具將提取考評局 PDF 報告中的數據，並提供題目標記與分析功能。

This tool extracts data from the HKDSE PDF reports and provides question tagging and analysis features.
"""
)
# ==========================================
# 把已處理數據存入 session_state，供其他 app 使用
# ==========================================
def cache_processed_data(uploaded_file):
    if uploaded_file is None:
        uploaded_file = st.session_state.get('last_uploaded_file')
    if uploaded_file is None:
        return False
    file_name = getattr(uploaded_file, 'name', st.session_state.get('source_pdf_name', 'uploaded.pdf'))
    file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, 'getvalue') else bytes(uploaded_file)
    st.session_state['source_pdf_name'] = file_name
    st.session_state['source_pdf_bytes'] = file_bytes
    st.session_state['processed_item_df'] = extract_item_analysis(file_bytes)
    st.session_state['processed_mcq_df'] = extract_mcq_analysis(file_bytes)
    total_df, subject_name, exam_year, attendance_ys, attendance_ds = extract_latest_dse_total_data(file_bytes)
    st.session_state['processed_total_df'] = total_df
    st.session_state['custom_total_overview_df'] = total_df.copy() if isinstance(total_df, pd.DataFrame) else None
    st.session_state['processed_total_attendance_ys'] = attendance_ys
    st.session_state['processed_total_attendance_ds'] = attendance_ds
    st.session_state['processed_subject_name'] = subject_name
    st.session_state['processed_exam_year'] = exam_year
    return True


def build_extraction_status_message():
    item_df = st.session_state.get('processed_item_df')
    mcq_df = st.session_state.get('processed_mcq_df')
    total_df = st.session_state.get('processed_total_df')

    def status(label_cn, label_en, condition):
        if condition:
            return f"✅ {label_cn}提取完成 | {label_en} extraction completed"
        return f"❌ {label_cn}提取失敗 | {label_en} extraction failed"

    return [
        status("總數表格", "Total Table", isinstance(total_df, pd.DataFrame) and not total_df.empty),
        status("項目分析表格", "Item Analysis Table", isinstance(item_df, pd.DataFrame) and not item_df.empty),
        status("多項選擇題表格", "MCQ Analysis Table", isinstance(mcq_df, pd.DataFrame) and not mcq_df.empty),
    ]


def dataframe_to_structured_text(df, label):
    if df is None or df.empty:
        return f"{label}: no data available."

    df = df.copy()
    df = df.fillna("").astype(str)
    lines = [f"{label} overview:", f"Columns: {', '.join(df.columns.astype(str).tolist())}"]
    sample_rows = df.head(10).to_dict(orient="records")
    for index, row in enumerate(sample_rows, start=1):
        row_text = "; ".join(f"{k}={v}" for k, v in row.items())
        lines.append(f"Row {index}: {row_text}")
    if len(df) > len(sample_rows):
        lines.append(f"Only the first {len(sample_rows)} rows are shown out of {len(df)} total rows.")
    return "\n".join(lines)


def generate_groq_report(language, total_df, item_df, mcq_df, custom_prompt):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        raise ValueError("Missing GROQ_API_KEY in st.secrets. Please add it to your Streamlit secrets.")

    if not api_key:
        raise ValueError("GROQ_API_KEY in st.secrets is empty. Please provide a valid key.")

    system_instruction = (
        "你是一位專業的學校數據分析報告撰寫者。請以繁體中文撰寫，保持清晰、結構化且避免虛構數字。"
        if language == "zh"
        else "You are a professional school data analyst and report writer. Please write clearly, in a structured school-report style, and avoid inventing numbers."
    )

    total_text = dataframe_to_structured_text(total_df, "Total Overview") if total_df is not None else "Total overview table is unavailable."
    item_text = dataframe_to_structured_text(item_df, "Item Overview") if item_df is not None else "Item overview table is unavailable."
    mcq_text = dataframe_to_structured_text(mcq_df, "MCQ Overview") if mcq_df is not None else "MCQ overview table is unavailable."

    available_parts = [part for part, df in [("total", total_df), ("item", item_df), ("mcq", mcq_df)] if df is not None and hasattr(df, 'empty') and not df.empty]
    if len(available_parts) == 3:
        analysis_directive = (
            "Please write one integrated report synthesizing findings from the total, item, and MCQ tables. "
            "Discuss overlapping data patterns and separate out any distinct findings from each table."
        )
    else:
        missing = [name for name, df in [("Total", total_df), ("Item", item_df), ("MCQ", mcq_df)] if df is None or (hasattr(df, 'empty') and df.empty)]
        analysis_directive = (
            f"Generate the report using only the available tables and explicitly state that the following tables are unavailable or missing: {', '.join(missing)}. "
            "Do not hallucinate any missing numbers."
        )

    user_message = (
        f"{custom_prompt.strip()}\n\n"
        f"Language: {'Traditional Chinese' if language == 'zh' else 'English'}.\n\n"
        f"{analysis_directive}\n\n"
        f"Data available:\n"
        f"{total_text}\n\n"
        f"{item_text}\n\n"
        f"{mcq_text}\n\n"
        "If the data is insufficient, state that clearly and avoid making up values."
    )

    client = groq.Client(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message},
        ],
        max_tokens=800,
        temperature=0.3,
    )

    if not getattr(response, "choices", None):
        raise ValueError("Groq returned an empty response.")

    first_choice = response.choices[0]
    report_text = getattr(getattr(first_choice, "message", None), "content", None)
    if report_text is None:
        raise ValueError("Groq did not return any report text.")
    return report_text


def build_report_pdf(report_text):
    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    pdf_canvas.setFont("Helvetica", 11)
    y = height - 40
    for paragraph in report_text.splitlines():
        wrapped_lines = textwrap.wrap(paragraph, width=90)
        if not wrapped_lines:
            wrapped_lines = [""]
        for line in wrapped_lines:
            if y < 40:
                pdf_canvas.showPage()
                pdf_canvas.setFont("Helvetica", 11)
                y = height - 40
            pdf_canvas.drawString(40, y, line)
            y -= 14
    pdf_canvas.save()
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


# ==========================================
# 頂部：共用上傳區 / Top: Global Upload
# ==========================================
st.markdown("---")
st.subheader("📂 上載檔案 | Upload File")
global_file = st.file_uploader("請上載包含學校成績數據的考評局 PDF 報告 | Please upload the HKDSE PDF Report", type=["pdf"], key="global_file")
if global_file is not None:
    st.session_state['last_uploaded_file'] = global_file
    st.session_state['source_pdf_name'] = global_file.name
    st.session_state['source_pdf_bytes'] = global_file.getvalue()
    current_file = global_file
else:
    current_file = st.session_state.get('last_uploaded_file')

if current_file is not None:
    current_bytes = current_file.getvalue() if hasattr(current_file, 'getvalue') else bytes(current_file)
    previous_bytes = st.session_state.get('processed_source_pdf_bytes')
    if previous_bytes != current_bytes:
        with st.spinner("正在獲取資料... | Fetching data..."):
            cache_processed_data(current_file)
            st.session_state['processed_source_pdf_bytes'] = current_bytes
        status_lines = build_extraction_status_message()
        for line in status_lines:
            st.success(line)

# 建立主畫面四個標籤頁 (Tabs) 入口
# ==========================================
tab0, tab1, tab2, tab3 = st.tabs([
    "📊 總數表格 Total Table",
    "📝 項目分析表格 Item Analysis Table",
    "✅ 多項選擇題表格 MCQ Analysis Table",
    "🧠 LLM報告 Report Generator",
])

# -----------------
# 標籤頁 0 的內容 / Tab 0 Content
# -----------------
with tab0:
    st.subheader("📊 總數數據提取 Total Data Extraction")
    col_t1, col_t2 = st.columns([2, 5])
    with col_t1:
        st.info("""
        💡 **本區功能：** 自動提取最新年份的「總數」數據。
                
        **Function:** Automatically extracts the latest year's 'Total' data.
        """)
        if os.path.exists("example3_main.png"):
            st.image("example3_main.png", caption="總數表格示例 | Example of Total Table")
        else:
            st.warning("⚠️ (提示: 系統未找到 example3_main.png | Image not found)")
    with col_t2:
        if current_file is None:
            st.warning("👆 請先在上方上載 PDF 檔案 | Please upload the PDF report in above session.")
        else:
            with st.spinner("正在獲取資料... | Fetching data..."):
                try:
                    current_file.seek(0)
                    file_bytes = current_file.getvalue()
                    df_total, subject_name, exam_year, attendance_ys, attendance_ds = extract_latest_dse_total_data(file_bytes)
                    if df_total.empty:
                        st.error("❌ 無法提取數據！請確認你上載的 PDF 包含「總數」表格。\n *Failed to extract data! Please ensure the uploaded PDF contains the 'Total' table.*")
                    else:
                        st.success(f"✅ 提取成功！已取得 {exam_year} 年數據。 \n *Extraction successful! Data for the year {exam_year} retrieved.*")
                        st.subheader(f"📋 {subject_name} {exam_year} 數據概覽 | Data Preview")
                        st.table(df_total.style.format(precision=2))

                        if attendance_ys is not None and attendance_ds is not None:
                            # 分離 UNCL 與其他等級
                            df_without_uncl = df_total[df_total["等級"] != "UNCL"].reset_index(drop=True)
                            df_uncl = df_total[df_total["等級"] == "UNCL"].reset_index(drop=True)
                            
                            # 處理非 UNCL 等級（使用累計差值）
                            chart_df = df_without_uncl.melt(
                                id_vars=["等級"],
                                value_vars=["貴校", "日校"],
                                var_name="學校類別",
                                value_name="人數"
                            )
                            chart_df["出席"] = chart_df["學校類別"].map({
                                "貴校": attendance_ys,
                                "日校": attendance_ds
                            })
                            chart_df = chart_df.sort_values(["學校類別", "等級"])
                            chart_df["累計差值"] = chart_df.groupby("學校類別")["人數"].diff().fillna(chart_df["人數"])
                            chart_df["累計差值"] = chart_df["累計差值"].clip(lower=0)
                            chart_df["百分比"] = (chart_df["累計差值"] / chart_df["出席"]) * 100
                            chart_df["百分比標籤"] = chart_df["百分比"].apply(lambda x: f"{x:.1f}%")
                            
                            # 處理 UNCL（直接用原始數字計算百分比，不參與減法）
                            if not df_uncl.empty:
                                uncl_row = df_uncl.iloc[0]
                                uncl_ys_count = int(uncl_row["貴校"])
                                uncl_ds_count = int(uncl_row["日校"])
                                uncl_ys_pct = (uncl_ys_count / attendance_ys) * 100
                                uncl_ds_pct = (uncl_ds_count / attendance_ds) * 100
                                
                                uncl_chart_data = pd.DataFrame({
                                    "等級": ["UNCL", "UNCL"],
                                    "學校類別": ["貴校", "日校"],
                                    "人數": [uncl_ys_count, uncl_ds_count],
                                    "出席": [attendance_ys, attendance_ds],
                                    "累計差值": [uncl_ys_count, uncl_ds_count],
                                    "百分比": [uncl_ys_pct, uncl_ds_pct],
                                    "百分比標籤": [f"{uncl_ys_pct:.1f}%", f"{uncl_ds_pct:.1f}%"]
                                })
                                chart_df = pd.concat([chart_df, uncl_chart_data], ignore_index=True)

                            # 根據等級數量與字元長度自動決定 X 軸標籤的旋轉角度：預設水平，只有在不夠位置時才直立
                            grades = list(df_total["等級"])
                            num_grades = len(grades)
                            max_label_len = max(len(str(g)) for g in grades) if num_grades > 0 else 0
                            avg_char_px = 8  # 保守估計每個字元佔用像素
                            # 可用空間大約保守設為 700px（在窄屏幕會更小），若需要可調整
                            available_px = 700
                            required_px = num_grades * max_label_len * avg_char_px
                            label_angle = -90 if required_px > available_px or num_grades > 12 else 0

                            bar = alt.Chart(chart_df).mark_bar().encode(
                                x=alt.X("等級:N", title="等級 | Level", sort=list(df_total["等級"]), axis=alt.Axis(labelFontSize=14, titleFontSize=14, labelAngle=label_angle, labelAlign='center', labelOverlap='parity')),
                                xOffset="學校類別:N",
                                y=alt.Y("百分比:Q", title="佔出席百分比 | Percentage of attendance (%)", axis=alt.Axis(labelFontSize=14, titleFontSize=14)),
                                color=alt.Color(
                                    "學校類別:N",
                                    scale=alt.Scale(domain=["貴校", "日校"], range=["#7BA8E0", "#FF9999"]),
                                    title=" "
                                ),
                                tooltip=["等級", "學校類別", "累計差值", alt.Tooltip("百分比:Q", format=".1f")]
                            )

                            labels = alt.Chart(chart_df).mark_text(dy=-8, color="black", fontSize=16).encode(
                                x=alt.X("等級:N", sort=list(df_total["等級"]), axis=alt.Axis(labelAngle=label_angle)),
                                xOffset="學校類別:N",
                                y=alt.Y("百分比:Q"),
                                text=alt.Text("百分比標籤:N")
                            )

                            chart = (bar + labels).properties(height=420)
                            st.subheader("""
                            📈 貴校與日校比較 - 柱形圖
                            ### Comparison of Your school and Day schools - Bar chart
                            """)
                            st.altair_chart(chart, use_container_width=True)
                            
                            st.subheader("📊 數據表 | Data Table")
                            pivot_df = pd.DataFrame()
                            
                            # 處理非 UNCL 等級
                            for grade in df_without_uncl["等級"]:
                                grade_data = chart_df[chart_df["等級"] == grade]
                                ys_row = grade_data[grade_data["學校類別"] == "貴校"]
                                ds_row = grade_data[grade_data["學校類別"] == "日校"]
                                
                                if not ys_row.empty:
                                    ys_count = int(ys_row["累計差值"].values[0])
                                    ys_pct = f"{ys_row['百分比'].values[0]:.1f}%"
                                else:
                                    ys_count = 0
                                    ys_pct = "0.0%"
                                
                                if not ds_row.empty:
                                    ds_count = int(ds_row["累計差值"].values[0])
                                    ds_pct = f"{ds_row['百分比'].values[0]:.1f}%"
                                else:
                                    ds_count = 0
                                    ds_pct = "0.0%"
                                
                                pivot_df = pd.concat([pivot_df, pd.DataFrame({
                                    "等級 Level": [grade],
                                    "貴校人數 Your School No.": [ys_count],
                                    "貴校百分比 Your School %": [ys_pct],
                                    "日校人數 Day Schools No.": [ds_count],
                                    "日校百分比 Day Schools %": [ds_pct]
                                })], ignore_index=True)
                            
                            # 處理 UNCL - 直接使用原始數字，計算百分比（不參與減法）
                            if not df_uncl.empty:
                                uncl_row = df_uncl.iloc[0]
                                uncl_ys_count = int(uncl_row["貴校"])
                                uncl_ds_count = int(uncl_row["日校"])
                                uncl_ys_pct = f"{(uncl_ys_count / attendance_ys) * 100:.1f}%"
                                uncl_ds_pct = f"{(uncl_ds_count / attendance_ds) * 100:.1f}%"
                                
                                pivot_df = pd.concat([pivot_df, pd.DataFrame({
                                    "等級 Level": ["UNCL"],
                                    "貴校人數 Your School No.": [uncl_ys_count],
                                    "貴校百分比 Your School %": [uncl_ys_pct],
                                    "日校人數 Day Schools No.": [uncl_ds_count],
                                    "日校百分比 Day Schools %": [uncl_ds_pct]
                                })], ignore_index=True)
                            
                            # 轉置數據表
                            transposed_df = pivot_df.set_index("等級 Level").T
                            st.dataframe(transposed_df, use_container_width=True)
                        else:
                            st.warning("⚠️ 無法計算百分比，缺少出席人數資料。 | Unable to calculate percentages due to missing attendance data.")
                except Exception as e:
                    st.error(f"❌ 發生錯誤 | Error processing file: {str(e)}")

# -----------------
# 標籤頁 1 的內容 / Tab 1 Content
# -----------------
with tab1:
    st.subheader("📝 項目分析數據提取 Item Report Data Extraction")
    col1, col2 = st.columns([2, 5])
    with col1:
        st.info("""
        💡 **本區適用於以下格式的報告：**
        表格橫向列出「平均分 Mean」、「標準差 S.D.」等數據。
                
        **Applicable for reports formatted like:** The table horizontally displays data such as 'Mean' and 'S.D.'.
        """)
        if os.path.exists("example1_item.png"):
            st.image("example1_item.png", caption="項目分析表格示例 | Example of Item Analysis Table")
        else:
            st.warning("⚠️ (提示: 系統未找到 example1_item.png | Image not found)")
    with col2:
        if current_file is None:
            st.warning("👆 請先在上方上載 PDF 檔案 | Please upload a PDF file above first.")
        else:
            with st.spinner("正在獲取資料... | Fetching data..."):
                try:
                    current_file.seek(0)
                    file_bytes = current_file.getvalue()
                    df_item = extract_item_analysis(file_bytes)
                    if df_item.empty:
                        st.error("❌ 無法提取數據！請確認你上載的是否為正確的「項目分析報告」。 \n *Failed to extract data! Please ensure you uploaded the correct 'Item Analysis Report'.*")
                    else:
                        st.success(f"✅ 提取成功！共獲取 {len(df_item)} 行數據。 \n *Extraction successful! {len(df_item)} rows retrieved.*")
                        if st.button("🔎 進入自訂項目分析 | Start Custom Item Analysis", type="primary", use_container_width=True, key="btn_item_app"):
                            st.switch_page("pages/1_custom_item_app.py")
                        st.subheader("📋 數據概覽 | Data Preview")
                        df_item_display = df_item.drop(columns=["row_index"]) if "row_index" in df_item.columns else df_item
                        st.table(df_item_display.style.format(precision=2))
                        st.download_button(
                            label="📥 下載 Excel 檔案 | Download Excel File",
                            data=convert_df_to_excel(df_item, "Item Analysis"),
                            file_name=f"{current_file.name.replace('.pdf', '')}_ItemAnalysis.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="btn_item",
                            type="primary"
                        )
                except Exception as e:
                    st.error(f"❌ 發生錯誤 | Error processing file: {str(e)}")

# -----------------
# 標籤頁 2 的內容 / Tab 2 Content
# -----------------
with tab2:
    st.subheader("✅ 多項選擇題數據提取 MCQ Analysis Data Extraction")
    col3, col4 = st.columns([2, 5])
    with col3:
        st.info("""
        💡 **本區適用於以下格式的報告：**
        表格列出「A, B, C, D」選項的選擇人數，並附有 ☑️ 標記顯示正確答案。
                
        **Applicable for reports formatted like:** The table lists the number of students for options 'A, B, C, D' and uses a ☑️ mark to indicate the correct answer.
        """)
        if os.path.exists("example2_mcq.png"):
            st.image("example2_mcq.png", caption="多項選擇題表格示例 | Example of MCQ Analysis Table")
        else:
            st.warning("⚠️ (提示: 系統未找到 example2_mcq.png | Image not found)")
    with col4:
        if current_file is None:
            st.warning("👆 請先在上方上載 PDF 檔案 | Please upload a PDF file above first.")
        else:
            with st.spinner("正在獲取資料... | Fetching data..."):
                try:
                    current_file.seek(0)
                    file_bytes = current_file.getvalue()
                    df_mcq = extract_mcq_analysis(file_bytes)
                    if df_mcq.empty:
                        st.error("❌ 無法提取數據！請確認你上載的是否為正確的「多項選擇題分析報告」。 \n *Failed to extract data! Please ensure you uploaded the correct 'MCQ Analysis Report'.*")
                    else:
                        st.success(f"✅ 提取成功！共獲取 {len(df_mcq)} 題的數據。 \n *Extraction successful! Data for {len(df_mcq)} questions retrieved. *")
                        if st.button("🔎 進入自訂多項選擇題分析 | Start Custom MCQ Analysis", type="primary", use_container_width=True, key="btn_mcq_app"):
                            st.switch_page("pages/2_custom_mcq_app.py")
                        st.subheader("📋 數據概覽 | Data Preview")
                        df_mcq_display = df_mcq.drop(columns=["row_index"]) if "row_index" in df_mcq.columns else df_mcq
                        st.table(df_mcq_display.style.format(precision=2))
                        st.download_button(
                            label="📥 下載 Excel 檔案 | Download Excel File",
                            data=convert_df_to_excel(df_mcq, "MCQ Analysis"),
                            file_name=f"{current_file.name.replace('.pdf', '')}_MCQAnalysis.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="btn_mcq",
                            type="primary"
                        )
                except Exception as e:
                    st.error(f"❌ 發生錯誤 | Error processing file: {str(e)}")

with tab3:
    st.subheader("🧠 LLM報告生成器 | LLM Report Generator")
    st.info(
        "本標籤頁會從自訂項目分析及自訂多項選擇題分析分頁讀取總覽表，並使用 Groq 生成分析報告。"
        "This tab reads overview tables from the custom item and MCQ pages through session state and generates reports using Groq."
    )

    total_df = st.session_state.get("custom_total_overview_df")
    item_df = st.session_state.get("custom_item_overview_df")
    mcq_df = st.session_state.get("custom_mcq_overview_df")

    if total_df is None and item_df is None and mcq_df is None:
        st.warning(
            "請先前往「總數」、「項目分析」與「多項選擇題分析」分頁生成總覽表。"
            " | Please first visit Total, Item Analysis and MCQ Analysis pages to build overview tables."
        )

    if total_df is not None:
        st.subheader("📌 總數分析總覽 Total Overview")
        st.dataframe(total_df, use_container_width=True, hide_index=True)

    if item_df is not None:
        st.subheader("📌 項目分析總覽 Item Overview")
        st.dataframe(item_df, use_container_width=True, hide_index=True)

    if mcq_df is not None:
        st.subheader("📌 多項選擇題總覽 MCQ Overview")
        st.dataframe(mcq_df, use_container_width=True, hide_index=True)

    default_prompt = (
        "請根據以下總覽表撰寫清晰、專業的分析報告，重點指出整體表現、強弱項與值得關注的地方。\n"
        "Write a clear and professional analytical report based on the overview tables, highlighting overall performance, strengths, weaknesses, and notable findings."   
    )
    custom_report_prompt = st.text_area(
        "報告指示 | Report Instructions",
        value=st.session_state.get("custom_report_prompt", default_prompt),
        key="custom_report_prompt",
        height=500,
    )

    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        api_key = None

    if not api_key:
        st.error(
            "缺少 Groq API 金鑰。請在 Streamlit secrets 中新增 GROQ_API_KEY。"
        )

    col_zh, col_en = st.columns(2)
    gen_zh = False
    gen_en = False
    with col_zh:
        gen_zh = st.button("生成中文報告", type="primary", use_container_width=True)
    with col_en:
        gen_en = st.button("Generate English Report", type="primary", use_container_width=True)

    if (gen_zh or gen_en) and not api_key:
        st.warning("無法生成報告，因為缺少 GROQ_API_KEY。| Cannot generate report because GROQ_API_KEY is missing.")

    if gen_zh or gen_en:
        if item_df is None and mcq_df is None:
            st.warning(
                "無法生成報告，因為沒有可用的總覽表。請先前往相關分頁生成 overview tables。"
            )
        elif api_key:
            try:
                if gen_zh:
                    report = generate_groq_report("zh", total_df, item_df, mcq_df, custom_report_prompt)
                    st.session_state["generated_report_zh"] = report
                if gen_en:
                    report = generate_groq_report("en", total_df, item_df, mcq_df, custom_report_prompt)
                    st.session_state["generated_report_en"] = report
            except Exception as e:
                st.error(f"❌ 報告生成失敗 | Report generation failed: {str(e)}")

    if st.session_state.get("generated_report_zh"):
        st.subheader("📄 已生成中文報告 | Generated Chinese Report")
        st.write(st.session_state.get("generated_report_zh", ""))
        pdf_bytes = build_report_pdf(st.session_state.get("generated_report_zh", ""))
        st.download_button(
            label="📥 下載中文報告 PDF | Download Chinese Report PDF",
            data=pdf_bytes,
            file_name="school_report_zh.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    if st.session_state.get("generated_report_en"):
        st.subheader("📄 Generated English Report")
        st.write(st.session_state.get("generated_report_en", ""))
        pdf_bytes = build_report_pdf(st.session_state.get("generated_report_en", ""))
        st.download_button(
            label="📥 Download English Report PDF",
            data=pdf_bytes,
            file_name="school_report_en.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
