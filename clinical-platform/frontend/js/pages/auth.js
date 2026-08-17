// js/pages/auth.js
import { apiCall } from '../api.js';

export class AuthPage {
  constructor(container, role, onLogin) {
    this.container = container;
    this.role = role;
    this.onLogin = onLogin;
    this.isLogin = true;
    this.render();
  }

  render() {
    const roleLabel = this.role === 'dentist' ? '🦷 Dentist' : '🦴 Orthopedist';
    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80vh;gap:24px">
        <div class="card" style="width:400px;padding:32px">
          <div class="text-center mb-md">
            <span style="font-size:24px">${roleLabel}</span>
            <h2 style="margin-top:8px">${this.isLogin ? 'Sign In' : 'Create Account'}</h2>
          </div>
          <form id="auth-form" class="flex flex-col gap-md">
            ${!this.isLogin ? '<div><label class="label">Full Name</label><input class="input" name="full_name" required></div>' : ''}
            <div><label class="label">Email</label><input class="input" type="email" name="email" required></div>
            <div><label class="label">Password</label><input class="input" type="password" name="password" required></div>
            <div id="auth-error" style="color:var(--color-danger);font-size:14px"></div>
            <button type="submit" class="btn btn-primary btn-lg">${this.isLogin ? 'Sign In' : 'Register'}</button>
          </form>
          <p class="text-center mt-md" style="font-size:14px">
            <a href="#" id="toggle-auth">${this.isLogin ? 'Create account' : 'Sign in'}</a>
          </p>
        </div>
      </div>
    `;
    this.container.querySelector('#auth-form').onsubmit = (e) => this.handleSubmit(e);
    this.container.querySelector('#toggle-auth').onclick = (e) => { e.preventDefault(); this.isLogin = !this.isLogin; this.render(); };
  }

  async handleSubmit(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const data = Object.fromEntries(form);
    try {
      const endpoint = this.isLogin ? '/api/auth/login' : '/api/auth/register';
      if (!this.isLogin) data.role = this.role;
      const result = await apiCall(endpoint, { method: 'POST', body: JSON.stringify(data) });
      this.onLogin(result.token);
    } catch (err) {
      document.getElementById('auth-error').textContent = err.message;
    }
  }
}