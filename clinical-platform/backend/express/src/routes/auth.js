// src/routes/auth.js
import { Router } from 'express';
import bcrypt from 'bcryptjs';
import { pool } from '../services/db.js';
import { generateToken, generateRefreshToken, authenticate } from '../middleware/auth.js';

export const authRouter = Router();

authRouter.post('/register', async (req, res) => {
  try {
    const { email, password, full_name, role, clinic_id } = req.body;
    if (!email || !password || !full_name) {
      return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'Email, password, and full_name are required' } });
    }
    if (!['dentist', 'orthopedist', 'admin'].includes(role)) {
      return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'Role must be dentist, orthopedist, or admin' } });
    }
    const existing = await pool.query('SELECT id FROM users WHERE email = $1 AND deleted_at IS NULL', [email]);
    if (existing.rows.length > 0) {
      return res.status(409).json({ error: { code: 'USER_EXISTS', message: 'A user with this email already exists' } });
    }
    const password_hash = await bcrypt.hash(password, 12);
    const result = await pool.query(
      'INSERT INTO users (email, password_hash, full_name, role, clinic_id) VALUES ($1, $2, $3, $4, $5) RETURNING id, email, full_name, role, clinic_id',
      [email, password_hash, full_name, role, clinic_id || null]
    );
    const user = result.rows[0];
    const token = generateToken(user);
    const refreshToken = generateRefreshToken(user);
    res.cookie('token', token, { httpOnly: true, maxAge: 15 * 60 * 1000 });
    res.status(201).json({ user, token, refreshToken });
  } catch (err) {
    console.error('Register error:', err);
    res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Registration failed' } });
  }
});

authRouter.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    if (!email || !password) {
      return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'Email and password are required' } });
    }
    const result = await pool.query(
      'SELECT id, email, password_hash, full_name, role, clinic_id FROM users WHERE email = $1 AND deleted_at IS NULL',
      [email]
    );
    if (result.rows.length === 0) {
      return res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' } });
    }
    const user = result.rows[0];
    const valid = await bcrypt.compare(password, user.password_hash);
    if (!valid) {
      return res.status(401).json({ error: { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' } });
    }
    const token = generateToken(user);
    const refreshToken = generateRefreshToken(user);
    delete user.password_hash;
    res.cookie('token', token, { httpOnly: true, maxAge: 15 * 60 * 1000 });
    res.json({ user, token, refreshToken });
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Login failed' } });
  }
});

authRouter.get('/me', authenticate, async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT id, email, full_name, role, clinic_id FROM users WHERE id = $1 AND deleted_at IS NULL',
      [req.user.id]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: { code: 'USER_NOT_FOUND', message: 'User not found' } });
    }
    res.json({ user: result.rows[0] });
  } catch (err) {
    res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to fetch user' } });
  }
});

authRouter.post('/logout', (req, res) => {
  res.clearCookie('token');
  res.json({ message: 'Logged out' });
});
