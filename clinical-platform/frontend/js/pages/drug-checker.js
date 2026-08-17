// js/pages/drug-checker.js
import { apiCall } from '../api.js';

export class DrugCheckerPage {
  constructor(container, role, onBack) {
    this.container = container;
    this.role = role;
    this.onBack = onBack;
    this.drugs = [];
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div>
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border);margin-bottom:24px">
          <div style="display:flex;gap:24px;align-items:center">
            <button class="btn btn-secondary" id="btn-back">← Back</button>
            <strong>Drug Interaction Checker</strong>
          </div>
        </nav>
        <div class="card">
          <p class="text-secondary">Add 2 or more drugs to check for known interactions. Powered by RxNorm.</p>
          <div class="flex gap-md mt-md">
            <input class="input" id="drug-input" placeholder="Drug name (e.g., warfarin)" style="flex:1" />
            <button class="btn btn-primary" id="btn-add">Add Drug</button>
          </div>
          <div id="drug-list" class="flex gap-sm mt-md" style="flex-wrap:wrap"></div>
          <button class="btn btn-primary btn-lg mt-md" id="btn-check" disabled>Check Interactions</button>
          <div id="results" class="mt-md"></div>
        </div>
      </div>
    `;
    this.container.querySelector('#btn-back').onclick = this.onBack;
    this.container.querySelector('#btn-add').onclick = () => this.addDrug();
    this.container.querySelector('#drug-input').onkeydown = (e) => { if (e.key === 'Enter') this.addDrug(); };
    this.container.querySelector('#btn-check').onclick = () => this.check();
    this.renderDrugList();
  }

  addDrug() {
    const input = this.container.querySelector('#drug-input');
    const val = input.value.trim();
    if (!val) return;
    if (!this.drugs.includes(val)) this.drugs.push(val);
    input.value = '';
    this.renderDrugList();
  }

  removeDrug(d) {
    this.drugs = this.drugs.filter(x => x !== d);
    this.renderDrugList();
  }

  renderDrugList() {
    const list = this.container.querySelector('#drug-list');
    list.innerHTML = this.drugs.map(d => `
      <div style="padding:6px 12px;background:var(--color-bg);border-radius:16px;display:flex;gap:8px;align-items:center">
        <span>${d}</span>
        <button class="btn" style="padding:0 6px;color:var(--color-danger)" data-remove="${d}">×</button>
      </div>
    `).join('');
    list.querySelectorAll('[data-remove]').forEach(btn => {
      btn.onclick = () => this.removeDrug(btn.dataset.remove);
    });
    this.container.querySelector('#btn-check').disabled = this.drugs.length < 2;
  }

  async check() {
    const results = this.container.querySelector('#results');
    results.innerHTML = '<p class="text-secondary">Checking...</p>';
    try {
      const data = await apiCall('/api/drug-interactions/check', {
        method: 'POST',
        body: JSON.stringify({ drugs: this.drugs }),
      });
      this.renderResults(data);
    } catch (e) {
      results.innerHTML = `<p style="color:var(--color-danger)">${e.message}</p>`;
    }
  }

  renderResults(data) {
    const results = this.container.querySelector('#results');
    const interactions = data.interactions || [];
    const warnings = data.warnings || [];
    const resolved = data.drugs_resolved || [];

    results.innerHTML = `
      <h4 style="margin-top:24px">Resolved Drugs</h4>
      <ul>
        ${resolved.map(r => `<li><strong>${r.input}</strong> → ${r.name || 'NOT FOUND'}${r.drug_class ? ` <span class="text-secondary">(${r.drug_class})</span>` : ''}</li>`).join('')}
      </ul>

      ${warnings.length > 0 ? `<p style="color:var(--color-warning);margin-top:8px">⚠️ ${warnings.join('; ')}</p>` : ''}

      <h4 style="margin-top:24px">Interactions Found: ${interactions.length}</h4>
      ${interactions.length === 0 ? '<p class="text-secondary">No known interactions in the database. This does NOT mean the combination is safe — always consult clinical references.</p>' : ''}
      ${interactions.map(i => `
        <div class="card mt-md" style="border-left:4px solid ${this.severityColor(i.severity)}">
          <div style="display:flex;justify-content:space-between">
            <strong>${i.drug_a} + ${i.drug_b}</strong>
            <span style="color:${this.severityColor(i.severity)};font-weight:700">${i.severity.toUpperCase()}</span>
          </div>
          ${i.mechanism ? `<p class="text-secondary mt-md"><strong>Mechanism:</strong> ${i.mechanism}</p>` : ''}
          ${i.clinical_significance ? `<p><strong>Clinical significance:</strong> ${i.clinical_significance}</p>` : ''}
          <p class="text-secondary" style="font-size:12px;margin-top:8px">Source: ${i.evidence_source || 'unknown'} (${i.evidence_strength || 'unknown'})</p>
        </div>
      `).join('')}
    `;
  }

  severityColor(s) {
    return {
      minor: '#16a34a',
      moderate: '#d97706',
      major: '#dc2626',
      contraindicated: '#7f1d1d',
    }[s] || '#64748b';
  }
}
