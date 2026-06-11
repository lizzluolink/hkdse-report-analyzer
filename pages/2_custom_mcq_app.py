import sys
import os
from pathlib import Path

# Add parent directory to path to import pdf_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from pdf_utils import extract_mcq_analysis, convert_df_to_pdf, convert_df_to_styled_excel

st.set_page_config(page_title="HKDSE Statistical Report Data Extraction | HKDSE學校統計報告 數據提取工具", page_icon="🧭", layout="wide")
st.title("🎯 自訂多項選擇題分析 | Custom MCQ Analysis")

if "mcq_custom_cols" not in st.session_state:
    st.session_state.mcq_custom_cols = []
if "mcq_col_options_history" not in st.session_state:
    st.session_state.mcq_col_options_history = {}
if "item_custom_values" not in st.session_state:
    st.session_state.item_custom_values = {}
if "mcq_custom_values" not in st.session_state:
    st.session_state.mcq_custom_values = {}
if "mcq_clear_inputs" not in st.session_state:
    st.session_state.mcq_clear_inputs = False
if "mcq_save_note" not in st.session_state:
    st.session_state.mcq_save_note = ""
if "mcq_cutoff_high" not in st.session_state:
    st.session_state.mcq_cutoff_high = 70
if "mcq_cutoff_low" not in st.session_state:
    st.session_state.mcq_cutoff_low = 30
if "mcq_exp_high" not in st.session_state:
    st.session_state.mcq_exp_high = 80
if "mcq_exp_inter" not in st.session_state:
    st.session_state.mcq_exp_inter = 60
if "mcq_exp_low" not in st.session_state:
    st.session_state.mcq_exp_low = 40
if "mcq_sort_levels" not in st.session_state:
    st.session_state.mcq_sort_levels = [{"col": "row_index", "order": "desc"}]

def prepare_mcq_analysis_for_custom(df):
    df = df.copy()
    def get_top_option(row, prefix):
        opts = {
            "A": row.get(f"{prefix} A_No.", 0),
            "B": row.get(f"{prefix} B_No.", 0),
            "C": row.get(f"{prefix} C_No.", 0),
            "D": row.get(f"{prefix} D_No.", 0),
        }
        for k in opts:
            try:
                opts[k] = float(opts[k])
            except:
                opts[k] = 0
        return max(opts, key=opts.get)
    
    df["Your school Top Option"] = df.apply(lambda r: get_top_option(r, "Your school"), axis=1)
    df["Day schools Top Option"] = df.apply(lambda r: get_top_option(r, "Day schools"), axis=1)
    
    # 計算百分比和正確率
    def calculate_percentages(row, prefix):
        try:
            a = float(row.get(f"{prefix} A_No.", 0))
            b = float(row.get(f"{prefix} B_No.", 0))
            c = float(row.get(f"{prefix} C_No.", 0))
            d = float(row.get(f"{prefix} D_No.", 0))
            total = a + b + c + d
            
            if total > 0:
                return {
                    f"{prefix} A_%": (a / total) * 100,
                    f"{prefix} B_%": (b / total) * 100,
                    f"{prefix} C_%": (c / total) * 100,
                    f"{prefix} D_%": (d / total) * 100,
                }
            else:
                return {
                    f"{prefix} A_%": 0,
                    f"{prefix} B_%": 0,
                    f"{prefix} C_%": 0,
                    f"{prefix} D_%": 0,
                }
        except:
            return {
                f"{prefix} A_%": 0,
                f"{prefix} B_%": 0,
                f"{prefix} C_%": 0,
                f"{prefix} D_%": 0,
            }
    
    # 計算 Your school 的百分比
    your_pcts = df.apply(lambda r: calculate_percentages(r, "Your school"), axis=1)
    for opt in ["A", "B", "C", "D"]:
        df[f"Your school {opt}_%"] = your_pcts.apply(lambda x: x.get(f"Your school {opt}_%", 0))
    
    # 計算 Day schools 的百分比
    day_pcts = df.apply(lambda r: calculate_percentages(r, "Day schools"), axis=1)
    for opt in ["A", "B", "C", "D"]:
        df[f"Day schools {opt}_%"] = day_pcts.apply(lambda x: x.get(f"Day schools {opt}_%", 0))
    
    # 計算正確率
    def get_correct_rate(row, prefix):
        corr_ans = str(row.get("Corr. Ans", "")).replace("☑️", "").strip()
        if corr_ans in ["A", "B", "C", "D"]:
            return row.get(f"{prefix} {corr_ans}_%", 0)
        return 0
    
    df["Your school Correct %"] = df.apply(lambda r: get_correct_rate(r, "Your school"), axis=1)
    df["Day schools Correct %"] = df.apply(lambda r: get_correct_rate(r, "Day schools"), axis=1)
    
    return df

st.page_link("app.py", label="返回主頁 | Main Page", icon="⬅️")

if "processed_mcq_df" not in st.session_state or st.session_state.processed_mcq_df is None:
    source_pdf_bytes = st.session_state.get("source_pdf_bytes")
    if isinstance(source_pdf_bytes, (bytes, bytearray)) and source_pdf_bytes:
        st.session_state.processed_mcq_df = extract_mcq_analysis(source_pdf_bytes)

if "processed_mcq_df" not in st.session_state or st.session_state.processed_mcq_df is None:
    st.warning("未找到多項選擇題資料，請回到主頁完成上載。| No MCQ data found yet. Please upload the report in the main page.")
    st.stop()

df_mcq_c = st.session_state.processed_mcq_df.copy()
source_name = st.session_state.get("source_pdf_name", "未命名檔案")
st.success(f"已載入主頁資料 Data Loaded from: {source_name}")

if not df_mcq_c.empty:
    df_mcq_c = prepare_mcq_analysis_for_custom(df_mcq_c)
    if "row_index" not in df_mcq_c.columns:
        df_mcq_c.insert(0, "row_index", range(1, len(df_mcq_c) + 1))
    if "題號" not in df_mcq_c.columns:
        df_mcq_c.insert(1, "題號", df_mcq_c.get("Question Number", range(1, len(df_mcq_c) + 1)))
    if "Question Number" in df_mcq_c.columns:
        df_mcq_c = df_mcq_c.drop(columns=["Question Number"])

    sel_q_mcq = None

    st.markdown("---")
    st.info("🏷️ 1. 建立自訂欄位並為題目設定分類 Create Custom Fields and Set Categories for Questions")
    step1_col, step2_col = st.columns([1, 1], border=True)

    with step1_col:
        st.subheader("1.1 建立自訂欄位 (最多 6 個) | Create Custom Fields (Maximum 6)")
        st.caption("自訂欄位可用於為每題設定不同的分類，例如「試卷」、「題型」、「難度」等，以協助後續的篩選和排序。")
        with st.form("mcq_add_field_form", clear_on_submit=True, border=False):
            new_col = st.text_input("輸入新自訂欄位名稱 | Enter New Custom Field Name", key="new_col_input_mcq")
            submitted = st.form_submit_button("➕ 新增欄位 | Add Field")
            if submitted:
                if new_col and new_col not in st.session_state.mcq_custom_cols and len(st.session_state.mcq_custom_cols) < 6:
                    st.session_state.mcq_custom_cols.append(new_col)
                    st.session_state.mcq_col_options_history[new_col] = []
                elif new_col and new_col not in st.session_state.mcq_custom_cols and len(st.session_state.mcq_custom_cols) >= 6:
                    st.warning("⚠️ 超過欄位數量限制 Field limit exceeded.")
        
        if st.session_state.mcq_custom_cols:
            st.success(f"已建立欄位 | Created Fields: {', '.join(st.session_state.mcq_custom_cols)}")

    with step2_col:
        st.subheader("1.2 為各題設定分類 | Set Categories for Questions")
        st.caption("在此模組為各題設定剛才建立的自訂欄位的分類，例如「試卷一」、「選擇題」、「高難度」等。")
        question_options = [f"{row['題號']} [{row['row_index']}]" for _, row in df_mcq_c.iterrows()]
        seq_map = {f"{row['題號']} [{row['row_index']}]": row['row_index'] for _, row in df_mcq_c.iterrows()}
        sel_q_mcq_display = st.multiselect("選擇題號（可選多於一項） | Select Question item(s) (You may select more than one option)", question_options, default=question_options[:1], key="mcq_q_sel")
        sel_q_mcq = [seq_map[q] for q in sel_q_mcq_display]

        if st.session_state.mcq_clear_inputs:
            for col in st.session_state.mcq_custom_cols:
                sel_key = f"sel_mcq_{col}"
                new_key = f"new_val_mcq_{col}"
                st.session_state[sel_key] = ""
                st.session_state[new_key] = ""
            st.session_state.mcq_clear_inputs = False

        if sel_q_mcq_display:
            selected_display = ", ".join(sel_q_mcq_display)
            st.write(f"**正在編輯 Editing: {selected_display}**")
            all_values = [st.session_state.mcq_custom_values.get(idx, {}) for idx in sel_q_mcq]
            curr_vals_mcq = {}
            for col in st.session_state.mcq_custom_cols:
                values_for_col = {v.get(col, "") for v in all_values}
                curr_vals_mcq[col] = values_for_col.pop() if len(values_for_col) == 1 else ""
        else:
            st.warning("請先選擇至少一題。| Please select at least one question first.")
            curr_vals_mcq = {}

        input_results_m = {}
        for col in st.session_state.mcq_custom_cols:
            history_opts = st.session_state.mcq_col_options_history.get(col, [])
            options = [""] + history_opts + ["➕ 輸入新類別 Enter a new category"]
            default_idx = 0
            curr_val = curr_vals_mcq.get(col, "")
            if curr_val in options:
                default_idx = options.index(curr_val)
            sel_col, new_col = st.columns([1, 1])
            with sel_col:
                sel_key = f"sel_mcq_{col}"
                sel_val = st.selectbox(f"{col}:", options=options, index=default_idx, key=sel_key)
            with new_col:
                if sel_val == "➕ 輸入新類別 Enter a new category":
                    new_key = f"new_val_mcq_{col}"
                    if new_key not in st.session_state:
                        st.session_state[new_key] = ""
                    new_val = st.text_input(f"請輸入新的「{col}」 | Enter new {col}:", key=new_key)
                    input_results_m[col] = new_val
                else:
                    input_results_m[col] = sel_val

        submit_col, note_col = st.columns([1, 1])
        with submit_col:
            submit_btn_m = st.button("📥 儲存設定 Save Settings", key=f"mcq_save_btn_{'_'.join(str(x) for x in sel_q_mcq)}")
        save_note_m = note_col.empty()
        if st.session_state.mcq_save_note:
            save_note_m.caption(st.session_state.mcq_save_note)

        if submit_btn_m and sel_q_mcq:
            for idx in sel_q_mcq:
                if idx not in st.session_state.mcq_custom_values:
                    st.session_state.mcq_custom_values[idx] = {}
                for col, val in input_results_m.items():
                    if val:
                        st.session_state.mcq_custom_values[idx][col] = val
                        if val not in st.session_state.mcq_col_options_history[col]:
                            st.session_state.mcq_col_options_history[col].append(val)
            st.session_state["mcq_last_saved_q"] = sel_q_mcq
            st.session_state["mcq_save_note"] = f"已為以下題目設定 「{col}」 分類 | Successfully defined {col} categories for questions: {selected_display}"
            st.session_state.mcq_clear_inputs = True
            st.rerun()

    df_mcq_display = df_mcq_c.copy()
    for col in st.session_state.mcq_custom_cols:
        df_mcq_display[col] = df_mcq_display["row_index"].apply(lambda x: st.session_state.mcq_custom_values.get(x, {}).get(col, ""))

    st.markdown("---")
    st.info("📍 2. 校本自訂分析 School-based Customize Analysis")

    col_attainment, col_expectation = st.columns(2, border=True)

    with col_attainment:
        st.subheader("2.1 定義「平均得分率」的分類 | Define Level of Attainment")
        st.caption("此模組用於根據全港日校考生的平均得分率，將題目分為「高得分率（High attainment）」、「中等得分率（Intermediate attainment）」、「低得分率（Low attainment）」三個類別，亦即把學生在每題的表現分為「良好（Good）」、「中等（Intermediate）」及「未如理想（Poor）」。在設定上述三個類別的分界值時，可參考香港考試及評核局於該年發布的HKDSE評核資訊及分析，或按該學科的情況作專業判斷。")
        col_cut1, col_cut2 = st.columns(2)
        with col_cut1:
            st.session_state.mcq_cutoff_high = st.number_input(
                "高／中得分率分界值（%）| High/Intermediate attainment Cutoff:",
                min_value=0, max_value=100, value=st.session_state.mcq_cutoff_high, step=1,
                key="mcq_cutoff_high_input", help="日校得分率高於此值，即視為「高得分率」 | Day school Mean % above this value are classified as 'High attainment'."
            )
        with col_cut2:
            st.session_state.mcq_cutoff_low = st.number_input(
                "中／低得分率分界值（%）| Intermediate/Low attainment Cutoff:",
                min_value=0, max_value=100, value=st.session_state.mcq_cutoff_low, step=1,
                key="mcq_cutoff_low_input", help="日校得分率低於此值，即視為「低得分率」 | Day school Mean % below this value are classified as 'Low attainment'."
            )
        st.markdown(f"""
                   題目得分率設定：高得分率 ≥ {st.session_state.mcq_cutoff_high}% | 中得分率 {st.session_state.mcq_cutoff_low}% - {st.session_state.mcq_cutoff_high}% | 低得分率 ≤ {st.session_state.mcq_cutoff_low}%
                   
                   Question Attainment Levels: High attainment ≥{st.session_state.mcq_cutoff_high}% | Intermediate attainment {st.session_state.mcq_cutoff_low}% - {st.session_state.mcq_cutoff_high}% | Low attainment ≤{st.session_state.mcq_cutoff_low}%
                   """)

    with col_expectation:
        st.subheader("2.2 校本預期平均得分率 | School-based Expected Attainment")
        st.caption("在設定「全港日校考生的平均得分率」的類別後，此模組讓學校按校本情況進一步設定學生在高、中、低得分率題目的「校本預期平均得分率」，例如是與全港水平一致、較高或較低，以協助分析該校學生在各題中的表現是否達到校本的預期水平。（此「預期平均得分率」即校本的「底線」，當學生在某題的表現低於這條底線時，便代表需要注意及跟進）。")
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        with col_exp1:
            st.session_state.mcq_exp_high = st.number_input(
                "預期高得分率題目得分率（%）| Expected for High attainment questions:",
                min_value=0, max_value=100, value=st.session_state.mcq_exp_high, step=1,
                key="mcq_exp_high_input"
            )
        with col_exp2:
            st.session_state.mcq_exp_inter = st.number_input(
                "預期中等得分率題目得分率（%）| Expected for Intermediate attainment questions:",
                min_value=0, max_value=100, value=st.session_state.mcq_exp_inter, step=1,
                key="mcq_exp_inter_input"
            )
        with col_exp3:
            st.session_state.mcq_exp_low = st.number_input(
                "預期低得分率題目得分率（%）| Expected for Low attainment questions:",
                min_value=0, max_value=100, value=st.session_state.mcq_exp_low, step=1,
                key="mcq_exp_low_input"
            )

    st.markdown("---")

    # 計算 Day School Attainment
    def get_mcq_attainment(rate):
        rate_pct = rate if rate >= 1 else rate * 100
        if rate_pct >= st.session_state.mcq_cutoff_high:
            return "High attainment"
        elif rate_pct <= st.session_state.mcq_cutoff_low:
            return "Low attainment"
        else:
            return "Intermediate attainment"

    df_mcq_display["Day School Attainment"] = df_mcq_display["Day schools Correct %"].apply(get_mcq_attainment)

    # 計算 School-based Expected Attainment
    def get_mcq_expected_status(row):
        attainment = row["Day School Attainment"]
        your_rate = row["Your school Correct %"]
        your_rate_pct = your_rate if your_rate >= 1 else your_rate * 100

        if attainment == "High attainment":
            expected = st.session_state.mcq_exp_high
        elif attainment == "Intermediate attainment":
            expected = st.session_state.mcq_exp_inter
        else:  # Low attainment
            expected = st.session_state.mcq_exp_low

        return "Attained" if your_rate_pct >= expected else "Below Expectation"

    df_mcq_display["School-based Expected Attainment"] = df_mcq_display.apply(get_mcq_expected_status, axis=1)

    def status_cell_style(val):
        if val == "High attainment":
            return "background-color: #d4edda"
        if val == "Intermediate attainment":
            return "background-color: #e5dbf7"
        if val == "Low attainment":
            return "background-color: #ffe5cc"
        if isinstance(val, str) and val.startswith("Attained"):
            return "background-color: #fff3b3; color: #2e7d32; font-weight: bold"
        if isinstance(val, str) and val.startswith("Below Expectation"):
            return "background-color: #fff3b3; color: #8b0000; font-style: italic"
        return ""

    def style_mcq_row(row):
        styles = [""] * len(row)
        corr_ans = str(row.get("Corr. Ans", "")).replace("☑️", "").strip()
        if corr_ans:
            your_top = str(row.get("Your school Top Option", "")).strip()
            day_top = str(row.get("Day schools Top Option", "")).strip()
            if your_top and your_top != corr_ans:
                styles[row.index.get_loc("Your school Top Option")] = "color: #8b0000; font-weight: bold; font-style: italic; background-color: #ffcccc"
            if day_top and day_top != corr_ans:
                styles[row.index.get_loc("Day schools Top Option")] = "color: #8b0000; font-weight: bold; font-style: italic; background-color: #ffcccc"
        return styles

    def build_mcq_export_df(df, for_excel=False):
        export_df = df.copy()
        if not for_excel:
            formatters = {
                "Your school Correct %": lambda x: f"{x:.1f}%" if pd.notna(x) else "",
                "Day schools Correct %": lambda x: f"{x:.1f}%" if pd.notna(x) else "",
                "Your school A_%": lambda x: f"{x:.1f}" if pd.notna(x) else "",
                "Your school B_%": lambda x: f"{x:.1f}" if pd.notna(x) else "",
                "Your school C_%": lambda x: f"{x:.1f}" if pd.notna(x) else "",
                "Your school D_%": lambda x: f"{x:.1f}" if pd.notna(x) else "",
                "Day schools A_%": lambda x: f"{x:.1f}" if pd.notna(x) else "",
                "Day schools B_%": lambda x: f"{x:.1f}" if pd.notna(x) else "",
                "Day schools C_%": lambda x: f"{x:.1f}" if pd.notna(x) else "",
                "Day schools D_%": lambda x: f"{x:.1f}" if pd.notna(x) else "",
            }
            for col, fn in formatters.items():
                if col in export_df.columns:
                    export_df[col] = export_df[col].apply(fn)
        else:
            for col in export_df.columns:
                converted = pd.to_numeric(export_df[col], errors='coerce')
                if not converted.isna().all():
                    export_df[col] = converted
        return export_df

    def build_mcq_style_map(df):
        style_map = {}
        columns = list(df.columns)
        # Use positional row indices (0-based) to remain consistent after filtering/sorting
        for pos, (_, row) in enumerate(df.iterrows()):
            row_idx = pos
            if "Corr. Ans" in columns:
                col_idx = columns.index("Corr. Ans")
                style_map[(row_idx, col_idx)] = {"fill": "#d4edda"}
            if "Your school Top Option" in columns:
                col_idx = columns.index("Your school Top Option")
                corr_ans = str(row.get("Corr. Ans", "")).replace("☑️", "").strip()
                your_top = str(row.get("Your school Top Option", "")).strip()
                if corr_ans and your_top and your_top != corr_ans:
                    style_map[(row_idx, col_idx)] = {"fill": "#ffcccc", "font_color": "#8b0000", "bold": True}
            if "Day schools Top Option" in columns:
                col_idx = columns.index("Day schools Top Option")
                corr_ans = str(row.get("Corr. Ans", "")).replace("☑️", "").strip()
                day_top = str(row.get("Day schools Top Option", "")).strip()
                if corr_ans and day_top and day_top != corr_ans:
                    style_map[(row_idx, col_idx)] = {"fill": "#ffcccc", "font_color": "#8b0000", "bold": True}
            if "Day School Attainment" in columns:
                col_idx = columns.index("Day School Attainment")
                attainment = row["Day School Attainment"]
                if attainment == "High attainment":
                    style_map[(row_idx, col_idx)] = {"fill": "#d4edda"}
                elif attainment == "Intermediate attainment":
                    style_map[(row_idx, col_idx)] = {"fill": "#e5dbf7"}
                elif attainment == "Low attainment":
                    style_map[(row_idx, col_idx)] = {"fill": "#ffe5cc"}
            if "School-based Expected Attainment" in columns:
                col_idx = columns.index("School-based Expected Attainment")
                expected = row["School-based Expected Attainment"]
                if isinstance(expected, str) and expected.startswith("Attained"):
                    style_map[(row_idx, col_idx)] = {"fill": "#fff3b3", "font_color": "#2e7d32", "bold": True}
                elif isinstance(expected, str) and expected.startswith("Below Expectation"):
                    style_map[(row_idx, col_idx)] = {"fill": "#fff3b3", "font_color": "#8b0000"}
        return style_map

    st.write("📊 **總覽表 (本表跟隨以上設定自動更新) | Overview Table (This table updates automatically based on the above settings)**")
    st.session_state["custom_mcq_overview_df"] = df_mcq_display.copy()
    st.dataframe(
        df_mcq_display.style
            .format({
                "Your school Correct %": "{:.1f}%",
                "Day schools Correct %": "{:.1f}%",
                "Your school A_%": "{:.1f}",
                "Your school B_%": "{:.1f}",
                "Your school C_%": "{:.1f}",
                "Your school D_%": "{:.1f}",
                "Day schools A_%": "{:.1f}",
                "Day schools B_%": "{:.1f}",
                "Day schools C_%": "{:.1f}",
                "Day schools D_%": "{:.1f}"
            })
            .apply(
                lambda col: col.map(lambda x: "background-color: #d4edda" if col.name == "Corr. Ans" else ""),
                axis=0
            )
            .apply(
                lambda col: col.map(status_cell_style),
                subset=["Day School Attainment", "School-based Expected Attainment"],
                axis=0
            )
            .apply(style_mcq_row, axis=1),
        use_container_width=True, hide_index=True
    )

    export_df_pdf = build_mcq_export_df(df_mcq_display, for_excel=False)
    export_df_excel = build_mcq_export_df(df_mcq_display, for_excel=True)
    style_map = build_mcq_style_map(df_mcq_display)
    excel_bytes = convert_df_to_styled_excel(export_df_excel, style_map, sheet_name="MCQ Overview")
    pdf_bytes = convert_df_to_pdf(export_df_pdf, style_map, title="多項選擇題分析 | 總覽表 MCQ Analysis | Overview Table")

    col_pdf, col_excel = st.columns(2)
    with col_pdf:
        st.download_button(
            label="📄 下載 PDF 總覽表 | Download Overview PDF",
            data=pdf_bytes,
            file_name=f"{source_name.replace('.pdf', '')}_MCQOverview.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    with col_excel:
        st.download_button(
            label="📥 下載 Excel 總覽表 | Download Overview Excel",
            data=excel_bytes,
            file_name=f"{source_name.replace('.pdf', '')}_MCQOverview.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )

    st.markdown("---")
    st.info("↕️ 3. 篩選與排序分析 Filter and Sort Analysis")
    st.subheader("3.1 篩選 Filter")
    f_cols_mcq = st.columns(max(len(st.session_state.mcq_custom_cols) + 2, 2))
    active_filters_mcq = {}
    for i, col in enumerate(st.session_state.mcq_custom_cols):
        with f_cols_mcq[i]:
            u_vals_mcq = [x for x in df_mcq_display[col].unique() if str(x).strip()]
            active_filters_mcq[col] = st.multiselect(f"{col}", u_vals_mcq, key=f"filter_mcq_{col}")
    
    with f_cols_mcq[len(st.session_state.mcq_custom_cols)]:
        attainment_vals_mcq = [x for x in df_mcq_display["Day School Attainment"].unique() if str(x).strip()]
        active_filters_mcq["Day School Attainment"] = st.multiselect("Day School Attainment", attainment_vals_mcq, key="filter_mcq_attainment")
    
    with f_cols_mcq[len(st.session_state.mcq_custom_cols) + 1]:
        expected_vals_mcq = [x for x in df_mcq_display["School-based Expected Attainment"].unique() if str(x).strip()]
        active_filters_mcq["School-based Expected Attainment"] = st.multiselect("School-based Expected Attainment", expected_vals_mcq, key="filter_mcq_expected")

    final_mcq_df = df_mcq_display.copy()
    for col, s_filters in active_filters_mcq.items():
        if s_filters:
            final_mcq_df = final_mcq_df[final_mcq_df[col].isin(s_filters)]

    st.subheader("3.2 排序 Sort")

    def _rerun_on_sort_change_mcq():
        st.session_state["_mcq_sort_rerun_toggle"] = not st.session_state.get("_mcq_sort_rerun_toggle", False)

    sort_columns_opts = [
        "row_index",
        "Your school Correct %",
        "Day schools Correct %",
        "Day School Attainment",
        "School-based Expected Attainment",
    ]

    add_col, remove_col = st.columns([1, 2], gap="xxsmall")
    with add_col:
        if st.button("➕ 新增排序欄 Add Level", key="mcq_add_sort_level"):
            if len(st.session_state.mcq_sort_levels) < 4:
                st.session_state.mcq_sort_levels.append({"col": "row_index", "order": "desc"})
                _rerun_on_sort_change_mcq()
    with remove_col:
        if st.button("➖ 移除排序欄 Remove Level", key="mcq_remove_sort_level"):
            if len(st.session_state.mcq_sort_levels) > 1:
                st.session_state.mcq_sort_levels.pop()
                _rerun_on_sort_change_mcq()

    for i, level in enumerate(st.session_state.mcq_sort_levels):
        cols = st.columns([1, 1])
        with cols[0]:
            sel = st.selectbox(f"欄位 Field {i+1}", sort_columns_opts, index=sort_columns_opts.index(level.get("col") if level.get("col") in sort_columns_opts else "row_index"), key=f"mcq_sort_col_{i}", on_change=_rerun_on_sort_change_mcq)
            st.session_state.mcq_sort_levels[i]["col"] = sel
        with cols[1]:
            order = st.radio("", ["由高至低 | Descending Order", "由低至高 | Ascending Order"], index=0 if level.get("order", "desc") == "desc" else 1, horizontal=True, key=f"mcq_sort_order_{i}", on_change=_rerun_on_sort_change_mcq)
            st.session_state.mcq_sort_levels[i]["order"] = "desc" if "由高至低" in order else "asc"
    # Apply multi-level sorting based on session_state.mcq_sort_levels
    try:
        sort_by_list = []
        ascending_list = []
        temp_sort_cols = []
        for idx, lvl in enumerate(st.session_state.mcq_sort_levels):
            col = lvl.get("col")
            order = lvl.get("order", "desc")
            ascending = True if order == "asc" else False

            if col == "Day School Attainment":
                rank_map = {"High attainment": 3, "Intermediate attainment": 2, "Low attainment": 1}
                temp_col = f"___mcq_sort_key_{idx}"
                final_mcq_df[temp_col] = final_mcq_df[col].map(rank_map).fillna(0)
                sort_by_list.append(temp_col)
                temp_sort_cols.append(temp_col)
                ascending_list.append(ascending)
            elif col == "School-based Expected Attainment":
                rank_map = {"Attained": 2, "Below Expectation": 1}
                temp_col = f"___mcq_sort_key_{idx}"
                final_mcq_df[temp_col] = final_mcq_df[col].map(rank_map).fillna(0)
                sort_by_list.append(temp_col)
                temp_sort_cols.append(temp_col)
                ascending_list.append(ascending)
            elif col in ["row_index", "Your school Correct %", "Day schools Correct %"]:
                final_mcq_df[col] = pd.to_numeric(final_mcq_df[col], errors='coerce')
                sort_by_list.append(col)
                ascending_list.append(ascending)
            else:
                sort_by_list.append(col)
                ascending_list.append(ascending)

        if sort_by_list:
            final_mcq_df = final_mcq_df.sort_values(by=sort_by_list, ascending=ascending_list, kind='mergesort')
        for c in temp_sort_cols:
            if c in final_mcq_df.columns:
                final_mcq_df = final_mcq_df.drop(columns=[c])
    except Exception:
        pass

    st.dataframe(
        final_mcq_df.style
            .format({
                "Your school Correct %": "{:.1f}%",
                "Day schools Correct %": "{:.1f}%",
                "Your school A_%": "{:.1f}",
                "Your school B_%": "{:.1f}",
                "Your school C_%": "{:.1f}",
                "Your school D_%": "{:.1f}",
                "Day schools A_%": "{:.1f}",
                "Day schools B_%": "{:.1f}",
                "Day schools C_%": "{:.1f}",
                "Day schools D_%": "{:.1f}"
            })
            .apply(
                lambda col: col.map(lambda x: "background-color: #d4edda" if col.name == "Corr. Ans" else ""),
                axis=0
            )
            .apply(
                lambda col: col.map(status_cell_style),
                subset=["Day School Attainment", "School-based Expected Attainment"],
                axis=0
            )
            .apply(style_mcq_row, axis=1),
        use_container_width=True, hide_index=True
    )
    
    # Build dynamic PDF title with filter and sort info
    filter_info_mcq = []
    for col, s_filters in active_filters_mcq.items():
        if s_filters:
            filter_info_mcq.append(f"{col}: {', '.join(map(str, s_filters))}")
    filter_str_mcq = " | ".join(filter_info_mcq) if filter_info_mcq else "無篩選 | No filters"
    # describe sort levels
    sort_descs = [f"{lvl.get('col')} ({'asc' if lvl.get('order')=='asc' else 'desc'})" for lvl in st.session_state.mcq_sort_levels]
    sort_str = " > ".join(sort_descs) if sort_descs else "row_index (desc)"
    pdf_title_mcq = f"多項選擇題分析 | MCQ Analysis | {filter_str_mcq} | Sort: {sort_str}"
    
    filtered_export_df = build_mcq_export_df(final_mcq_df, for_excel=True)
    filtered_export_pdf = convert_df_to_pdf(build_mcq_export_df(final_mcq_df, for_excel=False), build_mcq_style_map(final_mcq_df), title=pdf_title_mcq)
    filtered_export_excel = convert_df_to_styled_excel(filtered_export_df, build_mcq_style_map(final_mcq_df), sheet_name="MCQ Filtered")
    step4_pdf_col, step4_excel_col = st.columns(2)
    with step4_pdf_col:
        st.download_button(
            label="📄 下載 PDF 篩選表 | Download Filtered PDF",
            data=filtered_export_pdf,
            file_name=f"{source_name.replace('.pdf', '')}_MCQFiltered.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    with step4_excel_col:
        st.download_button(
            label="📥 下載 Excel 篩選表 | Download Filtered Excel",
            data=filtered_export_excel,
            file_name=f"{source_name.replace('.pdf', '')}_MCQFiltered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
else:
    st.error("找不到可用的項目分析資料。 | No MCQ analysis data available.")

st.markdown("---")
