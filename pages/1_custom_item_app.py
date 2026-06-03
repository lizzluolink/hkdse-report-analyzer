import pandas as pd
import streamlit as st

from pdf_utils import extract_item_analysis

st.set_page_config(page_title="Item Analysis", page_icon="📌", layout="wide")
st.title("📌 自定義項目分析 app")
st.caption("此頁會讀取主 app 已處理好的資料。請先回主 app 上載 PDF，並按『處理檔案並啟用自定義分析 app』。")

if "item_custom_cols" not in st.session_state:
    st.session_state.item_custom_cols = []
if "item_col_options_history" not in st.session_state:
    st.session_state.item_col_options_history = {}
if "item_custom_values" not in st.session_state:
    st.session_state.item_custom_values = {}
if "mcq_custom_values" not in st.session_state:
    st.session_state.mcq_custom_values = {}
if "item_clear_inputs" not in st.session_state:
    st.session_state.item_clear_inputs = False
if "item_save_note" not in st.session_state:
    st.session_state.item_save_note = ""
if "item_cutoff_high" not in st.session_state:
    st.session_state.item_cutoff_high = 70
if "item_cutoff_low" not in st.session_state:
    st.session_state.item_cutoff_low = 30
if "item_exp_high" not in st.session_state:
    st.session_state.item_exp_high = 80
if "item_exp_inter" not in st.session_state:
    st.session_state.item_exp_inter = 60
if "item_exp_low" not in st.session_state:
    st.session_state.item_exp_low = 40

st.page_link("app.py", label="⬅️ 返回主 app", icon="⬅️")

if "processed_item_df" not in st.session_state or st.session_state.processed_item_df is None:
    source_pdf_bytes = st.session_state.get("source_pdf_bytes")
    if isinstance(source_pdf_bytes, (bytes, bytearray)) and source_pdf_bytes:
        st.session_state.processed_item_df = extract_item_analysis(source_pdf_bytes)

if "processed_item_df" not in st.session_state or st.session_state.processed_item_df is None:
    st.warning("尚未找到已處理好的項目分析資料。請先回主 app 完成前處理。")
    st.stop()

df_item_c = st.session_state.processed_item_df.copy()
source_name = st.session_state.get("source_pdf_name", "未命名檔案")
st.success(f"已載入主 app 處理完成的資料：{source_name}")

if not df_item_c.empty:
    if "初始序列" not in df_item_c.columns:
        df_item_c.insert(0, "初始序列", range(1, len(df_item_c) + 1))
    if "題號" not in df_item_c.columns:
        df_item_c.insert(1, "題號", df_item_c.get("Item", range(1, len(df_item_c) + 1)))

    sel_q = None
    step1_col, step2_col = st.columns([1, 1])

    with step1_col:
        st.info("Step 1：建立自定義欄位 (最多 6 個)")
        with st.form("item_add_field_form", clear_on_submit=True):
            new_col = st.text_input("輸入新自定義欄位名稱：", key="new_col_input_item")
            submitted = st.form_submit_button("➕ 新增欄位")
            if submitted:
                if new_col and new_col not in st.session_state.item_custom_cols and len(st.session_state.item_custom_cols) < 6:
                    st.session_state.item_custom_cols.append(new_col)
                    st.session_state.item_col_options_history[new_col] = []

        if st.session_state.item_custom_cols:
            st.success(f"目前建立的欄位：{', '.join(st.session_state.item_custom_cols)}")

    with step2_col:
        st.info("Step 2：為每一題設定分類 (下拉聯想與新增)")
        question_options = [f"{row['題號']} [{row['初始序列']}]" for _, row in df_item_c.iterrows()]
        seq_map = {f"{row['題號']} [{row['初始序列']}]": row['初始序列'] for _, row in df_item_c.iterrows()}
        sel_qs_display = st.multiselect("選擇要輸入標籤的題號：", question_options, default=question_options[:1], key="item_q_sel")
        sel_qs = [seq_map[q] for q in sel_qs_display]

        if st.session_state.item_clear_inputs:
            for col in st.session_state.item_custom_cols:
                sel_key = f"sel_item_{col}"
                new_key = f"new_val_item_{col}"
                st.session_state[sel_key] = ""
                st.session_state[new_key] = ""
            st.session_state.item_clear_inputs = False

        if sel_qs_display:
            selected_display = ", ".join(sel_qs_display)
            st.write(f"**正在編輯：{selected_display}**")
            all_values = [st.session_state.item_custom_values.get(idx, {}) for idx in sel_qs]
            current_values = {}
            for col in st.session_state.item_custom_cols:
                values_for_col = {v.get(col, "") for v in all_values}
                current_values[col] = values_for_col.pop() if len(values_for_col) == 1 else ""
        else:
            st.warning("請先選擇至少一題。")
            current_values = {}

        input_results = {}
        for col in st.session_state.item_custom_cols:
            history_opts = st.session_state.item_col_options_history.get(col, [])
            options = [""] + history_opts + ["輸入新文本"]
            default_idx = 0
            curr_val = current_values.get(col, "")
            if curr_val in options:
                default_idx = options.index(curr_val)
            sel_col, new_col = st.columns([1, 1])
            with sel_col:
                sel_key = f"sel_item_{col}"
                sel_val = st.selectbox(f"{col}:", options=options, index=default_idx, key=sel_key)
            with new_col:
                if sel_val == "輸入新文本":
                    new_key = f"new_val_item_{col}"
                    if new_key not in st.session_state:
                        st.session_state[new_key] = ""
                    new_val = st.text_input(f"請輸入新的「{col}」:", key=new_key)
                    input_results[col] = new_val
                else:
                    input_results[col] = sel_val

        submit_col, note_col = st.columns([1, 1])
        with submit_col:
            submit_btn = st.button("📥 儲存設定", key=f"item_save_btn_{'_'.join(str(x) for x in sel_qs)}")
        save_note = note_col.empty()
        if st.session_state.item_save_note:
            save_note.caption(st.session_state.item_save_note)

        if submit_btn and sel_qs:
            for idx in sel_qs:
                if idx not in st.session_state.item_custom_values:
                    st.session_state.item_custom_values[idx] = {}
                for col, val in input_results.items():
                    if val:
                        st.session_state.item_custom_values[idx][col] = val
                        if val not in st.session_state.item_col_options_history[col]:
                            st.session_state.item_col_options_history[col].append(val)
            st.session_state["item_last_saved_q"] = sel_qs
            st.session_state["item_save_note"] = f"已為 {selected_display} 設定分類"
            st.session_state.item_clear_inputs = True
            st.rerun()

    st.markdown("---")
    st.info("Step 3：自訂分析重點（左右並排顯示）")

    col_attainment, col_expectation = st.columns(2)

    with col_attainment:
        st.subheader("1️⃣ 科本得分率分類")
        st.write("根據全港日校考生的平均得分率，將題目分為三個等級。")
        col_cut1, col_cut2 = st.columns(2)
        with col_cut1:
            st.session_state.item_cutoff_high = st.number_input(
                "高得分率分界值（%）：",
                min_value=0, max_value=100, value=st.session_state.item_cutoff_high, step=1,
                key="item_cutoff_high_input", help="高於此值為「High attainment」"
            )
        with col_cut2:
            st.session_state.item_cutoff_low = st.number_input(
                "低得分率分界值（%）：",
                min_value=0, max_value=100, value=st.session_state.item_cutoff_low, step=1,
                key="item_cutoff_low_input", help="低於此值為「Low attainment」，介乎之間為「Intermediate attainment」"
            )
        st.caption(f"分類設定：高≥{st.session_state.item_cutoff_high}% | 中{st.session_state.item_cutoff_low}%-{st.session_state.item_cutoff_high}% | 低≤{st.session_state.item_cutoff_low}%")

    with col_expectation:
        st.subheader("2️⃣ 校本預期平均得分率")
        st.write("設定本校學生在各類題目的預期得分率，用以判斷是否達到校本預期水平。")
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        with col_exp1:
            st.session_state.item_exp_high = st.number_input(
                "High attainment 題目的預期（%）：",
                min_value=0, max_value=100, value=st.session_state.item_exp_high, step=1,
                key="item_exp_high_input"
            )
        with col_exp2:
            st.session_state.item_exp_inter = st.number_input(
                "Intermediate attainment 題目的預期（%）：",
                min_value=0, max_value=100, value=st.session_state.item_exp_inter, step=1,
                key="item_exp_inter_input"
            )
        with col_exp3:
            st.session_state.item_exp_low = st.number_input(
                "Low attainment 題目的預期（%）：",
                min_value=0, max_value=100, value=st.session_state.item_exp_low, step=1,
                key="item_exp_low_input"
            )

    st.markdown("---")

    df_display = df_item_c.copy()
    for col in st.session_state.item_custom_cols:
        df_display[col] = df_display["初始序列"].apply(lambda x: st.session_state.item_custom_values.get(x, {}).get(col, ""))

    # 計算 Day School Attainment
    def get_attainment(rate):
        rate_pct = rate * 100 if rate <= 1 else rate
        if rate_pct >= st.session_state.item_cutoff_high:
            return "High attainment"
        elif rate_pct <= st.session_state.item_cutoff_low:
            return "Low attainment"
        else:
            return "Intermediate attainment"

    df_display["Day School Attainment"] = df_display["Day schools Mean %"].apply(get_attainment)

    # 計算 School-based Expected Attainment
    def get_expected_status(row):
        attainment = row["Day School Attainment"]
        your_rate = row["Your school Mean %"]
        your_rate_pct = your_rate * 100 if your_rate <= 1 else your_rate

        if attainment == "High attainment":
            expected = st.session_state.item_exp_high
        elif attainment == "Intermediate attainment":
            expected = st.session_state.item_exp_inter
        else:  # Low attainment
            expected = st.session_state.item_exp_low

        return "Attained ✓" if your_rate_pct >= expected else "Below Expectation ✗"

    df_display["School-based Expected Attainment"] = df_display.apply(get_expected_status, axis=1)

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

    st.write("📊 **總覽表 (自動更新)：**")
    st.dataframe(
        df_display.style
            .format({
                "Your school Attem. %": "{:.1f}",
                "Your school Mean": "{:.1f}",
                "Your school Mean %": "{:.1%}",
                "Your school SD": "{:.1f}",
                "Day schools Attem. %": "{:.1f}",
                "Day schools Mean": "{:.1f}",
                "Day schools Mean %": "{:.1%}",
                "Day schools SD": "{:.1f}"
            })
            .apply(
                lambda col: col.map(status_cell_style),
                subset=["Day School Attainment", "School-based Expected Attainment"],
                axis=0
            ),
        use_container_width=True, hide_index=True
    )

    st.markdown("---")
    st.info("Step 4：篩選與排序結果")

    f_cols = st.columns(max(len(st.session_state.item_custom_cols) + 2, 2))
    active_filters = {}
    for i, col in enumerate(st.session_state.item_custom_cols):
        with f_cols[i]:
            u_vals = [x for x in df_display[col].unique() if str(x).strip()]
            active_filters[col] = st.multiselect(f"篩選 {col}", u_vals, key=f"filter_item_{col}")
    
    with f_cols[len(st.session_state.item_custom_cols)]:
        attainment_vals = [x for x in df_display["Day School Attainment"].unique() if str(x).strip()]
        active_filters["Day School Attainment"] = st.multiselect("篩選 Day School Attainment", attainment_vals, key="filter_item_attainment")
    
    with f_cols[len(st.session_state.item_custom_cols) + 1]:
        expected_vals = [x for x in df_display["School-based Expected Attainment"].unique() if str(x).strip()]
        active_filters["School-based Expected Attainment"] = st.multiselect("篩選 School-based Expected Attainment", expected_vals, key="filter_item_expected")

    c4, c5 = st.columns([2, 1])
    with c4:
        sort_by = st.selectbox("排序依據", ["預設（按題號）", "Your school Mean %", "Day schools Mean %", "Day School Attainment", "School-based Expected Attainment"], key="sort_item")
    with c5:
        sort_order = st.radio("排序方式", ["由高至低", "由低至高"], horizontal=True, key="order_item")

    final_df = df_display.copy()
    for col, s_filters in active_filters.items():
        if s_filters:
            final_df = final_df[final_df[col].isin(s_filters)]

    if sort_by != "預設（按題號）":
        try:
            final_df[sort_by] = pd.to_numeric(final_df[sort_by], errors='coerce')
            final_df = final_df.sort_values(sort_by, ascending=(sort_order == "由低至高"))
        except:
            pass

    st.dataframe(
        final_df.style
            .format({
                "Your school Attem. %": "{:.1f}",
                "Your school Mean": "{:.1f}",
                "Your school Mean %": "{:.1%}",
                "Your school SD": "{:.1f}",
                "Day schools Attem. %": "{:.1f}",
                "Day schools Mean": "{:.1f}",
                "Day schools Mean %": "{:.1%}",
                "Day schools SD": "{:.1f}"
            })
            .apply(
                lambda col: col.map(status_cell_style),
                subset=["Day School Attainment", "School-based Expected Attainment"],
                axis=0
            ),
        use_container_width=True, hide_index=True
    )
else:
    st.error("找不到可用的項目分析資料。")

st.markdown("---")
