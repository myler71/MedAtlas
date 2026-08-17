// js/pages/patient-overview.js
import { apiCall } from '../api.js';
import { DentalChartPage } from './dental-chart.js';
import { SkeletonPage } from './skeleton.js';

export class PatientOverviewPage {
  constructor(container, patientId, role, onBack) {
    this.container = container;
    this.patientId = patientId;
    this.role = role;
    this.onBack = onBack;
    this.render();
  }

  async render() {
    this.container.innerHTML = `
      <div>
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border);margin-bottom:24px">
          <div style="display:flex;gap:24px;align-items:center">
            <button class="btn btn-secondary" id="btn-back">← Back</button>
            <strong>Patient Overview</strong>
          </div>
          <div style="display:flex;gap:8px">
            ${this.role === 'dentist' || this.role === 'admin' ? '<button class="btn btn-primary" id="btn-dental">🦷 Dental Chart</button>' : ''}
            ${this.role === 'orthopedist' || this.role === 'admin' ? '<button class="btn btn-primary" id="btn-skeleton">🦴 Skeleton</button>' : ''}
          </div>
        </nav>
        <div id="overview-body" class="flex flex-col gap-lg"></div>
      </div>
    `;
    this.container.querySelector('#btn-back').onclick = this.onBack;
    if (this.role === 'dentist' || this.role === 'admin') {
      this.container.querySelector('#btn-dental').onclick = () => {
        new DentalChartPage(this.container, this.patientId, this.role, () => this.render());
      };
    }
    if (this.role === 'orthopedist' || this.role === 'admin') {
      this.container.querySelector('#btn-skeleton').onclick = () => {
        new SkeletonPage(this.container, this.patientId, this.role, () => this.render());
      };
    }

    const body = this.container.querySelector('#overview-body');
    body.innerHTML = '<p class="text-secondary">Loading...</p>';

    let overview;
    try {
      overview = await apiCall(`/api/patients/${this.patientId}/overview`);
    } catch (e) {
      body.innerHTML = `<p style="color:var(--color-danger)">Failed to load: ${e.message}</p>`;
      return;
    }

    let allergies = [], meds = [], history = [];
    try { allergies = await apiCall(`/api/patients/${this.patientId}/allergies`); } catch {}
    try { meds = await apiCall(`/api/patients/${this.patientId}/medications?status=active`); } catch {}
    try { history = await apiCall(`/api/patients/${this.patientId}/medical-history`); } catch {}

    body.innerHTML = `
      <div class="card">
        <h2>${overview.patient_name}</h2>
        <p class="text-secondary">${overview.summary}</p>
      </div>

      <div class="grid-3">
        <div class="card">
          <h4>Active Medications</h4>
          <p style="font-size:32px;font-weight:700;color:var(--color-primary)">${overview.active_medications}</p>
          <ul style="margin-top:8px;list-style:none">
            ${meds.slice(0, 5).map(m => `<li>• ${m.drug_name} ${m.dosage || ''} ${m.frequency || ''}</li>`).join('') || '<li class="text-secondary">None</li>'}
          </ul>
        </div>
        <div class="card">
          <h4>Allergies</h4>
          <p style="font-size:32px;font-weight:700;color:var(--color-warning)">${overview.active_allergies}</p>
          <ul style="margin-top:8px;list-style:none">
            ${allergies.slice(0, 5).map(a => `<li>• ${a.allergen} <span class="text-secondary">(${a.severity})</span></li>`).join('') || '<li class="text-secondary">None</li>'}
          </ul>
        </div>
        <div class="card">
          <h4>Chronic Conditions</h4>
          <p style="font-size:32px;font-weight:700;color:var(--color-danger)">${overview.chronic_conditions}</p>
          <ul style="margin-top:8px;list-style:none">
            ${history.slice(0, 5).map(h => `<li>• ${h.condition_name} <span class="text-secondary">(${h.status})</span></li>`).join('') || '<li class="text-secondary">None</li>'}
          </ul>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <h4>Dental States</h4>
          <ul style="list-style:none">
            ${Object.entries(overview.dental_state_breakdown).map(([k, v]) => `<li>${k}: ${v}</li>`).join('')}
          </ul>
        </div>
        <div class="card">
          <h4>Skeleton States</h4>
          <ul style="list-style:none">
            ${Object.entries(overview.skeleton_state_breakdown).map(([k, v]) => `<li>${k}: ${v}</li>`).join('') || '<li class="text-secondary">No events recorded</li>'}
          </ul>
        </div>
      </div>

      <div class="card">
        <h4>Recent Events</h4>
        ${overview.recent_events.length === 0 ? '<p class="text-secondary">No recent events</p>' : `
          <table style="width:100%;margin-top:8px">
            <thead><tr><th style="text-align:left">Date</th><th style="text-align:left">Type</th><th style="text-align:left">Detail</th></tr></thead>
            <tbody>
              ${overview.recent_events.map(e => `
                <tr><td>${e.date}</td><td>${e.type}</td><td>${e.label} ${e.notes ? `— ${e.notes}` : ''}</td></tr>
              `).join('')}
            </tbody>
          </table>
        `}
      </div>
    `;
  }
}
