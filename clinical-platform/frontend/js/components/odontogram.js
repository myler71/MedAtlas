// js/components/odontogram.js
// Renders a simple anatomical tooth SVG. Quadrant and position determine shape.
import { apiCall } from '../api.js';

const TOOTH_STATE_CLASSES = {
  healthy: 'tooth-state-healthy',
  caries: 'tooth-state-caries',
  restored: 'tooth-state-restored',
  missing: 'tooth-state-missing',
  extracted: 'tooth-state-extracted',
  root_canal: 'tooth-state-root_canal',
  crown: 'tooth-state-crown',
  implant: 'tooth-state-implant',
  fractured: 'tooth-state-fractured',
};

export class Odontogram {
  constructor(container, patientId, onSelectTooth) {
    this.container = container;
    this.patientId = patientId;
    this.onSelectTooth = onSelectTooth;
    this.teeth = [];
  }

  async load() {
    const data = await apiCall(`/api/patients/${this.patientId}/dental-chart`);
    this.teeth = data.teeth;
    this.render();
  }

  render() {
    // Group teeth by quadrant
    const byQuad = { 1: [], 2: [], 3: [], 4: [] };
    for (const t of this.teeth) byQuad[t.quadrant].push(t);

    // Order rows: Q1+Q2 (upper), Q3+Q4 (lower). Quadrant numbers in FDI: UR=1, UL=2, LL=3, LR=4.
    const rows = [
      { label: 'Upper', quadA: byQuad[1], quadB: byQuad[2] },
      { label: 'Lower', quadA: byQuad[3], quadB: byQuad[4] },
    ];

    const html = rows.map((r, idx) => `
      <div class="odontogram-row" style="${idx === 0 ? 'margin-bottom:24px' : ''}">
        ${this.renderRow(r.quadA, true)}
        ${this.renderRow(r.quadB, false)}
      </div>
    `).join('');

    this.container.innerHTML = `<div class="odontogram-container">${html}</div>`;

    // Attach click handlers
    this.container.querySelectorAll('.tooth-svg').forEach(el => {
      el.onclick = () => {
        const toothId = el.dataset.toothId;
        const tooth = this.teeth.find(t => t.id === toothId);
        if (tooth) this.onSelectTooth(tooth);
      };
    });
  }

  renderRow(teeth, isRightSide) {
    // Right-side: position 8 (molar) leftmost, position 1 (central incisor) rightmost
    // For UL quadrant 2 (left side of mouth, but rendered on right): reverse
    const sorted = [...teeth].sort((a, b) => b.position_in_quadrant - a.position_in_quadrant);
    return sorted.map(t => {
      const stateClass = TOOTH_STATE_CLASSES[t.state] || TOOTH_STATE_CLASSES.healthy;
      const label = t.tooth_number_universal || t.tooth_number_fdi;
      return `
        <svg class="tooth-svg ${stateClass}" data-tooth-id="${t.id}" width="36" height="50" viewBox="0 0 36 50">
          <path d="M 8 8 Q 18 4 28 8 L 28 30 Q 28 42 22 46 Q 18 48 14 46 Q 8 42 8 30 Z" />
          <text class="tooth-label" x="18" y="56">${label}</text>
        </svg>
      `;
    }).join('');
  }
}
