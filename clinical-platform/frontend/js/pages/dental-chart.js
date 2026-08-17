// js/pages/dental-chart.js
import { apiCall } from '../api.js';
import { Odontogram } from '../components/odontogram.js';

export class DentalChartPage {
  constructor(container, patientId, role, onBack) {
    this.container = container;
    this.patientId = patientId;
    this.role = role;
    this.onBack = onBack;
    this.selectedTooth = null;
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div>
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border);margin-bottom:24px">
          <div style="display:flex;gap:24px;align-items:center">
            <button class="btn btn-secondary" id="btn-back">← Back</button>
            <strong>Dental Chart — Patient ${this.patientId.substring(0, 8)}</strong>
          </div>
        </nav>
        <div id="odontogram-host" class="card"></div>
        <div id="tooth-detail" class="tooth-detail-panel"></div>
      </div>
    `;
    this.container.querySelector('#btn-back').onclick = this.onBack;

    const host = this.container.querySelector('#odontogram-host');
    this.odonto = new Odontogram(host, this.patientId, (tooth) => this.selectTooth(tooth));
    this.odonto.load();
  }

  async selectTooth(tooth) {
    this.selectedTooth = tooth;
    const panel = this.container.querySelector('#tooth-detail');
    panel.classList.add('open');

    // Load event history
    let events = [];
    try {
      events = await apiCall(`/api/patients/${this.patientId}/dental-chart/teeth/${tooth.id}/events`);
    } catch (e) { events = []; }

    const eventTypeOptions = ['exam','caries','restoration','extraction','root_canal','crown','implant','fracture','cleaning','other']
      .map(t => `<option value="${t}">${t}</option>`).join('');

    panel.innerHTML = `
      <h3>Tooth ${tooth.tooth_number_universal || tooth.tooth_number_fdi}</h3>
      <p class="text-secondary">FDI ${tooth.tooth_number_fdi} • ${tooth.dentition_type}</p>
      <p>Current state: <strong>${tooth.state}</strong></p>

      <h4 style="margin-top:24px">Add Event</h4>
      <form id="event-form" class="flex flex-col gap-md" style="margin-top:8px">
        <div>
          <label class="label">Event Type</label>
          <select class="input" name="event_type" required>${eventTypeOptions}</select>
        </div>
        <div>
          <label class="label">Procedure</label>
          <input class="input" name="procedure_name" />
        </div>
        <div>
          <label class="label">Notes</label>
          <textarea class="input" name="notes" rows="3"></textarea>
        </div>
        <button type="submit" class="btn btn-primary">Add Event</button>
      </form>

      <h4 style="margin-top:24px">Event History</h4>
      <div class="event-timeline">
        ${events.length === 0 ? '<p class="text-secondary">No events yet.</p>' : events.map(e => `
          <div class="event-item">
            <strong>${e.event_type}</strong>
            ${e.procedure_name ? `— ${e.procedure_name}` : ''}
            <div class="text-secondary" style="font-size:12px">${e.event_date}</div>
            ${e.notes ? `<div style="margin-top:4px">${e.notes}</div>` : ''}
          </div>
        `).join('')}
      </div>

      <button class="btn btn-secondary mt-md" id="btn-close-panel">Close</button>
    `;
    panel.querySelector('#btn-close-panel').onclick = () => panel.classList.remove('open');
    panel.querySelector('#event-form').onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const data = Object.fromEntries(fd);
      await apiCall(`/api/patients/${this.patientId}/dental-chart/teeth/${tooth.id}/events`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      // Reload odontogram + panel
      await this.odonto.load();
      const fresh = this.odonto.teeth.find(t => t.id === tooth.id);
      if (fresh) this.selectTooth(fresh);
    };
  }
}
