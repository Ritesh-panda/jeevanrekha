# Ama Swasthya Sahayaka

> **An AI-driven, multi-lingual public health WhatsApp chatbot delivering instant medical guidance, emergency detection, and localized healthcare access for the people of Odisha.**

---

## 📖 Overview

**Ama Swasthya Sahayaka** (Our Health Assistant) is a localized healthcare accessibility platform built on WhatsApp. It bridges the gap between citizens and critical health information by leveraging advanced AI (Google Gemini / Vertex AI) to understand queries in regional languages (like Odia and Hindi) and provide real-time, actionable medical guidance. 

**Who it is for:** Citizens seeking quick medical information, parents tracking child vaccinations, and anyone needing immediate localized hospital details.
**Why it exists:** To democratize access to healthcare information, reduce panic during medical emergencies, and ensure life-saving guidance is accessible to everyone regardless of language barriers.

---

## ✨ Key Features

* **🚨 Intelligent Emergency Detection:** Automatically detects critical medical situations from user messages and prioritizes action-first responses (e.g., immediate steps, calling 108).
* **🌍 Multi-lingual AI Support:** Auto-detects user language, translates queries to English for processing, and replies back in the user's native tongue.
* **🏥 Geolocation Hospital Finder:** Integrates with WhatsApp location sharing and PostGIS to find the nearest hospitals and specialized doctors.
* **🔎 AI Symptom Analysis:** Acts as a first-level triage, analyzing user-described symptoms and providing advisory guidance.
* **💉 Automated Vaccination Scheduler:** Calculates personalized immunization schedules based on a child's Date of Birth.
* **📰 Real-time Health Alerts:** Fetches the latest public health news and disease outbreak alerts.

### 🎯 System Use Cases

```mermaid
flowchart LR
    User([User / Citizen])
    
    subgraph Ama Swasthya Sahayaka
        UC1[Symptom Analysis]
        UC2[Emergency Triage]
        UC3[Hospital & Doctor Finder]
        UC4[Vaccine Scheduling]
        UC5[Health Alerts]
    end
    
    User -->|WhatsApp Message| UC1
    User -->|Text/Location| UC2
    User -->|Share Location| UC3
    User -->|Provide DOB| UC4
    User -->|Request Updates| UC5
```

---

## 🛠️ Tech Stack

**Backend Framework:**
* FastAPI (Python 3)
* Uvicorn (ASGI Server)

**Database & Infrastructure:**
* PostgreSQL (Relational Database)
* PostGIS / GeoAlchemy2 (Geospatial querying for hospitals)
* SQLAlchemy (ORM) & Alembic (Migrations)
* Redis & Celery (Asynchronous Task Queues)

**AI & Cloud Integrations:**
* Google Generative AI (Gemini) & Vertex AI (Intent classification & Medical AI)
* Google Cloud Translation (Multi-lingual support)
* Twilio API (WhatsApp Sandbox Webhooks)
* NewsAPI (Health alerts)

### 🧩 Component Architecture

```mermaid
flowchart TD
    User((WhatsApp User)) <-->|Twilio API| Webhook
    
    subgraph FastAPI Application
        Webhook[API Router] --> Services[Service Layer]
        Services --> CRUD[Data Access Layer]
    end
    
    subgraph External APIs
        Services <--> Translation[Google Translate]
        Services <--> LLM[Vertex AI / Gemini]
        Services <--> News[News API]
    end
    
    subgraph Data Layer
        CRUD <--> PostgreSQL[(PostgreSQL + PostGIS)]
        Services <--> Redis[(Redis Cache/Broker)]
        Redis <--> Celery[Celery Workers]
    end
```

---

## 🏗️ Architecture

1. **User Interaction:** The user sends a WhatsApp message in their preferred language to the Twilio Sandbox number.
2. **Ingestion & Translation:** Twilio sends a POST webhook to the FastAPI backend (`/api/v1/chat`). The system detects the language and translates the payload into English.
3. **Intent Routing:** The message is fed into Google Vertex AI/Gemini, which uses structured schemas to classify the intent (`EMERGENCY`, `SYMPTOM_ANALYSIS`, `HOSPITAL_FINDER`, `VACCINE_SCHEDULE`, `GET_ALERTS`).
4. **Service Execution:**
   * *Emergency/Symptom:* AI generates medical advisory text.
   * *Location:* PostGIS queries the database for hospitals nearest to the provided coordinates.
   * *Vaccine:* The system calculates future vaccine dates based on the provided DOB.
5. **Response & Delivery:** The final response is translated back into the user's native language and dispatched via Twilio's Messaging API.

### 🔀 Core Logic Flow (Activity Diagram)

```mermaid
flowchart TD
    Start([Receive WhatsApp Message]) --> DetectLang{Is English?}
    DetectLang -- No --> TranslateIn[Translate to English]
    DetectLang -- Yes --> RouteIntent
    TranslateIn --> RouteIntent[Analyze Intent via Vertex AI]
    
    RouteIntent --> Switch{Intent Type}
    
    Switch -- EMERGENCY --> Emg[Generate Actionable Steps]
    Switch -- HOSPITAL_FINDER --> Loc{Has Location?}
    Loc -- Yes --> PostGIS[Find Nearest Hospital]
    Loc -- No --> AskLoc[Prompt for Location]
    
    Switch -- VACCINE_SCHEDULE --> DOB{Has DOB?}
    DOB -- Yes --> Calc[Calculate Schedule]
    DOB -- No --> AskDOB[Prompt for DOB]
    
    Switch -- SYMPTOM_ANALYSIS --> Symp[Generate AI Triage Advice]
    Switch -- GET_ALERTS --> Alerts[Fetch News API]
    
    Emg --> Finalize
    PostGIS --> Finalize
    AskLoc --> Finalize
    Calc --> Finalize
    AskDOB --> Finalize
    Symp --> Finalize
    Alerts --> Finalize
    
    Finalize[Prepare Final Response] --> DetectOrig{Original Lang English?}
    DetectOrig -- No --> TranslateOut[Translate to Original Language]
    DetectOrig -- Yes --> Send
    
    TranslateOut --> Send[Send Twilio XML Response]
    Send --> Finish([End])
```

### 🔄 System Workflow Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User (WhatsApp)
    participant T as Twilio Sandbox
    participant F as FastAPI Backend
    participant Tr as Google Translation
    participant AI as Vertex AI / Gemini
    participant DB as PostgreSQL + PostGIS

    U->>T: Sends Message (e.g., in Odia/Hindi)
    T->>F: Webhook POST /api/v1/chat
    F->>Tr: Detect Language & Translate to English
    Tr-->>F: English Translation
    F->>AI: Determine Intent & Medical Context
    AI-->>F: Structured Intent
    
    alt is EMERGENCY
        F->>F: Generate Action-First Emergency Response
    else is HOSPITAL_FINDER
        F->>DB: Query Nearest Hospitals (ST_DWithin)
        DB-->>F: Hospital List
    else is VACCINE_SCHEDULE
        F->>DB: Fetch Vaccine Schedule based on DOB
        DB-->>F: Schedule Data
    end
    
    F->>Tr: Translate Response to User's Language
    Tr-->>F: Translated Response
    F->>T: TwiML XML Response
    T->>U: WhatsApp Reply
```

---

## 🗄️ Database Schema

```mermaid
erDiagram
    USER {
        string id PK "WhatsApp number"
        string language_preference
        datetime created_at
    }
    HOSPITAL {
        int id PK
        string name
        string city
        geometry location "POINT"
    }
    DOCTOR {
        int id PK
        string name
        string specialty
        int hospital_id FK
    }
    VACCINE {
        int id PK
        string name
        int due_at_weeks_min
        int due_at_weeks_max
        text details
    }
    APPOINTMENT {
        int id PK
        string user_id FK
        int doctor_id FK
        int hospital_id FK
        datetime appointment_time
        string status
        datetime created_at
    }

    HOSPITAL ||--o{ DOCTOR : "has"
    USER ||--o{ APPOINTMENT : "books"
    DOCTOR ||--o{ APPOINTMENT : "assigned to"
    HOSPITAL ||--o{ APPOINTMENT : "hosted at"
```

---

## 📂 Folder Structure

```text
ama_swasthya_sahayaka/
├── alembic/                # Database migration scripts and versions
├── app/
│   ├── api/                # API routers (Twilio webhook endpoints)
│   ├── core/               # App configuration and environment variables
│   ├── crud/               # Database operations (Users, Hospitals, Vaccines)
│   ├── db/                 # DB connection and session management
│   ├── models/             # SQLAlchemy ORM models (including PostGIS Geometry)
│   ├── schemas/            # Pydantic models for strict data validation
│   └── services/           # Core business logic (AI, Maps, Translation, Alerts)
├── .env                    # Environment variables configuration
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic configuration
├── seed_database.py        # Script to mock hospitals and doctors
└── seed_vaccines.py        # Script to populate standard immunization data
```

---

## 🚀 Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/your-username/ama-swasthya-sahayaka.git
cd ama-swasthya-sahayaka
```

**2. Set up a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure Environment Variables**
Create a `.env` file in the root directory and add the following:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
GOOGLE_API_KEY=your_gemini_api_key
NEWS_API_KEY=your_news_api_key
```
*(Ensure your PostgreSQL database has the PostGIS extension enabled: `CREATE EXTENSION postgis;`)*

**5. Run Database Migrations & Seeding**
```bash
alembic upgrade head
python seed_database.py
python seed_vaccines.py
```

**6. Start the API Server**
```bash
uvicorn app.main:app --reload
```

**7. Expose Local Server**
Use Ngrok to expose your local FastAPI server to the internet, then paste the Ngrok URL (`https://<your-ngrok-url>/api/v1/chat`) into your Twilio WhatsApp Sandbox Webhook settings.
```bash
ngrok http 8000
```

---

## 📱 Usage

Once running, interact with the bot on WhatsApp using natural language:

* **Symptom Triage:** *"Mujhe bukhar aur sardi hai"* (Hindi: I have a fever and cold)
* **Hospital Finder:** Tap the `+` icon on WhatsApp > **Location** > **Share Current Location**
* **Vaccination:** *"Vaccine schedule for baby born on 10 Jan 2025"*
* **Alerts:** *"What are the latest health alerts?"*

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Basic health check endpoint. |
| `POST` | `/api/v1/chat` | Main Twilio Webhook. Receives `From`, `Body`, `Latitude`, and `Longitude` as form data. |

---

## 🗺️ Roadmap

* **Voice Note Integration:** Process WhatsApp audio messages using Google Cloud Speech-to-Text for users who cannot type.
* **Telemedicine Handoff:** Integrate with local doctor APIs to allow direct appointment booking from the chat.
* **Image Analysis:** Allow users to upload images of prescriptions or visible symptoms (rashes, wounds) for preliminary AI analysis.
* **Push Notifications:** Send proactive automated WhatsApp reminders for upcoming baby vaccinations.

---

## ⚠️ Limitations / Assumptions

* **Production WhatsApp Access:** The current setup assumes the use of the Twilio Sandbox. For production, a verified WhatsApp Business API account is required.
* **Medical Liability:** The AI provides *advisory* information. It is strictly not a replacement for professional medical diagnosis.
* **Infrastructure:** Accurate hospital discovery requires a well-populated, production-grade PostGIS database with verified coordinates.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.
