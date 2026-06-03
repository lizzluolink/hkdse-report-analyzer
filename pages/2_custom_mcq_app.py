import pandas as pd
import streamlit as st

from pdf_utils import extract_mcq_analysis

st.set_page_config(page_title="MCQ Analysis", page_icon="🎯", layout="wide")
st.title("🎯 自定義 MCQ 分析 app")
st.caption("此頁會讀取主 app 已處理好的資料。請先回主 app 上載 PDF，並按『處理檔案並啟用自定義分析 app』。")

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

def highlight_mcq_row(row):
    your_top = str(row.get("Your school Top Option", "")).strip()
    day_top = str(row.get("Day schools Top Option", "")).strip()
    corr_ans = str(row.get("Corr. Ans", "")).replace("☑️", "").strip()
    cond1 = (your_top != corr_ans)
    cond2 = (your_top != day_top)
    if cond1 and cond2:
        return ["background-color: #f8d7da"] * len(row)
    elif cond1:
        return ["background-color: #fff3cd"] * len(row)
    elif cond2:
        return ["background-color: #d1ecf1"] * len(row)
    else:
        return [""] * len(row)

st.page_link("app.py", label="⬅️ 返回主 app", icon="⬅️")

if "processed_mcq_df" not in st.session_state or st.session_state.processed_mcq_df is None:
    source_pdf_bytes = st.session_state.get("source_pdf_bytes")
    if isinstance(source_pdf_bytes, (bytes, bytearray)) and source_pdf_bytes:
        st.session_state.processed_mcq_df = extract_mcq_analysis(source_pdf_bytes)

if "processed_mcq_df" not in st.session_state or st.session_state.processed_mcq_df is None:
    st.warning("尚未找到已處理好的 MCQ 資料。請先回主 app 完成前處理。")
    st.stop()

df_mcq_c = st.session_state.processed_mcq_df.copy()
source_name = st.session_state.get("source_pdf_name", "未命名檔案")
st.success(f"已載入主 app 處理完成的資料：{source_name}")

if not df_mcq_c.empty:
    df_mcq_c = prepare_mcq_analysis_for_custom(df_mcq_c)
    if "初始序列" not in df_mcq_c.columns:
        df_mcq_c.insert(0, "初始序列", range(1, len(df_mcq_c) + 1))
    if "題號" not in df_mcq_c.columns:
        df_mcq_c.insert(1, "題號", df_mcq_c.get("Question Number", range(1, len(df_mcq_c) + 1)))

    sel_q_mcq = None
    step1_col, step2_col = st.columns([1, 1])

    with step1_col:
        st.info("Step 1：建立 MCQ 自定義欄位 (最多 6 個)")
        with st.form("mcq_add_field_form", clear_on_submit=True):
            new_col = st.text_input("輸入新自定義欄位名稱：", key="new_col_input_mcq")
            submitted = st.form_submit_button("➕ 新增欄位")
            if submitted:
                if new_col and new_col not in st.session_state.mcq_custom_cols and len(st.session_state.mcq_custom_cols) < 6:
                    st.session_state.mcq_custom_cols.append(new_col)
                    st.session_state.mcq_col_options_history[new_col] = []
        
        if st.session_state.mcq_custom_cols:
            st.success(f"目前建立的欄位：{', '.join(st.session_state.mcq_custom_cols)}")

    with step2_col:
        st.info("Step 2：為每一題設定分類 (下拉聯想與新增)")
        question_options = [f"{row['題號']} [{row['初始序列']}]" for _, row in df_mcq_c.iterrows()]
        seq_map = {f"{row['題號']} [{row['初始序列']}]": row['初始序列'] for _, row in df_mcq_c.iterrows()}
        sel_q_mcq_display = st.multiselect("選擇要輸入標籤的題號：", question_options, default=question_options[:1], key="mcq_q_sel")
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
            st.write(f"**正在編輯：{selected_display}**")
            all_values = [st.session_state.mcq_custom_values.get(idx, {}) for idx in sel_q_mcq]
            curr_vals_mcq = {}
            for col in st.session_state.mcq_custom_cols:
                values_for_col = {v.get(col, "") for v in all_values}
                curr_vals_mcq[col] = values_for_col.pop() if len(values_for_col) == 1 else ""
        else:
            st.warning("請先選擇至少一題。")
            curr_vals_mcq = {}

        input_results_m = {}
        for col in st.session_state.mcq_custom_cols:
            history_opts = st.session_state.mcq_col_options_history.get(col, [])
            options = [""] + history_opts + ["輸入新文本"]
            default_idx = 0
            curr_val = curr_vals_mcq.get(col, "")
            if curr_val in options:
                default_idx = options.index(curr_val)
            sel_col, new_col = st.columns([1, 1])
            with sel_col:
                sel_key = f"sel_mcq_{col}"
                sel_val = st.selectbox(f"{col}:", options=options, index=default_idx, key=sel_key)
            with new_col:
                if sel_val == "輸入新文本":
                    new_key = f"new_val_mcq_{col}"
                    if new_key not in st.session_state:
                        st.session_state[new_key] = ""
                    new_val = st.text_input(f"請輸入新的「{col}」:", key=new_key)
                    input_results_m[col] = new_val
                else:
                    input_results_m[col] = sel_val

        submit_col, note_col = st.columns([1, 1])
        with submit_col:
            submit_btn_m = st.button("📥 儲存設定", key=f"mcq_save_btn_{'_'.join(str(x) for x in sel_q_mcq)}")
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
            st.session_state["mcq_save_note"] = f"已為 {selected_display} 設定分類"
            st.session_state.mcq_clear_inputs = True
            st.rerun()

    df_mcq_display = df_mcq_c.copy()
    for col in st.session_state.mcq_custom_cols:
        df_mcq_display[col] = df_mcq_display["初始序列"].apply(lambda x: st.session_state.mcq_custom_values.get(x, {}).get(col, ""))

    st.markdown("---")
    st.info("Step 3：自訂分析重點（左右並排顯示）")

    col_attainment, col_expectation = st.columns(2)

    with col_attainment:
        st.subheader("1️⃣ 科本得分率分類")
        st.write("根據全港日校考生的平均正確率，將題目分為三個等級。")
        col_cut1, col_cut2 = st.columns(2)
        with col_cut1:
            st.session_state.mcq_cutoff_high = st.number_input(
                "高正確率分界值（%）：",
                min_value=0, max_value=100, value=st.session_state.mcq_cutoff_high, step=1,
                key="mcq_cutoff_high_input", help="高於此值為「High attainment」"
            )
        with col_cut2:
            st.session_state.mcq_cutoff_low = st.number_input(
                "低正確率分界值（%）：",
                min_value=0, max_value=100, value=st.session_state.mcq_cutoff_low, step=1,
                key="mcq_cutoff_low_input", help="低於此值為「Low attainment」，介乎之間為「Intermediate attainment」"
            )
        st.caption(f"分類設定：高≥{st.session_state.mcq_cutoff_high}% | 中{st.session_state.mcq_cutoff_low}%-{st.session_state.mcq_cutoff_high}% | 低≤{st.session_state.mcq_cutoff_low}%")

    with col_expectation:
        st.subheader("2️⃣ 校本預期平均得分率")
        st.write("設定本校學生在各類題目的預期正確率，用以判斷是否達到校本預期水平。")
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        with col_exp1:
            st.session_state.mcq_exp_high = st.number_input(
                "High attainment 題目的預期（%）：",
                min_value=0, max_value=100, value=st.session_state.mcq_exp_high, step=1,
                key="mcq_exp_high_input"
            )
        with col_exp2:
            st.session_state.mcq_exp_inter = st.number_input(
                "Intermediate attainment 題目的預期（%）：",
                min_value=0, max_value=100, value=st.session_state.mcq_exp_inter, step=1,
                key="mcq_exp_inter_input"
            )
        with col_exp3:
            st.session_state.mcq_exp_low = st.number_input(
                "Low attainment 題目的預期（%）：",
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

        return "Attained ✓" if your_rate_pct >= expected else "Below Expectation ✗"

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

    st.write("📊 **總覽表 (自動更新)：**")
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

    st.markdown("---")
    st.info("Step 4：篩選與高亮分析")

    f_cols_mcq = st.columns(max(len(st.session_state.mcq_custom_cols) + 2, 2))
    active_filters_mcq = {}
    for i, col in enumerate(st.session_state.mcq_custom_cols):
        with f_cols_mcq[i]:
            u_vals_mcq = [x for x in df_mcq_display[col].unique() if str(x).strip()]
            active_filters_mcq[col] = st.multiselect(f"篩選 {col}", u_vals_mcq, key=f"filter_mcq_{col}")
    
    with f_cols_mcq[len(st.session_state.mcq_custom_cols)]:
        attainment_vals_mcq = [x for x in df_mcq_display["Day School Attainment"].unique() if str(x).strip()]
        active_filters_mcq["Day School Attainment"] = st.multiselect("篩選 Day School Attainment", attainment_vals_mcq, key="filter_mcq_attainment")
    
    with f_cols_mcq[len(st.session_state.mcq_custom_cols) + 1]:
        expected_vals_mcq = [x for x in df_mcq_display["School-based Expected Attainment"].unique() if str(x).strip()]
        active_filters_mcq["School-based Expected Attainment"] = st.multiselect("篩選 School-based Expected Attainment", expected_vals_mcq, key="filter_mcq_expected")

    final_mcq_df = df_mcq_display.copy()
    for col, s_filters in active_filters_mcq.items():
        if s_filters:
            final_mcq_df = final_mcq_df[final_mcq_df[col].isin(s_filters)]

    st.markdown("""
    🔍 顏色說明：紅色 = 貴校最高選項既非正答亦不同於日校；黃色 = 非正答；藍色 = 與日校最高選項不同。
    """)
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
            .apply(style_mcq_row, axis=1)
            .apply(highlight_mcq_row, axis=1),
        use_container_width=True, hide_index=True
    )
else:
    st.error("找不到可用的 MCQ 分析資料。")

st.markdown("---")
