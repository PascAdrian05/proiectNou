# Setup Instructions

## Database
Baza de date este PostgreSQL 16 care rulează în Docker. Pentru a porni doar baza de date:
```bash
docker-compose up db
```

## Backend Setup

### 1. Adaugă cheia GROQ pentru AI
Deschide `backend/.env` și adaugă cheia ta GROQ:
```env
GROQ_API_KEY=gsk_...cheia_ta_aici
```
Poți obține o cheie gratuită la: https://console.groq.com

### 2. Aplică migrațiile bazei de date
```bash
cd backend
docker-compose exec api alembic upgrade head
```

Sau dacă rulezi backend-ul local:
```bash
cd backend
python -m alembic upgrade head
```

### 3. Pornește backend-ul
```bash
docker-compose up api
```

Backend-ul va rula pe: http://localhost:8000
API docs: http://localhost:8000/api/v1/docs

## Frontend Setup

### 1. Instalează dependențele
```bash
cd frontend
npm install
```

### 2. Pornește frontend-ul
```bash
npm run dev
```

Frontend-ul va rula pe: http://localhost:3000

## Verificare

### 1. Creează un cont
- Mergi la http://localhost:3000/register
- Creează un cont nou

### 2. Testează AI Assistant
- După login, vei vedea butonul "AI Assistant" în dreapta jos
- Click pe el pentru a deschide panoul
- Click pe "Get security tips" sau "Verify posture"
- Primul request va fi încărcat (poate dura 5-10 secunde)
- Rezultatul va fi salvat automat în baza de date

### 3. Verifică datele în baza de date
```bash
docker-compose exec db psql -U postgres -d security_monitor
```

```sql
-- Vezi utilizatorii
SELECT id, email, role FROM "user";

-- Vezi conversațiile AI
SELECT id, user_id, conversation_type, created_at FROM ai_conversation;

-- Ieși
\q
```

## Dacă AI-ul rămâne încărcare

1. **Verifică că GROQ_API_KEY este setată** în `backend/.env`
2. **Verifică logs-urile backend-ului**:
   ```bash
   docker-compose logs api
   ```
3. **Verifică că backend-ul rulează**:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
4. **Verifică că migrația a fost aplicată**:
   ```bash
   docker-compose exec api alembic current
   ```

## Structura aplicației

### Frontend
- **Pagini protejate**: Dashboard, Websites, Scans, Findings, Alerts, Settings, Billing
- **Butoane dezactivate când nu ești logat**: Toate acțiunile (create, delete, refresh, AI analyze)
- **AI Assistant**: Apare DOAR după login, salvează conversațiile în baza de date

### Backend
- **API**: FastAPI cu SQLModel
- **Bază de date**: PostgreSQL 16 (port 5433 pe host)
- **AI**: Groq API (model llama-3.3-70b-versatile)
- **Migrații**: Alembic

### Endpoint-uri AI
- `POST /api/v1/ai/security-tips` - Obține sfaturi de securitate
- `POST /api/v1/ai/verify-posture` - Verifică postura de securitate
- `POST /api/v1/ai/analyze-finding/{id}` - Analizează un finding specific
- `GET /api/v1/ai/conversations/` - Lista conversațiilor user-ului
- `POST /api/v1/ai/conversations/` - Creează o conversație nouă
- `PATCH /api/v1/ai/conversations/{id}` - Actualizează o conversație
- `DELETE /api/v1/ai/conversations/{id}` - Șterge o conversație

## Troubleshooting

### "AI Assistant is not configured"
- Adaugă `GROQ_API_KEY` în `backend/.env`
- Restart backend-ul: `docker-compose restart api`

### "Failed to load conversations"
- Verifică că migrația a fost aplicată: `alembic upgrade head`
- Verifică logs: `docker-compose logs api`

### Butoane dezactivate
- Verifică că ești logat (vezi în header "Signed in as...")
- Verifică browser console pentru erori

### Eroare de conexiune la baza de date
- Verifică că PostgreSQL rulează: `docker-compose ps db`
- Verifică connection string-ul în `backend/.env`