// js/pages/dashboard.js
import { apiCall } from '../api.js';

export class Dashboard {
  constructor(container, role, token) {
    this.container = container;
    this.role = role;
    this.token = token;
    this.render();
  }

  render() {
    const roleLabel = this.role === 'dentist' ? '🦷 Dentist' : '🦴 Orthopedist';
    const primaryModule = this.role === 'dentist' ? 'Dental Chart' : 'Skeleton / Orthopedic Chart';
    this.container.innerHTML = `
      <div>
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border);margin-bottom:24px">
          <div style="display:flex;gap:24px;align-items:center">
            <strong>Clinical Platform</strong>
            <span class="text-secondary">${roleLabel}</span>
          </div>
          <div style="display:flex;gap:16px;align-items:center">
            <button class="btn btn-secondary" id="btn-logout">Logout</button>
          </div>
        </nav>
        <div class="grid-3">
          <div class="card"><h3>Patients</h3><p class="text-secondary mt-md">Manage patient records</p></div>
          <div class="card"><h3>${primaryModule}</h3><p class="text-secondary mt-md">Interactive clinical chart</p></div>
          <div class="card"><h3>Drug Checker</h3><p class="text-secondary mt-md">Check drug interactions</p></div>
          <div class="card"><h3>AI Assistant</h3><p class="text-secondary mt-md">Ask about patient records</p></div>
          <div class="card"><h3>Appointments</h3><p class="text-secondary mt-md">Schedule and manage</p></div>
          <div class="card"><h3>History</h3><p class="text-secondary mt-md">View audit history</p></div>
        </div>
      </div>
    `;
    this.container.querySelector('#btn-logout').onclick = () => {
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      location.reload();
    };
  }
}