import pandas as pd
import streamlit as st

from pdf_utils import extract_item_analysis

st.set_page_config(page_title="Item Analysis", page_icon="📌", layout="wide")
st.title("📌 自訂項目分析 | Custom Item Analysis")
st.caption("此頁會讀取主頁已處理好的資料。| This page reads the processed data from the main page.")
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

st.page_link("app.py", label="返回主頁 | Back to Main Page", icon="⬅️")

if "processed_item_df" not in st.session_state or st.session_state.processed_item_df is None:
    source_pdf_bytes = st.session_state.get("source_pdf_bytes")
    if isinstance(source_pdf_bytes, (bytes, bytearray)) and source_pdf_bytes:
        st.session_state.processed_item_df = extract_item_analysis(source_pdf_bytes)

if "processed_item_df" not in st.session_state or st.session_state.processed_item_df is None:
    st.warning("未找到項目分析資料，請回到主頁完成上載。| No item analysis data found yet. Please upload your report in the main page.")
    st.stop()

df_item_c = st.session_state.processed_item_df.copy()
source_name = st.session_state.get("source_pdf_name", "未命名檔案")
st.success(f"已載入主頁資料：{source_name}")

if not df_item_c.empty:
    if "row_index" not in df_item_c.columns:
        df_item_c.insert(0, "row_index", range(1, len(df_item_c) + 1))
    if "題號" not in df_item_c.columns:
        df_item_c.insert(1, "題號", df_item_c.get("Item", range(1, len(df_item_c) + 1)))

    sel_q = None
    step1_col, step2_col = st.columns([1, 1])

    with step1_col:
        st.info("1️⃣ 建立自訂欄位 (最多 6 個) | Create Custom Fields (Maximum 6)")
        with st.form("item_add_field_form", clear_on_submit=True):
            new_col = st.text_input("輸入新自訂欄位名稱 | Enter New Custom Field Name", key="new_col_input_item")
            submitted = st.form_submit_button("➕ 新增欄位 | Add Field")
            if submitted:
                if new_col and new_col not in st.session_state.item_custom_cols and len(st.session_state.item_custom_cols) < 6:
                    st.session_state.item_custom_cols.append(new_col)
                    st.session_state.item_col_options_history[new_col] = []

        if st.session_state.item_custom_cols:
            st.success(f"已建立欄位 | Created Fields: {', '.join(st.session_state.item_custom_cols)}")

    with step2_col:
        st.info("2️⃣ 為各題設定分類 | Set Categories for Each Question")
        question_options = [f"{row['題號']} [{row['row_index']}]" for _, row in df_item_c.iterrows()]
        seq_map = {f"{row['題號']} [{row['row_index']}]": row['row_index'] for _, row in df_item_c.iterrows()}
        sel_qs_display = st.multiselect("選擇輸入類別的題號 | Select Questions to Add Categorie(s)", question_options, default=question_options[:1], key="item_q_sel")
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
            st.write(f"**正在編輯 | Editing: {selected_display}**")
            all_values = [st.session_state.item_custom_values.get(idx, {}) for idx in sel_qs]
            current_values = {}
            for col in st.session_state.item_custom_cols:
                values_for_col = {v.get(col, "") for v in all_values}
                current_values[col] = values_for_col.pop() if len(values_for_col) == 1 else ""
        else:
            st.warning("請先選擇至少一題。| Please select at least one question first.")
            current_values = {}

        input_results = {}
        for col in st.session_state.item_custom_cols:
            history_opts = st.session_state.item_col_options_history.get(col, [])
            options = [""] + history_opts + ["➕ 輸入新類別 | Enter a new category"]
            default_idx = 0
            curr_val = current_values.get(col, "")
            if curr_val in options:
                default_idx = options.index(curr_val)
            sel_col, new_col = st.columns([1, 1])
            with sel_col:
                sel_key = f"sel_item_{col}"
                sel_val = st.selectbox(f"{col}:", options=options, index=default_idx, key=sel_key)
            with new_col:
                if sel_val == "➕ 輸入新類別 | Enter a new category":
                    new_key = f"new_val_item_{col}"
                    if new_key not in st.session_state:
                        st.session_state[new_key] = ""
                    new_val = st.text_input(f"請輸入新的 「{col}」 | Enter new  {col}:", key=new_key)
                    input_results[col] = new_val
                else:
                    input_results[col] = sel_val

        submit_col, note_col = st.columns([1, 1])
        with submit_col:
            submit_btn = st.button("📥 儲存設定 | Save Settings", key=f"item_save_btn_{'_'.join(str(x) for x in sel_qs)}")
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
            st.session_state["item_save_note"] = f"已為以下題目設定分類 | Defined categories for questions: {selected_display}"
            st.session_state.item_clear_inputs = True
            st.rerun()

    st.markdown("---")
    st.info("3️⃣ 校本自訂分析 | School-based Customize Analysis")

    col_attainment, col_expectation = st.columns(2)

    with col_attainment:
        st.subheader("① 定義「平均得分率」的分類 | Define Level of Attainment")
        st.caption("此模組用於根據全港日校考生的平均得分率，將題目分為「高得分率（High attainment）」、「中等得分率（Intermediate attainment）」、「低得分率（Low attainment）」三個類別，亦即把學生在每題的表現分為「良好（Good）」、「中等（Intermediate）」及「未如理想（Poor）」。在設定上述三個類別的分界值時，可參考香港考試及評核局於該年發布的HKDSE評核資訊及分析資料1，或按該學科的情況作專業判斷。")
        col_cut1, col_cut2 = st.columns(2)
        with col_cut1:
            st.session_state.item_cutoff_high = st.number_input(
                "高／中得分率分界值（%）| High/Intermediate attainment Cutoff:",
                min_value=0, max_value=100, value=st.session_state.item_cutoff_high, step=1,
                key="item_cutoff_high_input", help="日校得分率高於此值，即視為「高得分率」 | Day school Mean % above this value are classified as 'High attainment'."
            )
        with col_cut2:
            st.session_state.item_cutoff_low = st.number_input(
                "中／低得分率分界值（%）| Intermediate/Low attainment Cutoff:",
                min_value=0, max_value=100, value=st.session_state.item_cutoff_low, step=1,
                key="item_cutoff_low_input", help="日校得分率低於此值，即視為「低得分率」 | Day school Mean % below this value are classified as 'Low attainment'."
            )
        st.markdown(f"""
                   題目得分率設定：高得分率 ≥{st.session_state.item_cutoff_high}% | 中得分率 {st.session_state.item_cutoff_low}%-{st.session_state.item_cutoff_high}% | 低得分率 ≤{st.session_state.item_cutoff_low}%
                   
                   Question Attainment Levels: High attainment ≥{st.session_state.item_cutoff_high}% | Intermediate attainment {st.session_state.item_cutoff_low}% - {st.session_state.item_cutoff_high}% | Low attainment ≤{st.session_state.item_cutoff_low}%
                   """)

    with col_expectation:
        st.subheader("② 校本預期平均得分率 | Define School-based Expected Attainment")
        st.caption("在設定「全港日校考生的平均得分率」的類別後，此模組讓學校按校本情況進一步設定學生在高、中、低得分率題目的「校本預期平均得分率」，例如是與全港水平一致、較高或較低，以協助分析該校學生在各題中的表現是否達到校本的預期水平。（此「預期平均得分率」即校本的「底線」，當學生在某題的表現低於這條底線時，便代表需要注意及跟進）。")
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        with col_exp1:
            st.session_state.item_exp_high = st.number_input(
                "預期高得分率題目得分率（%）| Expected for High attainment questions:",
                min_value=0, max_value=100, value=st.session_state.item_exp_high, step=1,
                key="item_exp_high_input"
            )
        with col_exp2:
            st.session_state.item_exp_inter = st.number_input(
                "預期中等得分率題目得分率（%）| Expected for Intermediate attainment questions:",
                min_value=0, max_value=100, value=st.session_state.item_exp_inter, step=1,
                key="item_exp_inter_input"
            )
        with col_exp3:
            st.session_state.item_exp_low = st.number_input(
                "預期低得分率題目得分率（%）| Expected for Low attainment questions:",
                min_value=0, max_value=100, value=st.session_state.item_exp_low, step=1,
                key="item_exp_low_input"
            )

    st.markdown("---")

    df_display = df_item_c.copy()
    for col in st.session_state.item_custom_cols:
        df_display[col] = df_display["row_index"].apply(lambda x: st.session_state.item_custom_values.get(x, {}).get(col, ""))

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

        return "Attained" if your_rate_pct >= expected else "Below Expectation"

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

    st.write("📊 **總覽表 (本表跟隨以上設定自動更新) | Overview Table (This table updates automatically based on the above settings)**")
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
    st.info("4️⃣ 篩選與排序分析 | Filter and Sort Analysis")

    f_cols = st.columns(max(len(st.session_state.item_custom_cols) + 2, 2))
    active_filters = {}
    for i, col in enumerate(st.session_state.item_custom_cols):
        with f_cols[i]:
            u_vals = [x for x in df_display[col].unique() if str(x).strip()]
            active_filters[col] = st.multiselect(f"{col}", u_vals, key=f"filter_item_{col}")
    
    with f_cols[len(st.session_state.item_custom_cols)]:
        attainment_vals = [x for x in df_display["Day School Attainment"].unique() if str(x).strip()]
        active_filters["Day School Attainment"] = st.multiselect("Day School Attainment", attainment_vals, key="filter_item_attainment")
    
    with f_cols[len(st.session_state.item_custom_cols) + 1]:
        expected_vals = [x for x in df_display["School-based Expected Attainment"].unique() if str(x).strip()]
        active_filters["School-based Expected Attainment"] = st.multiselect("School-based Expected Attainment", expected_vals, key="filter_item_expected")

    c4, c5 = st.columns([2, 1])
    with c4:
        sort_by = st.selectbox("排序", ["按題號 | by Question Number", "Your school Mean %", "Day schools Mean %", "Day School Attainment", "School-based Expected Attainment"], key="sort_item")
    with c5:
        sort_order = st.radio("排序方式", ["由高至低 | Highest to Lowest", "由低至高 | Lowest to Highest"], horizontal=True, key="order_item")

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
    st.error("找不到可用的項目分析資料。 | No item analysis data available.")

st.markdown("---")
