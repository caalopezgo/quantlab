# Publish checklist (finish these two steps)

Everything in the repo is ready. Only GitHub login + Cloud deploy need your browser.

## 1. Public GitHub repo

Your local `gh` token expired. In a terminal:

```bash
cd /Users/carlos/quantlab
gh auth login -h github.com -p https -w
# follow the browser prompt

gh repo create quantlab --public --source=. --remote=origin --push \
  --description "Personal quantitative research engine — backtest, risk, paper trading"
```

If the name `quantlab` is taken:

```bash
gh repo create carlos-quantlab --public --source=. --remote=origin --push
```

Then paste the URL into `PORTFOLIO.md` and `docs/WEBSITE_SECTION.md` (replace `GITHUB_URL`).

## 2. Live demo (Streamlit Community Cloud)

1. Open https://share.streamlit.io  
2. New app → your public repo → branch `main` → main file `app.py`  
3. Deploy (uses `requirements.txt`)  
4. Paste the `*.streamlit.app` URL into `PORTFOLIO.md` and `docs/WEBSITE_SECTION.md` as `DEMO_URL`

Details: [`DEPLOY.md`](DEPLOY.md)

## 3. Website

Copy from [`WEBSITE_SECTION.md`](WEBSITE_SECTION.md) into your site.  
Images already live under `docs/images/`.

## 4. Verify CI

After the first push, open the repo **Actions** tab — workflow `ci` should run `pytest` on Python 3.11 and 3.12.
