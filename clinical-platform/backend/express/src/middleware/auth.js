// src/middleware/auth.js
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';

export function authenticate(req, res, next) {
  const token = req.cookies?.token || req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'No token provided' } });
  }
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ error: { code: 'INVALID_TOKEN', message: 'Invalid or expired token' } });
  }
}

export function generateToken(user) {
  return jwt.sign(
    { id: user.id, email: user.email, role: user.role, clinic_id: user.clinic_id },
    JWT_SECRET,
    { expiresIn: `${process.env.JWT_EXPIRY_MINUTES || 15}m` }
  );
}

export function generateRefreshToken(user) {
  return jwt.sign(
    { id: user.id, type: 'refresh' },
    JWT_SECRET,
    { expiresIn: `${process.env.JWT_REFRESH_DAYS || 7}d` }
  );
}
