# Deploy — Streamlit Community Cloud

## One-time setup

1. Push this repo to GitHub (public).  
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.  
3. Select the repo, branch `main`, main file: `app.py`.  
4. Deploy. First run downloads Yahoo data into the Cloud instance cache.

## Project files used by Cloud

| File | Role |
| --- | --- |
| `app.py` | Entrypoint |
| `requirements.txt` | Dependencies (Cloud ignores `pyproject` editable installs) |
| `.streamlit/config.toml` | Theme |
| `config/default.yaml` | Strategy / risk defaults |

## Notes

- Free tier sleeps when idle; first load can be slow.  
- SQLite paper state on Cloud is **ephemeral** unless you add external storage — fine for demos.  
- Do not put brokerage secrets anywhere; V0.1 has none.  
- After deploy, paste the URL into `PORTFOLIO.md` and `docs/WEBSITE_SECTION.md`.

## Local parity

```bash
pip install -r requirements.txt
streamlit run app.py
```
