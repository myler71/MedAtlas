// js/components/skeleton-svg.js
import { apiCall } from '../api.js';

const STATE_CLASSES = {
  normal: 'skeleton-state-normal',
  fracture: 'skeleton-state-fracture',
  under_treatment: 'skeleton-state-under_treatment',
  follow_up: 'skeleton-state-follow_up',
  healing: 'skeleton-state-healing',
  surgical: 'skeleton-state-surgical',
  chronic: 'skeleton-state-chronic',
  treated: 'skeleton-state-treated',
};

export class SkeletonSVG {
  constructor(container, patientId, onSelectBone) {
    this.container = container;
    this.patientId = patientId;
    this.onSelectBone = onSelectBone;
    this.bones = [];
    this.regions = [];
  }

  async load() {
    const data = await apiCall(`/api/patients/${this.patientId}/skeleton`);
    this.regions = data.body_regions;
    this.bones = data.body_regions.flatMap(r => r.bones.map(b => ({ ...b, region_name: r.region_name, region_id: r.id })));
    this.render();
  }

  render() {
    const html = `
      <div class="skeleton-container">
        <svg viewBox="0 0 300 460" width="400" height="500" class="skeleton-svg-container">
          ${this.regions.map(r => {
            // Find the worst (most severe) bone state in this region to color it
            const states = r.bones.map(b => b.state);
            const worst = this._worstState(states);
            const cls = STATE_CLASSES[worst] || STATE_CLASSES.normal;
            return `<path class="bone-region ${cls}" data-region-id="${r.id}" d="${r.svg_path}" />`;
          }).join('')}
        </svg>
      </div>
      <div class="skeleton-legend">
        ${Object.entries(STATE_CLASSES).map(([key, cls]) => `
          <div class="skeleton-legend-item">
            <div class="skeleton-legend-swatch ${cls}"></div>
            <span>${key.replace(/_/g, ' ')}</span>
          </div>
        `).join('')}
      </div>
    `;
    this.container.innerHTML = html;
    this.container.querySelectorAll('.bone-region').forEach(el => {
      el.onclick = () => {
        const regionId = el.dataset.regionId;
        // Open the first bone in this region (or show all)
        const region = this.regions.find(r => r.id === regionId);
        if (region && region.bones.length > 0) this.onSelectBone(region.bones[0]);
      };
    });
  }

  _worstState(states) {
    const priority = ['fracture', 'surgical', 'under_treatment', 'follow_up', 'chronic', 'healing', 'treated', 'normal'];
    for (const p of priority) if (states.includes(p)) return p;
    return 'normal';
  }
}
