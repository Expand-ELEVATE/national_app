# Expand ELEVATE — National App

Deployed **once** by the PATH/national team on Streamlit Community Cloud.
Code is public (same "no secrets in repo" pattern as the state app), but
this app's secrets include the Supabase **service_role** key, which
bypasses Row Level Security — treat the deployed URL and login as the
most sensitive part of the whole platform.

## Setup

1. Deploy this repo on Streamlit Community Cloud, pointing at `national_app/app.py`.
2. In **Settings → Secrets**, paste (see `.streamlit/secrets.toml.example`):
   ```
   SUPABASE_URL = "..."
   SUPABASE_SERVICE_ROLE_KEY = "..."   # powerful — never share, never commit
   SUPABASE_ANON_KEY = "..."
   ```
3. Create the first national admin account directly in Supabase (Auth →
   Users → Add user), then insert a matching row in `admin_profiles` with
   `role='national'`, `state_code=NULL`.

## Local development

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill in real values
streamlit run app.py
```

## Pages
- **Dashboard** — paired pre/post counts and `scipy.stats.ttest_rel`
  paired t-tests, filterable by state and by level/designation
- **Questionnaire Builder** — create the single active questionnaire from CSV
- **Admin — Delete Data** — destructive ops; forces a full backup download
  and a typed "DELETE" confirmation before any table is wiped
- **Export** — download all data, or selected state(s), as CSV

## Security notes
- Only this app holds `service_role`. `state_app` must never have it.
- Deletion is deliberately slow and explicit (download → checkbox → type
  DELETE → click) specifically because there is only ever one active
  questionnaire — deleting it is a real, irreversible operational event.
