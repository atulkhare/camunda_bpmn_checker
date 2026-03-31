const app = {
    sessionId: null,

    init() {
        this.fetchConfig();
    },

    async fetchConfig() {
        try {
            const res = await fetch('/api/config');
            const data = await res.json();
            document.getElementById('config-source').value = data.SOURCE_CAMUNDA_REST_URL;
            document.getElementById('config-target').value = data.TARGET_CAMUNDA_REST_URL;
            document.getElementById('config-git').value = data.GIT_REPO_PATH;
        } catch (e) {
            console.error(e);
        }
    },

    setLoading(text) {
        document.getElementById('results-container').innerHTML = `
            <div class="empty-state loading">
                <p>⚙️ ${text}...</p>
            </div>
        `;
    },

    async runCheck() {
        this.setLoading("Comparing Camunda and Git");
        try {
            const res = await fetch('/api/check');
            const data = await res.json();
            console.log(data);

            if (data.error) {
                this.renderError(data.error);
                return;
            }

            let html = `<h2>Check Results</h2>`;
            html += `<p>Total Deployments Checked: <strong>${data.deployments_checked}</strong></p>`;
            
            html += this.renderList("Matches", data.matches, "badge-success");
            html += this.renderList("Mismatches", data.mismatches, "badge-danger");
            html += this.renderList("Missing in Git", data.missing_in_git, "badge-warning", true);

            document.getElementById('results-container').innerHTML = html;
        } catch (e) {
            this.renderError(e.message);
        }
    },

    async prepareSync() {
        this.setLoading("Fetching latest definitions securely");
        try {
            const res = await fetch('/api/sync/prepare');
            const data = await res.json();
            
            if (res.status !== 200) throw new Error(data.error || "Unknown Error");

            this.sessionId = data.session_id;

            let html = `<h2>Sync Preview</h2>`;
            html += `<p>Please review the deployments grouped by name below. If everything looks correct, confirm the sync.</p>`;
            
            for (const [depName, files] of Object.entries(data.deployments)) {
                html += `
                    <div class="result-group">
                        <h3>📦 ${depName} <span class="badge" style="background: rgba(255,255,255,0.1);">${files.length} files</span></h3>
                        <ul class="result-list">
                            ${files.map(f => `<li><span>${f}</span></li>`).join('')}
                        </ul>
                    </div>
                `;
            }

            html += `
                <div class="sync-confirm-box">
                    <p style="margin-bottom: 1rem;">Ready to deploy to target server?</p>
                    <button class="btn btn-primary" onclick="app.executeSync()" style="width: 100%;">
                        🚀 Confirm & Sync to Target
                    </button>
                </div>
            `;

            document.getElementById('results-container').innerHTML = html;

        } catch (e) {
            this.renderError(e.message);
        }
    },

    async executeSync() {
        this.setLoading("Deploying bundles to Target Camunda Engine");
        try {
            const res = await fetch('/api/sync/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: this.sessionId })
            });
            const data = await res.json();
            
            let html = `<h2>Deployment Complete</h2>`;
            
            if (data.failed && data.failed.length > 0) {
                html += `<div style="padding:1rem; background:rgba(239, 68, 68, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--danger)">
                    <strong>Warning:</strong> Some deployments failed.
                </div>`;
                html += this.renderList("Failed Deployments", data.failed, "badge-danger", false, "deployment_name");
            } else {
                html += `<div style="padding:1rem; background:rgba(16, 185, 129, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--success)">
                    <strong>Success!</strong> All bundles were deployed successfully.
                </div>`;
            }

            if (data.success && data.success.length > 0) {
                html += this.renderList("Successful Deployments", data.success, "badge-success", false, "deployment_name", "id");
            }

            document.getElementById('results-container').innerHTML = html;

        } catch (e) {
            this.renderError(e.message);
        }
    },

    renderList(title, items, badgeClass, isMissing = false, primaryKey="resource", secondaryKey=null) {
        if (!items || items.length === 0) return '';
        return `
            <div class="result-group">
                <h3>${title} <span class="badge ${badgeClass}">${items.length}</span></h3>
                <ul class="result-list">
                    ${items.map(item => `
                        <li>
                            <strong>${item[primaryKey] || "Unknown"}</strong> 
                            ${item[secondaryKey] ? `<span style="color:var(--text-secondary); font-size:0.8rem;">ID: ${item[secondaryKey]}</span>` : ''}
                            ${item.error ? `<span style="color:var(--danger)">${item.error}</span>` : ''}
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    },

    renderError(msg) {
        document.getElementById('results-container').innerHTML = `
            <div style="color: var(--danger); background: rgba(239, 68, 68, 0.1); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--danger);">
                <h3>🚨 Error</h3>
                <p>${msg}</p>
            </div>
        `;
    }
};

document.addEventListener('DOMContentLoaded', () => app.init());
