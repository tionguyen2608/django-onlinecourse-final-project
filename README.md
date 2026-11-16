# OnlineCourse assessment project

A Django course application with lessons, enrollment, multiple-choice exams, saved submissions, and weighted exam results. Learners pass at 80% or above. Each question is scored only when all correct choices, and no incorrect choices, are selected.

Built from IBM Developer Skills Network's [official starter project](https://github.com/ibm-developer-skills-network/final-cloud-app-with-database). The original Apache 2.0 license is retained.

## Run on Windows

Use Python 3.12 or later.

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
$env:DEMO_ADMIN_PASSWORD = Read-Host "Choose a local demo password"
.venv\Scripts\python manage.py seed_demo
.venv\Scripts\python manage.py runserver
```

## Run on Linux or macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
```

Open `http://127.0.0.1:8000/onlinecourse/` for the course and `http://127.0.0.1:8000/admin/` for administration. The demo administrator's username is `datadmin`. Supply its password through `DEMO_ADMIN_PASSWORD`. If that variable is not provided, the seed command creates a random local password in `.local-demo-password`, which Git ignores. Do not upload that password file or the local database.

The demo seed is repeatable. It adds three lessons and a three-question exam, including a question with multiple correct choices. Enroll in the course before submitting the exam.

## Validation

```bash
python manage.py check
python manage.py test onlinecourse --verbosity 2
```

The 15 tests cover scoring, saved submissions, missing enrollment, invalid and foreign-course choices, result ownership, and duplicate enrollment.

## Screenshot evidence

The GitHub Actions workflow runs the checks and captures screenshots from the running application. Download the `project-evidence` artifact from the successful workflow run. You can also generate the evidence locally:

```bash
python -m pip install playwright
python -m playwright install chromium
python tools/capture_evidence.py
```

The script logs into the local demo application, opens the actual admin site, enrolls in the course, submits a correct exam attempt, and captures the pages. It does not generate or alter screenshot content.

See [SUBMISSION.md](SUBMISSION.md) for the seven required submission items.

For deployment, set a private `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=0`, and configure `DJANGO_ALLOWED_HOSTS` for the intended host.
