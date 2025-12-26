# 🧬 Bioinfo Seeker Pro

A professional automated job hunting platform specifically designed for Bioinformatics and Biological Sciences. This tool crawls multiple job boards, applies custom filters, and manages a local database of opportunities with a high-end dark mode interface.

## 🚀 Key Features

- **Multi-Source Scraping**: Integrated with LinkedIn, Indeed, and Google Jobs using the JobSpy engine.
- **Dynamic Filtering**: Real-time filtering based on user-defined mandatory keywords in job descriptions.
- **Modern Tech Stack**: Built with Flask (Python) and a robust SQLAlchemy-based SQLite database.
- **Async-like UX**: Includes a custom JavaScript-based loading overlay to handle long-running scraping tasks without page timeouts.
- **Clean UI**: A high-contrast dark mode dashboard built with Bootstrap 5 and custom CSS.
- **Job Management**: Complete CRUD-like lifecycle (Search -> Save -> Mark as Applied -> Delete).

## 🛠️ Technical Skills Demonstrated

- **Back-end**: Python, Flask, SQLAlchemy (ORM).
- **Front-end**: HTML5, CSS3 (Modern UI/UX with Glassmorphism), JavaScript (DOM manipulation).
- **Data Engineering**: Web scraping, data cleaning, and persistence.
- **Environment Management**: Managed via `uv` for lightning-fast dependency resolution and reproducibility.
- **DevOps Ready**: Configured with `.gitignore` and environment variables for cloud deployment.

## 📂 Project Structure

```text
.
├── app.py           # Flask Server & Routes
├── database.py      # SQLAlchemy Models & DB Connection
├── seeker.py        # Core Scraping & Filtering Logic
├── static/          # Custom CSS & Assets
├── templates/       # Jinja2 HTML Templates
├── pyproject.toml   # Project metadata and dependencies
└── uv.lock          # Deterministic lockfile
```
---

## 👤 Author

**Caio Mussatto** - [Caio.mussatto@gmail.com](mailto:Caio.mussatto@gmail.com)

---

*Licensed under the MIT License.*
