"""
survey_app.py — Research Survey Platform
Streamlit application for:
  - Delivering questionnaires to respondents (online or local)
  - Collecting and storing responses as CSV
  - Admin dashboard with descriptive stats, reliability (Cronbach's α), and charts
  - Uploading a new DOCX questionnaire to auto-generate a new config

Run locally:
    streamlit run survey_app.py

Deploy for a public link:
    Push this folder to GitHub → connect to https://streamlit.io/cloud → deploy
"""

import csv
import json
import math
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# ─── PATHS ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "survey_config.json")
DATA_FILE   = os.path.join(BASE_DIR, "responses.csv")


# ─── CONFIG HELPERS ───────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_config() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    st.cache_data.clear()


# ─── RESPONSE HELPERS ─────────────────────────────────────────────────────────
def get_all_columns(cfg: dict) -> list:
    """Return ordered list of ALL CSV column names from config."""
    cols = ["timestamp"]
    for q in cfg["demographic_section"]["questions"]:
        cols.append(q["variable"])
        if q.get("has_other"):
            cols.append(f"{q['variable']}_other")
    for section in cfg["likert_sections"]:
        for q in section["questions"]:
            cols.append(f"{section['variable_prefix']}{q['number']}")
    return cols


def save_response(row: dict, cfg: dict) -> None:
    """Append one response row to the CSV file with all columns guaranteed."""
    all_cols = get_all_columns(cfg)
    file_exists = os.path.exists(DATA_FILE)
    with open(DATA_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=all_cols, extrasaction="ignore", restval=""
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


@st.cache_data(ttl=10)
def load_responses() -> pd.DataFrame:
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()
    return pd.read_csv(DATA_FILE, encoding="utf-8-sig")


# ─── STATS HELPERS ────────────────────────────────────────────────────────────
def cronbach_alpha(df_items: pd.DataFrame) -> float:
    """Compute Cronbach's alpha for a construct's item columns."""
    df_clean = df_items.apply(pd.to_numeric, errors="coerce").dropna()
    n_obs, n_items = df_clean.shape
    if n_obs < 2 or n_items < 2:
        return float("nan")
    item_vars = df_clean.var(axis=0, ddof=1)
    total_var = df_clean.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return float("nan")
    return round((n_items / (n_items - 1)) * (1 - item_vars.sum() / total_var), 3)


def alpha_label(alpha: float) -> str:
    if math.isnan(alpha):
        return "N/A"
    if alpha >= 0.9:
        return f"{alpha:.3f} ✅ Xuất sắc"
    if alpha >= 0.8:
        return f"{alpha:.3f} ✅ Tốt"
    if alpha >= 0.7:
        return f"{alpha:.3f} ⚠️ Chấp nhận được"
    if alpha >= 0.6:
        return f"{alpha:.3f} ⚠️ Yếu"
    return f"{alpha:.3f} ❌ Không chấp nhận"


# ─── PAGE: SURVEY ─────────────────────────────────────────────────────────────
def render_survey(cfg: dict) -> None:
    meta = cfg["survey_meta"]

    # Header
    st.markdown(
        f"<h1 style='text-align:center'>{meta['title']}</h1>",
        unsafe_allow_html=True,
    )
    if meta.get("subtitle"):
        st.markdown(
            f"<p style='text-align:center;color:#666;font-style:italic'>{meta['subtitle']}</p>",
            unsafe_allow_html=True,
        )
    st.markdown("---")

    # Intro box
    if meta.get("intro_text"):
        st.info(meta["intro_text"].replace("\\n", "\n"))

    st.markdown("---")

    with st.form("survey_form", clear_on_submit=False):
        responses: dict = {}

        # ── DEMOGRAPHICS ──────────────────────────────────────────────────────
        demo = cfg["demographic_section"]
        st.subheader(demo["title"])
        st.caption("Vui lòng chọn đáp án phù hợp nhất với Quý Ông/Bà.")

        for q in demo["questions"]:
            v   = q["variable"]
            lbl = f"**{q['number']}. {q['text']}**"

            if q["type"] == "radio":
                chosen = st.radio(lbl, q["options"], index=None, key=v)
                if chosen is None:
                    responses[v] = None
                else:
                    responses[v] = q["coding"].get(chosen, chosen)

                # Conditional "Khác" text input
                if q.get("has_other"):
                    other_key = f"{v}_other"
                    if chosen == q["options"][-1]:
                        responses[other_key] = st.text_input(
                            "↳ Vui lòng ghi rõ:", key=other_key, placeholder="Nhập ngành nghề..."
                        )
                    else:
                        responses[other_key] = ""

            elif q["type"] == "text":
                responses[v] = st.text_input(lbl, key=v)

            st.markdown("")  # spacer

        st.markdown("---")

        # ── LIKERT SECTIONS ───────────────────────────────────────────────────
        for section in cfg["likert_sections"]:
            st.subheader(section["title"])
            if section.get("description"):
                st.caption(section["description"])

            sl = section["scale_labels"]
            st.markdown(
                f"<div style='background:#f0f2f6;border-radius:8px;padding:8px 16px;"
                f"margin-bottom:12px;font-size:13px'>"
                f"<b>Thang đo:</b> &nbsp;"
                f"<b>1</b> = {sl[0]} &nbsp;|&nbsp; "
                f"<b>2</b> = {sl[1]} &nbsp;|&nbsp; "
                f"<b>3</b> = {sl[2]} &nbsp;|&nbsp; "
                f"<b>4</b> = {sl[3]} &nbsp;|&nbsp; "
                f"<b>5</b> = {sl[4]}"
                f"</div>",
                unsafe_allow_html=True,
            )

            for q in section["questions"]:
                var    = f"{section['variable_prefix']}{q['number']}"
                c_text, c_rating = st.columns([3, 2])
                c_text.markdown(f"**{q['number']}.** {q['text']}")
                with c_rating:
                    val = st.radio(
                        "Chọn:",
                        options=[1, 2, 3, 4, 5],
                        format_func=lambda x: str(x),
                        key=var,
                        horizontal=True,
                        label_visibility="collapsed",
                        index=None,
                    )
                responses[var] = val

            st.markdown("---")

        # ── SUBMIT BUTTON ─────────────────────────────────────────────────────
        col_btn, _ = st.columns([1, 2])
        submitted = col_btn.form_submit_button(
            "✅  Gửi khảo sát", type="primary", use_container_width=True
        )

        if submitted:
            # Build human-readable labels for missing questions
            missing_items = []

            for q in cfg["demographic_section"]["questions"]:
                if q["type"] == "radio" and responses.get(q["variable"]) is None:
                    missing_items.append(
                        f"📌 **[Thông tin đáp viên]** Câu {q['number']}: {q['text']}"
                    )

            for s in cfg["likert_sections"]:
                for q in s["questions"]:
                    var = f"{s['variable_prefix']}{q['number']}"
                    if responses.get(var) is None:
                        missing_items.append(
                            f"📌 **[{s['id']}]** Câu {q['number']}: {q['text'][:80]}{'...' if len(q['text']) > 80 else ''}"
                        )

            if missing_items:
                st.warning(
                    f"⚠️ Còn **{len(missing_items)}** câu hỏi chưa được trả lời. "
                    f"Vui lòng bổ sung trước khi gửi:\n\n"
                    + "\n".join(f"- {item}" for item in missing_items)
                )
            else:
                row = {"timestamp": datetime.now().isoformat(), **responses}
                save_response(row, cfg)
                st.success(
                    "🎉 **Cảm ơn Quý Ông/Bà đã tham gia khảo sát!**\n\n"
                    "Phản hồi của Quý Ông/Bà đã được ghi nhận thành công."
                )
                st.balloons()


# ─── PAGE: ANALYSIS ───────────────────────────────────────────────────────────
def render_analysis(cfg: dict) -> None:
    st.title("📊 Bảng phân tích dữ liệu")

    # ── Admin auth ────────────────────────────────────────────────────────────
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    if not st.session_state.admin_ok:
        with st.form("login_form"):
            st.markdown("### 🔐 Đăng nhập quản trị")
            pw = st.text_input("Mật khẩu:", type="password")
            if st.form_submit_button("Đăng nhập"):
                if pw == cfg["survey_meta"].get("admin_password", "admin123"):
                    st.session_state.admin_ok = True
                    st.rerun()
                else:
                    st.error("Sai mật khẩu!")
        return

    if st.button("🚪 Đăng xuất"):
        st.session_state.admin_ok = False
        st.rerun()

    # ── Load data ─────────────────────────────────────────────────────────────
    df = load_responses()
    if df.empty:
        st.warning("⚠️ Chưa có phản hồi nào trong hệ thống.")
        return

    n = len(df)
    constructs = cfg["likert_sections"]

    # ── Top metrics ───────────────────────────────────────────────────────────
    all_likert_cols = [
        f"{s['variable_prefix']}{q['number']}"
        for s in constructs
        for q in s["questions"]
        if f"{s['variable_prefix']}{q['number']}" in df.columns
    ]
    overall = df[all_likert_cols].apply(pd.to_numeric, errors="coerce").stack().mean() if all_likert_cols else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng số phản hồi", n)
    c2.metric("Mean tổng thể (Likert)", f"{overall:.2f} / 5.00")
    c3.metric("Số câu hỏi Likert", len(all_likert_cols))

    # ── Download ──────────────────────────────────────────────────────────────
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️  Tải xuống dữ liệu (CSV)",
        data=csv_bytes,
        file_name=f"survey_data_{datetime.now():%Y%m%d_%H%M%S}.csv",
        mime="text/csv",
    )
    st.markdown("---")

    # ── TAB LAYOUT ────────────────────────────────────────────────────────────
    tab_constructs, tab_corr, tab_demo, tab_raw = st.tabs(
        ["🔍 Nhân tố", "📐 Tương quan", "👥 Đặc điểm đáp viên", "📄 Dữ liệu thô"]
    )

    # ──────────────────────────────────────────────────────────────────────────
    with tab_constructs:
        st.subheader("Độ tin cậy & thống kê mô tả theo nhân tố")

        summary_rows = []
        for section in constructs:
            prefix = section["variable_prefix"]
            cols   = [
                f"{prefix}{q['number']}"
                for q in section["questions"]
                if f"{prefix}{q['number']}" in df.columns
            ]
            if not cols:
                continue

            subset = df[cols].apply(pd.to_numeric, errors="coerce")
            alpha  = cronbach_alpha(subset)
            c_mean = subset.values.mean()
            c_std  = subset.stack().std()
            summary_rows.append({
                "Nhân tố": section["short_title"],
                "Mã": section["id"],
                "Items": len(cols),
                "Mean": round(c_mean, 3),
                "Std": round(c_std, 3),
                "Min": int(subset.min().min()),
                "Max": int(subset.max().max()),
                "Cronbach α": alpha_label(alpha),
            })

            alpha_display = f"{alpha:.3f}" if not math.isnan(alpha) else "N/A"
            with st.expander(
                f"**{section['id']}** — {section['short_title']} "
                f"(α = {alpha_display}, Mean = {c_mean:.2f})"
            ):
                # Item-level bar chart
                item_labels = [
                    f"{prefix}{q['number']}: {q['text'][:55]}..."
                    if len(q["text"]) > 55 else f"{prefix}{q['number']}: {q['text']}"
                    for q in section["questions"]
                    if f"{prefix}{q['number']}" in df.columns
                ]
                item_means = subset.mean().values
                fig = px.bar(
                    x=item_means,
                    y=item_labels,
                    orientation="h",
                    range_x=[1, 5],
                    labels={"x": "Mean", "y": ""},
                    color=item_means,
                    color_continuous_scale="Blues",
                    title=f"Mean từng câu hỏi — {section['id']}",
                )
                fig.update_layout(showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)

                # Descriptive stats table
                desc = subset.describe().round(3)
                desc.columns = [
                    f"{prefix}{q['number']}"
                    for q in section["questions"]
                    if f"{prefix}{q['number']}" in df.columns
                ]
                st.dataframe(desc, use_container_width=True)

        if summary_rows:
            st.markdown("#### Tóm tắt tất cả nhân tố")
            st.dataframe(
                pd.DataFrame(summary_rows),
                use_container_width=True,
                hide_index=True,
            )

    # ──────────────────────────────────────────────────────────────────────────
    with tab_corr:
        st.subheader("Ma trận tương quan giữa các nhân tố (Construct means)")

        construct_scores = {}
        for section in constructs:
            prefix = section["variable_prefix"]
            cols   = [
                f"{prefix}{q['number']}"
                for q in section["questions"]
                if f"{prefix}{q['number']}" in df.columns
            ]
            if cols:
                construct_scores[section["id"]] = (
                    df[cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
                )

        if construct_scores:
            corr_df = pd.DataFrame(construct_scores).corr().round(3)
            fig_corr = px.imshow(
                corr_df,
                text_auto=True,
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1,
                title="Construct Correlation Matrix",
            )
            st.plotly_chart(fig_corr, use_container_width=True)
            st.dataframe(corr_df, use_container_width=True)

    # ──────────────────────────────────────────────────────────────────────────
    with tab_demo:
        st.subheader("Phân bố đặc điểm đáp viên")
        demo_qs = cfg["demographic_section"]["questions"]

        col_left, col_right = st.columns(2)
        for idx, q in enumerate(demo_qs):
            v = q["variable"]
            if v not in df.columns or q["type"] != "radio":
                continue

            reverse_coding = {str(code): label for label, code in q["coding"].items()}
            counts = (
                df[v]
                .astype(str)
                .map(reverse_coding)
                .value_counts()
                .reset_index()
            )
            counts.columns = ["Lựa chọn", "Số lượng"]

            fig_d = px.bar(
                counts,
                x="Số lượng",
                y="Lựa chọn",
                orientation="h",
                title=f"{q['number']}. {q['text']}",
                text_auto=True,
            )
            fig_d.update_layout(yaxis={"categoryorder": "total ascending"})

            target_col = col_left if idx % 2 == 0 else col_right
            with target_col:
                st.plotly_chart(fig_d, use_container_width=True)

    # ──────────────────────────────────────────────────────────────────────────
    with tab_raw:
        st.subheader("Dữ liệu thô")
        st.dataframe(df, use_container_width=True)
        st.caption(f"Tổng cộng: {n} hàng × {len(df.columns)} cột")


# ─── PAGE: UPLOAD / MANAGE ────────────────────────────────────────────────────
def render_upload(cfg: dict) -> None:
    st.title("📤 Quản lý khảo sát")

    tab_upload, tab_edit = st.tabs(["📁 Upload DOCX mới", "✏️ Chỉnh sửa JSON"])

    # ──────────────────────────────────────────────────────────────────────────
    with tab_upload:
        st.markdown(
            "Upload file Word (`.docx`) để tự động tạo cấu hình khảo sát mới. "
            "File phải có cùng định dạng: phần câu hỏi phân loại đáp viên ở phần đầu, "
            "các bảng Likert 5 điểm ở phần sau."
        )

        uploaded = st.file_uploader("📎 Chọn file .docx", type=["docx"])

        if uploaded:
            st.success(f"Đã nhận file: **{uploaded.name}**")
            if st.button("🔄 Phân tích & áp dụng khảo sát mới", type="primary"):
                with st.spinner("Đang phân tích cấu trúc file..."):
                    try:
                        import tempfile
                        from docx_to_json import parse_docx_to_config

                        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                            tmp.write(uploaded.getvalue())
                            tmp_path = tmp.name

                        new_cfg = parse_docx_to_config(tmp_path, cfg["survey_meta"])
                        os.unlink(tmp_path)

                        # Backup old config
                        backup_path = os.path.join(
                            BASE_DIR,
                            f"survey_config_backup_{datetime.now():%Y%m%d_%H%M%S}.json",
                        )
                        with open(backup_path, "w", encoding="utf-8") as bf:
                            json.dump(cfg, bf, ensure_ascii=False, indent=2)

                        save_config(new_cfg)
                        st.success(
                            f"✅ Cấu hình khảo sát đã được cập nhật!\n\n"
                            f"Bản backup cũ được lưu tại: `{os.path.basename(backup_path)}`"
                        )
                        with st.expander("📋 Xem cấu hình mới"):
                            st.json(new_cfg)
                    except Exception as exc:
                        st.error(f"❌ Lỗi khi phân tích file: {exc}")
                        st.exception(exc)

    # ──────────────────────────────────────────────────────────────────────────
    with tab_edit:
        st.markdown("Chỉnh sửa trực tiếp nội dung JSON của cấu hình khảo sát.")
        raw_json = json.dumps(cfg, ensure_ascii=False, indent=2)
        edited = st.text_area(
            "Nội dung `survey_config.json`:",
            value=raw_json,
            height=500,
        )
        col_save, col_reset = st.columns([1, 4])
        if col_save.button("💾 Lưu thay đổi", type="primary"):
            try:
                new_cfg = json.loads(edited)
                save_config(new_cfg)
                st.success("Đã lưu thành công!")
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON không hợp lệ: {e}")

        with st.expander("ℹ️ Hướng dẫn thêm câu hỏi"):
            st.markdown(
                """
**Thêm câu hỏi Likert mới vào một phần:**
```json
// Trong mảng "questions" của một "likert_sections":
{"number": 8, "text": "Câu hỏi mới của bạn ở đây."}
```

**Thêm một phần Likert hoàn toàn mới:**
```json
{
  "id": "NEW",
  "title": "PHẦN X: TÊN PHẦN MỚI (NEW)",
  "short_title": "NEW — Mô tả ngắn",
  "description": "Mô tả hướng dẫn cho phần này",
  "variable_prefix": "new_",
  "scale": 5,
  "scale_labels": ["Hoàn toàn không đồng ý", "Không đồng ý", "Trung lập", "Đồng ý", "Hoàn toàn đồng ý"],
  "questions": [
    {"number": 1, "text": "Câu hỏi 1 của phần mới."},
    {"number": 2, "text": "Câu hỏi 2 của phần mới."}
  ]
}
```

**Đổi mật khẩu quản trị:**  
Tìm `"admin_password"` trong `survey_meta` và thay giá trị.
                """
            )


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="Research Survey Tool",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if not os.path.exists(CONFIG_FILE):
        st.error(
            f"⚠️ Không tìm thấy file cấu hình: `survey_config.json`\n\n"
            "Vui lòng đảm bảo file này nằm cùng thư mục với `survey_app.py`."
        )
        st.stop()

    cfg = load_config()
    meta = cfg["survey_meta"]

    with st.sidebar:
        st.markdown(f"## 📋 Survey Tool")
        st.caption(f"Phiên bản: {meta.get('version', '—')}")
        st.markdown("---")

        page = st.radio(
            "Điều hướng",
            ["📋 Khảo sát", "📊 Phân tích dữ liệu", "📤 Quản lý khảo sát"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Quick stats in sidebar
        if os.path.exists(DATA_FILE):
            try:
                n_resp = sum(1 for _ in open(DATA_FILE, encoding="utf-8-sig")) - 1
                st.metric("Phản hồi đã nhận", max(0, n_resp))
            except Exception:
                pass

        st.caption("© RMIT Vietnam Research Tool")

    if page == "📋 Khảo sát":
        render_survey(cfg)
    elif page == "📊 Phân tích dữ liệu":
        render_analysis(cfg)
    else:
        render_upload(cfg)


if __name__ == "__main__":
    main()
