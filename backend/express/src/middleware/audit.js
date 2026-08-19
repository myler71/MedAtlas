// src/middleware/audit.js
import { Pool } from 'pg';

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

export function auditMiddleware(req, res, next) {
  const start = Date.now();
  res.on('finish', async () => {
    const duration = Date.now() - start;
    if (!req.path.startsWith('/api/')) return;
    try {
      await pool.query(
        `INSERT INTO audit_logs (user_id, action, resource_type, resource_id, success, ip_address, metadata)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [
          req.user?.id || null,
          `${req.method} ${req.path}`,
          req.path.split('/')[2] || null,
          req.params?.id || null,
          res.statusCode < 400,
          req.ip,
          JSON.stringify({ duration_ms: duration, status: res.statusCode })
        ]
      );
    } catch (e) {
      console.error('audit log fail', e);
    }
  });
  next();
}
