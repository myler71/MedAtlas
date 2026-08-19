import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import path from 'path';
import { fileURLToPath } from 'url';
import { authRouter } from './routes/auth.js';
import { createProxyRouter } from './routes/proxy.js';
import { auditMiddleware } from './middleware/audit.js';
import { errorHandler } from './middleware/errorHandler.js';

const app = express();
const PORT = process.env.EXPRESS_PORT || 3000;
const FASTAPI_BASE = process.env.FASTAPI_INTERNAL_URL || 'http://localhost:8000';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendPath = path.join(__dirname, '../../../frontend');

app.use(helmet());
app.use(cors({ origin: true, credentials: true }));
app.use(express.json());
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }));
app.use(auditMiddleware);
app.use(express.static(frontendPath));

// Routes
app.use('/api/auth', authRouter);
app.use('/api', createProxyRouter(FASTAPI_BASE));

// Health check
app.get('/api/health', (req, res) => res.json({ status: 'ok', service: 'express' }));

// Serve frontend for all non-API routes
app.get('*', (req, res) => {
  res.sendFile(path.join(frontendPath, 'index.html'));
});

// Error handler
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`Express gateway running on port ${PORT}`);
});

export default app;
