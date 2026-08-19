// js/pages/skeleton.js
import { apiCall } from '../api.js';
import { SkeletonSVG } from '../components/skeleton-svg.js';

export class SkeletonPage {
  constructor(container, patientId, role, onBack) {
    this.container = container;
    this.patientId = patientId;
    this.role = role;
    this.onBack = onBack;
    this.selectedBone = null;
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div>
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border);margin-bottom:24px">
          <div style="display:flex;gap:24px;align-items:center">
            <button class="btn btn-secondary" id="btn-back">← Back</button>
            <strong>Skeleton — Patient ${this.patientId.substring(0, 8)}</strong>
          </div>
        </nav>
        <div id="skeleton-host" class="card"></div>
        <div id="bone-detail" class="bone-detail-panel"></div>
      </div>
    `;
    this.container.querySelector('#btn-back').onclick = this.onBack;

    const host = this.container.querySelector('#skeleton-host');
    this.skel = new SkeletonSVG(host, this.patientId, (bone) => this.selectBone(bone));
    this.skel.load();
  }

  async selectBone(bone) {
    this.selectedBone = bone;
    const panel = this.container.querySelector('#bone-detail');
    panel.classList.add('open');

    let events = [];
    try {
      events = await apiCall(`/api/patients/${this.patientId}/skeleton/bones/${bone.id}/events`);
    } catch (e) { events = []; }

    const eventTypeOptions = ['exam','fracture','sprain','dislocation','surgery','implant','arthritis','healing','follow_up','other']
      .map(t => `<option value="${t}">${t}</option>`).join('');

    const healingOptions = ['', 'acute','recovering','healed','chronic','unknown']
      .map(h => `<option value="${h}">${h || '— none —'}</option>`).join('');

    panel.innerHTML = `
      <h3>${bone.bone_name}</h3>
      <p class="text-secondary">${bone.region_name || ''}${bone.side ? ` • ${bone.side}` : ''}</p>
      <p>Current state: <strong>${bone.state}</strong></p>

      <h4 style="margin-top:24px">Add Event</h4>
      <form id="event-form" class="flex flex-col gap-md" style="margin-top:8px">
        <div>
          <label class="label">Event Type</label>
          <select class="input" name="event_type" required>${eventTypeOptions}</select>
        </div>
        <div>
          <label class="label">Diagnosis</label>
          <input class="input" name="diagnosis" />
        </div>
        <div>
          <label class="label">Treatment</label>
          <input class="input" name="treatment" />
        </div>
        <div>
          <label class="label">Healing Status</label>
          <select class="input" name="healing_status">${healingOptions}</select>
        </div>
        <div>
          <label class="label">Notes</label>
          <textarea class="input" name="notes" rows="3"></textarea>
        </div>
        <button type="submit" class="btn btn-primary">Add Event</button>
      </form>

      <h4 style="margin-top:24px">Event History</h4>
      <div>
        ${events.length === 0 ? '<p class="text-secondary">No events yet.</p>' : events.map(e => `
          <div style="padding:8px 0;border-bottom:1px solid var(--color-border)">
            <strong>${e.event_type}</strong> ${e.diagnosis ? `— ${e.diagnosis}` : ''}
            <div class="text-secondary" style="font-size:12px">${e.event_date}${e.healing_status ? ` • ${e.healing_status}` : ''}</div>
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
      // Strip empty healing_status
      if (!data.healing_status) delete data.healing_status;
      await apiCall(`/api/patients/${this.patientId}/skeleton/bones/${bone.id}/events`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      await this.skel.load();
      const fresh = this.skel.bones.find(b => b.id === bone.id);
      if (fresh) this.selectBone(fresh);
    };
  }
}
