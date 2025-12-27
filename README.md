# 🔍 SeekerBot
### Automated Job Scraper 

[![Docker Hub](https://img.shields.io/badge/Docker_Hub-Latest-blue?logo=docker)](https://hub.docker.com/repository/docker/caiomussatto/seekerbot/)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Cloud_Run-green?logo=googlecloud)](https://seekerbot-763634027496.southamerica-east1.run.app/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow?logo=python)](https://www.python.org/)

**SeekerBot** is a specialized automation tool designed to aggregate, filter, and track job opportunities in the fields of Bioinformatics, Biology, and Data Science. It crawls multiple sources (LinkedIn, Indeed, Google Jobs) and provides a clean dashboard for job application management.

---

## 🚀 Live Links
- **Web App (Live):** [SeekerBot on Google Cloud Run](https://jobseeker-pro-763634027496.southamerica-east1.run.app/)
- **Docker Image:** https://hub.docker.com/repository/docker/caiomussatto/jobseeker

---

## ✨ Key Features
- **Multi-Source Scraping:** Concurrent extraction from LinkedIn, Indeed, and Google Jobs using `python-jobspy`.
- **Intelligent Filtering:** Precision filtering by mandatory keywords (e.g., Python, Master's, Laboratory) and location.
- **Dual Operating Modes:**
  - **Personal Mode:** Connected to a Supabase (PostgreSQL) database for persistent tracking and "Applied/Delete" status management.
  - **Public Mode:** Ephemeral session-based search for public demonstrations.
- **Clean UI:** Dark-themed responsive dashboard built with Flask and Bootstrap 5.
- **Dual Date Tracking:** Displays both the original job posting date and the date the opportunity was found by the bot.

---

## 🛠️ Tech Stack
- **Backend:** Python (Flask)
- **Database:** PostgreSQL (Supabase) via SQLAlchemy ORM
- **Scraping Engine:** Python-JobSpy (Crumble based)
- **Frontend:** Jinja2 Templates, Bootstrap 5, Markdown
- **DevOps:** Docker (Multi-stage builds), UV (Package Manager)
- **Cloud:** Google Cloud Run (Serverless)

---

## 🐳 Running with Docker

To run the public version of the app locally:

```bash
docker pull caiomussatto/seekerbot:latest
docker run -p 8080:8080 caiomussatto/seekerbot:latest
```

Then access `http://localhost:8080` in your browser.

---

## 🔧 Local Development & Setup

1. **Clone the repository:**
```bash
git clone https://github.com/CaioMussatto/SeekerBot

cd SeekerBot
```


2. **Environment Variables:**
Create a `.env` file for your database connection:
```env
DATABASE_URL=your_postgresql_url
USE_DB=True
```


3. **Install dependencies (using UV):**
```bash
uv sync --no-install-project
```


4. **Initialize the database:**
```bash
python database.py
```


5. **Run the application:**
```bash
python app.py
```



---

## 👤 Author

**Caio Mussatto**

* Email: [Caio.mussatto@gmail.com](mailto:Caio.mussatto@gmail.com)
* [LinkedIn](https://www.linkedin.com/in/caiomussatto/)

## Contributing

Contributions, issues, and feature requests are welcome.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.