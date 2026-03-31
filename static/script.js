const app = {
    sessionId: null,
    viewerSource: null,
    viewerTarget: null,

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

    async compareServers() {
        this.setLoading("Comparing Source and Target Servers by Key");
        try {
            const res = await fetch('/api/compare');
            const data = await res.json();
            
            if (data.error) {
                this.renderError(data.error);
                return;
            }

            let html = `<h2>Server Comparison Results</h2>`;
            
            if (data.modified.length === 0 && data.missing_in_target.length === 0) {
                html += `<div style="padding:1rem; background:rgba(16, 185, 129, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--success)">
                    <strong>Perfect Match:</strong> No differences found between the servers!
                </div>`;
            } else {
                html += `<p>Found differences between the Source and Target environments:</p>`;
            }

            // Build Modified List with custom buttons
            if (data.modified.length > 0) {
                html += `<div class="result-group">
                    <h3>Modified (Content Mismatch) <span class="badge badge-warning">${data.modified.length}</span></h3>
                    <ul class="result-list">`;
                
                if (!window._diffData) window._diffData = [];
                data.modified.forEach((item, index) => {
                    window._diffData[index] = item;
                    html += `
                        <li>
                            <div>
                                <strong style="display:block;">${item.resource}</strong> 
                                <span style="color:var(--text-secondary); font-size:0.8rem;">Key: ${item.key} | Type: ${item.type}</span>
                            </div>
                            ${item.type === 'process' 
                                ? `<button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size:0.85rem;" onclick="app.openDiffModal(${index})">View Diagram diff</button>` 
                                : `<span style="font-size:0.8rem; color:var(--text-secondary)">DMN (Check CLI for text diff)</span>`}
                        </li>
                    `;
                });
                html += `</ul></div>`;
            }

            html += this.renderList("Missing in Target", data.missing_in_target, "badge-danger", false, "resource", "key");

            document.getElementById('results-container').innerHTML = html;
        } catch (e) {
            this.renderError(e.message);
        }
    },

    openDiffModal(index) {
        const item = window._diffData[index];
        document.getElementById('modal-title').innerText = `Visual Comparison: ${item.resource}`;
        document.getElementById('diff-modal').classList.remove('hidden');

        if (!this.viewerSource) {
            this.viewerSource = new BpmnJS({ container: '#canvas-source', height: '100%', width: '100%' });
        }
        if (!this.viewerTarget) {
            this.viewerTarget = new BpmnJS({ container: '#canvas-target', height: '100%', width: '100%' });
        }

        this.viewerSource.importXML(item.source_xml)
            .then(() => { this.viewerSource.get('canvas').zoom('fit-viewport'); })
            .catch(err => console.error("Source XML Import Error:", err));
            
        this.viewerTarget.importXML(item.target_xml)
            .then(() => { this.viewerTarget.get('canvas').zoom('fit-viewport'); })
            .catch(err => console.error("Target XML Import Error:", err));
    },

    closeModal() {
        document.getElementById('diff-modal').classList.add('hidden');
        if (this.viewerSource) this.viewerSource.clear();
        if (this.viewerTarget) this.viewerTarget.clear();
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
