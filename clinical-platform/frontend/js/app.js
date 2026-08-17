// js/app.js
import { RoleSelection } from './pages/role-selection.js';
import { AuthPage } from './pages/auth.js';
import { Dashboard } from './pages/dashboard.js';

class App {
  constructor() {
    this.currentRole = localStorage.getItem('role');
    this.token = localStorage.getItem('token');
    this.render();
  }

  render() {
    const app = document.getElementById('app');
    if (!this.currentRole) {
      new RoleSelection(app, (role) => {
        this.currentRole = role;
        localStorage.setItem('role', role);
        this.render();
      });
    } else if (!this.token) {
      new AuthPage(app, this.currentRole, (token) => {
        this.token = token;
        localStorage.setItem('token', token);
        this.render();
      });
    } else {
      new Dashboard(app, this.currentRole, this.token);
    }
  }
}

new App();