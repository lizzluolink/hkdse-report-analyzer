# HKDSE Report Analyzer

HKDSE Report Analyzer 是一個基於 Streamlit 的工具，用於從 HKDSE 統計 PDF 報告中提取並分析數據。它支援自動提取總數表、項目分析和多項選擇題分析，並提供自訂標籤與排序功能，便於校本分析。

HKDSE Report Analyzer is a Streamlit-based tool for extracting and analyzing data from HKDSE statistical PDF reports. It supports automatic extraction of summary tables, item-level analysis, and multiple-choice question (MCQ) analysis, and includes custom tagging and sorting workflows for deeper school-based analysis.

## 功能特色 Features

- 📂 自動 PDF 上載與資料提取 / Automatic PDF upload and extraction
- 📊 總數表提取，並搭配圖表與百分比比較 / Total Table extraction with charts and percentage comparison
- 📝 項目分析提取，支援自訂欄位與排序篩選 / Item Analysis extraction with custom field labeling and sorted filtering
- ✅ 多項選擇題分析提取，支援正確答案檢測與自訂標籤 / MCQ Analysis extraction with correct answer detection and custom tagging
- 📥 下載 Excel 檔案 / Download extracted data as Excel files
- 🌐 中英雙語介面 / Bilingual UI support (中文 / English)
- 🔄 上傳新 PDF 自動刷新 / Auto-refresh when a new PDF is uploaded

## 支援流程 Supported workflows

### 1. 上載 HKDSE PDF 報告 Upload HKDSE PDF report
在主頁上傳 PDF 報告，工具會自動提取：
- 總數表數據 / Total Table data
- 項目分析數據 / Item Analysis data
- 多項選擇題分析數據 / MCQ Analysis data

### 2. 查看提取狀態 View extraction status
上傳後，主頁會顯示三條獨立狀態訊息：
- 總數表提取 / Total Table extraction
- 項目分析提取 / Item Analysis extraction
- 多項選擇題提取 / MCQ Analysis extraction

### 3. 總數表頁 Total Table tab
本頁會提取最新年份的總數分佈，並顯示：
- 提取的表格預覽 / extracted table preview
- 貴校與日校比較柱狀圖 / bar chart comparison between Your school and Day schools
- 轉置摘要表 / pivot-style summary report

### 4. 自訂項目分析頁 Custom Item Analysis tab
此頁用於項目層級數據處理與標記：
- 建立最多 8 個自訂欄位 / custom fields creation (maximum 8 fields)
- 以 `題號` 選取題目 / select questions by `題號`
- 為題目分配分類標籤 / assign categories for each question
- 篩選與排序 / filters and sorting by selected columns

### 5. 自訂多項選擇題分析頁 Custom MCQ Analysis tab
此頁用於 MCQ 層級數據處理與標記：
- 建立最多 8 個自訂欄位 / custom fields creation (maximum 8 fields)
- 以 `題號` 選取題目 / select questions by `題號`
- 為題目分配分類標籤 / assign categories for each question
- 根據 MCQ 指標與校本期望排序 / filter and sort by MCQ metrics and school attainment

## 安裝 Installation

1. 下載專案 / Clone the repository：

```bash
git clone https://github.com/lizz-luo/hkdse-report-analyzer-2.git
cd hkdse-report-analyzer-2
```

2. 安裝 Python 依賴 / Install Python dependencies：

```bash
pip install -r requirements.txt
```

## 啟動應用 Run the app

使用以下指令啟動 Streamlit：

```bash
streamlit run app.py
```

然後在瀏覽器中開啟顯示的 URL。

## 專案結構 Repository structure

- `app.py` — 主頁 Streamlit 應用，負責全局上傳與資料預覽 / main Streamlit app and global upload/preview UI
- `pdf_utils.py` — PDF 解析與數據提取工具 / PDF parsing and data extraction helpers
- `pages/1_custom_item_app.py` — 自訂項目分析頁面 / custom item analysis page
- `pages/2_custom_mcq_app.py` — 自訂 MCQ 分析頁面 / custom MCQ analysis page
- `requirements.txt` — 需要的 Python 套件 / required Python packages

## 注意事項 Notes

- 工具以 PDF 文字提取為基礎，因此最適合格式符合預期的 HKDSE 報告。/ The tool relies on PDF text extraction heuristics, so it works best with HKDSE reports that follow the expected formatting.
- `Item Analysis` 和 `MCQ Analysis` 分頁使用 `session_state` 儲存已提取資料，方便跨頁使用。/ `Item Analysis` and `MCQ Analysis` workspaces use session state to keep extracted data available across pages.

## 建議操作 Recommended usage

1. 在主頁上傳有效的 HKDSE PDF 報告。/ Upload a valid HKDSE PDF report on the main page.
2. 查看三條提取狀態訊息。/ Check the extraction status messages.
3. 預覽總數、項目和 MCQ 表格。/ Preview the Total, Item, and MCQ tables.
4. 如需匯出，下載 Excel 檔案；如需進一步分析，前往自訂分析頁面。/ Download Excel exports or proceed to custom analysis pages.
5. 建立最多 8 個自訂標籤，為選定題目分配分類，並進行篩選及排序。/ Create up to 8 custom labels, assign them to selected questions, then filter and sort the results.

---

