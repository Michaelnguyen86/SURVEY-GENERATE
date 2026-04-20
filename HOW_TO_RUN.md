# HOW TO RUN & DEPLOY — Research Survey Tool

## Run locally (immediate)

```
streamlit run survey_app.py
```
Opens at: http://localhost:8501

Share on local network: http://YOUR_IP:8501

---

## Deploy online (free public link via Streamlit Cloud)

1. Push this folder to a GitHub repository  
2. Go to https://streamlit.io/cloud → Sign in with GitHub  
3. Click **New app** → select your repo → set `survey_app.py` as entrypoint  
4. Click **Deploy** — you get a link like `https://yourapp.streamlit.app`  
5. Share that link with respondents  

---

## Files

| File | Purpose |
|------|---------|
| `survey_app.py` | Main Streamlit application (survey + analysis + upload) |
| `survey_config.json` | Survey definition — edit this to change questions |
| `docx_to_json.py` | Parser: converts a new DOCX questionnaire → JSON config |
| `requirements.txt` | Python dependencies |
| `responses.csv` | Created automatically when first response is submitted |

---

## Admin dashboard

- In the sidebar, click **📊 Phân tích dữ liệu**  
- Password: `research2026` (change in `survey_config.json` → `admin_password`)  
- Features: Cronbach's α, construct means, correlation matrix, demographics charts  
- Download all data as CSV with one click  

---

## Add questions to an existing section

In `survey_config.json`, find the section and add to its `questions` array:
```json
{"number": 8, "text": "Your new question text here."}
```

## Add a completely new Likert section

Append to the `likert_sections` array in `survey_config.json`:
```json
{
  "id": "NEW",
  "title": "PHẦN X: NEW SECTION TITLE (NEW)",
  "short_title": "NEW — Short description",
  "description": "Instruction shown above questions",
  "variable_prefix": "new_",
  "scale": 5,
  "scale_labels": ["Hoàn toàn không đồng ý","Không đồng ý","Trung lập","Đồng ý","Hoàn toàn đồng ý"],
  "questions": [
    {"number": 1, "text": "Question 1 text."},
    {"number": 2, "text": "Question 2 text."}
  ]
}
```

## Use a new DOCX questionnaire

### Option A — via the app UI
1. Open the app → sidebar → **📤 Quản lý khảo sát** → Upload DOCX  

### Option B — command line
```
python docx_to_json.py "New Questionnaire.docx" --output survey_config.json
```
