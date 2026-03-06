# SeekerBot: AI-Powered ATS Job Matcher & Scraper

[![Docker Hub](https://img.shields.io/badge/Docker_Hub-Latest-blue?logo=docker)](https://hub.docker.com/repository/docker/caiomussatto/seekerbot/)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Cloud_Run-green?logo=googlecloud)](https://jobseeker-pro-763634027496.southamerica-east1.run.app/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow?logo=python)](https://www.python.org/)

**SeekerBot** is an advanced automation tool designed to aggregate, filter, and critically evaluate job opportunities in the fields of Bioinformatics, Biology, and Data Science. It crawls multiple job boards (LinkedIn, Indeed, Glassdoor) and utilizes a rigorous AI-driven ATS (Applicant Tracking System) screening algorithm to score a candidate's Master CV against scraped job descriptions.

---

## Live Links
* **Web App (Live):** [SeekerBot on Google Cloud Run](https://jobseeker-pro-763634027496.southamerica-east1.run.app/)
* **Docker Image:** [caiomussatto/seekerbot on Docker Hub](https://hub.docker.com/repository/docker/caiomussatto/seekerbot)

---

## Key Features

* **Ruthless AI ATS Scoring:** Integrates with the Groq API to evaluate uploaded PDF resumes against job requirements. The algorithm strictly penalizes seniority gaps and missing hard skills, returning a 0-100 score and a professional rationale.
* **Automated Term Expansion:** Maximizes search visibility by using AI to expand a single user query into exactly 9 high-conversion, bilingual (Portuguese/English) job titles commonly used by tech recruiters.
* **Multi-Source Scraping:** Concurrent data extraction from major job boards using `python-jobspy`.
* **Stateless Processing:** Operates entirely in-memory for public deployments. Master CVs are parsed dynamically and discarded after scoring, ensuring data privacy and low cloud footprint.
* **Security-Hardened Docker:** Multi-stage Docker build utilizing `uv` for ultra-fast dependency resolution and running as a non-root user (`appuser`) to comply with enterprise cloud security standards.

---

## Tech Stack

* **Backend:** Python (Flask)
* **AI & Processing:** Groq API (LLMs), `pypdf`
* **Scraping Engine:** Python-JobSpy
* **Frontend:** Jinja2 Templates, Bootstrap 5, Markdown
* **DevOps:** Docker (Multi-stage, OCI annotations), UV (Package Manager)
* **Cloud Infrastructure:** Google Cloud Run (Serverless)

---

## Running with Docker

To run the stateless version of the app locally, you must provide your Groq API key via environment variables.

```bash
docker pull caiomussatto/seekerbot:latest

docker run -p 8080:8080 \
  -e GROQ_API_KEY="your_groq_api_key_here" \
  -e USE_DB=False \
  -e PORT=8080 \
  caiomussatto/seekerbot:latest
```

Once the container is running, access `http://localhost:8080` in your browser.

---

## Local Development & Setup

1. **Clone the repository:**

```bash
git clone https://github.com/CaioMussatto/SeekerBot
cd SeekerBot
```

2. **Environment Variables:**
Create a `.env` file in the project root folder. Include your database URL (if running the stateful branch) and your AI API key:

```env
USE_DB=False
GROQ_API_KEY=your_groq_api_key_here
```

3. **Install dependencies (using UV):**

```bash
uv sync --no-install-project
```

4. **Run the application:**

```bash
python app.py
```

---

## Author

**Caio Mussatto**

* Email: Caio.mussatto@gmail.com
* [LinkedIn](https://www.linkedin.com/in/caiomussatto/)

## Contributing

Contributions, issues, and feature requests are welcome.

1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

