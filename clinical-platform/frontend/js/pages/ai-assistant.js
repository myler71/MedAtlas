// js/pages/ai-assistant.js
import { apiCall } from '../api.js';

export class AIAssistantPage {
  constructor(container, patientId, role, onBack) {
    this.container = container;
    this.patientId = patientId;
    this.role = role;
    this.onBack = onBack;
    this.history = [];
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;height:100vh;max-height:90vh">
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--color-border)">
          <div style="display:flex;gap:24px;align-items:center">
            <button class="btn btn-secondary" id="btn-back">← Back</button>
            <strong>AI Patient Assistant</strong>
          </div>
        </nav>
        <div id="chat-history" style="flex:1;overflow-y:auto;padding:24px"></div>
        <form id="chat-form" style="padding:16px 0;border-top:1px solid var(--color-border);display:flex;gap:8px">
          <input class="input" id="msg-input" placeholder="Ask about this patient..." style="flex:1" />
          <button type="submit" class="btn btn-primary">Send</button>
        </form>
      </div>
    `;
    this.container.querySelector('#btn-back').onclick = this.onBack;
    this.container.querySelector('#chat-form').onsubmit = (e) => this.send(e);
    this.historyEl = this.container.querySelector('#chat-history');

    // Initial assistant message
    this.addAssistantMessage('I can answer questions about this patient\'s clinical record. Try asking about their allergies, medications, or recent procedures.');
  }

  addUserMessage(text) {
    this.history.push({ role: 'user', text });
    this.renderMessage('user', text);
  }

  addAssistantMessage(text) {
    this.history.push({ role: 'assistant', text });
    this.renderMessage('assistant', text);
  }

  renderMessage(role, text) {
    const div = document.createElement('div');
    div.style.cssText = `margin-bottom:12px;padding:12px;border-radius:8px;max-width:80%;${
      role === 'user'
        ? 'background:var(--color-primary);color:white;margin-left:auto'
        : 'background:var(--color-surface);border:1px solid var(--color-border)'
    }`;
    div.innerHTML = text;
    this.historyEl.appendChild(div);
    this.historyEl.scrollTop = this.historyEl.scrollHeight;
  }

  renderStructured(data) {
    const div = document.createElement('div');
    div.style.cssText = 'margin-bottom:12px;padding:12px;border-radius:8px;background:var(--color-surface);border:1px solid var(--color-border);max-width:85%';
    const citations = data.citations || [];
    div.innerHTML = `
      <div style="margin-bottom:8px"><strong>${data.patient_name}</strong></div>
      <div class="text-secondary" style="font-size:14px;margin-bottom:8px">${data.summary}</div>
      ${data.current_medications?.length ? `
        <details style="margin-top:8px"><summary><strong>Medications (${data.current_medications.length})</strong></summary>
          <ul>${data.current_medications.map(m => `<li>${m.drug} ${m.dosage || ''} ${m.frequency || ''} <em>(${m.status})</em></li>`).join('')}</ul>
        </details>
      ` : ''}
      ${data.allergies?.length ? `
        <details style="margin-top:8px"><summary><strong>Allergies (${data.allergies.length})</strong></summary>
          <ul>${data.allergies.map(a => `<li>${a.allergen} <em>(${a.severity})</em> ${a.reaction || ''}</li>`).join('')}</ul>
        </details>
      ` : ''}
      ${data.recent_procedures?.length ? `
        <details style="margin-top:8px"><summary><strong>Recent Procedures (${data.recent_procedures.length})</strong></summary>
          <ul>${data.recent_procedures.map(p => `<li>${p.date} — ${p.kind}: ${p.detail}</li>`).join('')}</ul>
        </details>
      ` : ''}
      ${data.important_notes?.length ? `
        <div style="margin-top:8px;padding:8px;background:#fef3c7;border-radius:4px;font-size:13px">
          ⚠️ ${data.important_notes.join(' • ')}
        </div>
      ` : ''}
      ${data.missing_information?.length ? `
        <div style="margin-top:8px;padding:8px;background:#fee2e2;border-radius:4px;font-size:13px">
          Missing: ${data.missing_information.join(', ')}
        </div>
      ` : ''}
      ${citations.length ? `
        <details style="margin-top:8px"><summary><strong>Citations (${citations.length})</strong></summary>
          <ol style="font-size:12px">${citations.map(c => `
            <li>${c.title || c.source}${c.url ? ` — <a href="${c.url}" target="_blank" rel="noopener">${c.url.substring(0, 60)}...</a>` : ''}
              <div style="color:var(--color-text-secondary)">${c.evidence_excerpt || ''}</div>
            </li>
          `).join('')}</ol>
        </details>
      ` : ''}
    `;
    this.historyEl.appendChild(div);
    this.historyEl.scrollTop = this.historyEl.scrollHeight;
  }

  async send(e) {
    e.preventDefault();
    const input = this.container.querySelector('#msg-input');
    const message = input.value.trim();
    if (!message) return;
    input.value = '';
    this.addUserMessage(message);
    try {
      const data = await apiCall('/api/chat/patient', {
        method: 'POST',
        body: JSON.stringify({ patient_id: this.patientId, message }),
      });
      this.renderStructured(data);
    } catch (e) {
      this.addAssistantMessage(`Error: ${e.message}`);
    }
  }
}
