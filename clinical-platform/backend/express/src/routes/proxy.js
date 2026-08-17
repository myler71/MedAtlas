// src/routes/proxy.js
import { Router } from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { authenticate } from '../middleware/auth.js';

export function createProxyRouter(fastapiBase) {
  const router = Router();

  router.use(authenticate);

  router.use('/', createProxyMiddleware({
    target: fastapiBase,
    changeOrigin: true,
    pathRewrite: (path) => path,  // keep the /api/* prefix
    onProxyReq: (proxyReq, req) => {
      if (req.user) {
        proxyReq.setHeader('x-user-id', req.user.id);
        proxyReq.setHeader('x-user-role', req.user.role);
        proxyReq.setHeader('x-clinic-id', req.user.clinic_id || '');
      }
    }
  }));

  return router;
}
