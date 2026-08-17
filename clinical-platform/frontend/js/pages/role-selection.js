// js/pages/role-selection.js
export class RoleSelection {
  constructor(container, onSelect) {
    this.container = container;
    this.onSelect = onSelect;
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80vh;gap:32px">
        <h1 style="font-size:28px;font-weight:700">Clinical Platform</h1>
        <p style="color:var(--color-text-secondary);font-size:16px">What type of doctor are you?</p>
        <div style="display:flex;gap:24px">
          <div class="card role-card" id="select-dentist">
            <span class="emoji">🦷</span>
            <strong>Dentist</strong>
          </div>
          <div class="card role-card" id="select-orthopedist">
            <span class="emoji">🦴</span>
            <strong>Orthopedist</strong>
          </div>
        </div>
      </div>
    `;
    this.container.querySelector('#select-dentist').onclick = () => this.onSelect('dentist');
    this.container.querySelector('#select-orthopedist').onclick = () => this.onSelect('orthopedist');
  }
}