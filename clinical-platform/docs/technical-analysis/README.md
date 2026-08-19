# Clinical Platform — Technical Documentation Index

## Documents

| Document | Content | Lines |
|----------|---------|-------|
| [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) | Architecture, modules, services, deployment | ~350 |
| [DATA_STRUCTURES.md](./DATA_STRUCTURES.md) | All database tables, ER diagram, Python models | ~500 |
| [DATA_FLOW.md](./DATA_FLOW.md) | Request flows, auth, CRUD, RAG pipeline | ~400 |
| [KEY_FUNCTIONS.md](./KEY_FUNCTIONS.md) | Critical function deep-dives, call graph | ~400 |
| [KEY_QUESTIONS.md](./KEY_QUESTIONS.md) | Design decisions, trade-offs, security gaps | ~300 |

## Quick Navigation

### By Topic
- **Authentication**: SYSTEM_OVERVIEW §6, DATA_FLOW §1-2, KEY_FUNCTIONS §1-2, KEY_QUESTIONS §2
- **Database Schema**: DATA_STRUCTURES §2-7, SYSTEM_OVERVIEW §5
- **Dental Domain**: DATA_STRUCTURES §3, DATA_FLOW §4, KEY_FUNCTIONS §3
- **Orthopedic Domain**: DATA_STRUCTURES §4, DATA_FLOW §5, KEY_FUNCTIONS §4
- **Drug Intelligence**: DATA_STRUCTURES §6, DATA_FLOW §6, KEY_FUNCTIONS §5
- **RAG Pipeline**: DATA_STRUCTURES §7, DATA_FLOW §7, KEY_FUNCTIONS §6
- **AI Chat**: DATA_FLOW §8, KEY_QUESTIONS §7
- **Security**: SYSTEM_OVERVIEW §7, KEY_QUESTIONS §13
- **Frontend**: SYSTEM_OVERVIEW §4.3, DATA_FLOW §10, KEY_FUNCTIONS §7
- **Deployment**: SYSTEM_OVERVIEW §8

### By Module
- **Express Gateway**: server.js, auth.js, proxy.js, audit.js, rbac.js, errorHandler.js
- **FastAPI Backend**: main.py, patients.py, dental.py, orthopedic.py, drugs.py, chat.py
- **RAG**: embeddings.py, retrieval.py, tavily.py
- **AI**: patient_assistant.py
- **Frontend**: app.js, api.js, odontogram.js, skeleton-svg.js
