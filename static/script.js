const app = {
    sessionId: null,
    viewerSource: null,
    viewerTarget: null,

    init() {
        this.fetchConfig();
        this.fetchMappings();
    },

    switchTab(tabId) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
        document.getElementById(`btn-tab-${tabId}`).classList.add('active');
        document.getElementById(`tab-${tabId}`).style.display = 'block';
        if (tabId !== 'config') {
            document.getElementById('results-container').innerHTML = '<div class="empty-state"><p>Results will be displayed here</p></div>';
        }
    },

    async fetchConfig() {
        try {
            const res = await fetch('/api/config');
            const data = await res.json();
            if(document.getElementById('config-source')) document.getElementById('config-source').value = data.SOURCE_CAMUNDA_REST_URL || '';
            if(document.getElementById('config-target-base')) document.getElementById('config-target-base').value = data.CAMUNDA_BASE_URL || 'http://localhost:8080';
            if(document.getElementById('config-folder')) document.getElementById('config-folder').value = data.TECHNICAL_FOLDER_PATH || '';
        } catch (e) {
            console.error(e);
        }
    },

    async fetchMappings() {
        try {
            const res = await fetch('/api/mapping');
            const mappingData = await res.json();
            this.renderMappingEditor(mappingData);
        } catch(e) { console.error(e); }
    },

    renderMappingEditor(mappingData) {
        const container = document.getElementById('mapping-container');
        container.innerHTML = '';
        for (const [appName, contextPath] of Object.entries(mappingData)) {
            container.insertAdjacentHTML('beforeend', this.createMappingRow(appName, contextPath));
        }
    },

    createMappingRow(appName = '', contextPath = '') {
        return `
            <div class="mapping-row">
                <input type="text" placeholder="Application Name (e.g., OrderApp)" value="${appName}" class="map-key">
                <span style="color:var(--text-secondary)">&#10142;</span>
                <input type="text" placeholder="Context Path (e.g., orderApp)" value="${contextPath}" class="map-val">
                <button class="btn-danger" onclick="this.parentElement.remove()">X</button>
            </div>
        `;
    },

    addMappingRow() {
        document.getElementById('mapping-container').insertAdjacentHTML('beforeend', this.createMappingRow());
    },

    async saveMappings() {
        const newMappings = {};
        document.querySelectorAll('.mapping-row').forEach(row => {
            const k = row.querySelector('.map-key').value.trim();
            const v = row.querySelector('.map-val').value.trim();
            if (k && v) newMappings[k] = v;
        });

        try {
            await fetch('/api/mapping', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newMappings)
            });
            alert("Mappings saved successfully!");
        } catch(e) { alert("Error saving mappings"); }
    },

    async runLocalCheck() {
        this.setLoading("Scanning Technical Folder and Comparing with Server endpoints");
        try {
            const baseUrl = document.getElementById('config-target-base').value;
            const res = await fetch(`/api/local-check?baseUrl=${encodeURIComponent(baseUrl)}`);
            if (!res.ok) {
                const text = await res.text();
                throw new Error(`Server Error (${res.status}): ` + text.substring(0, 150));
            }
            const data = await res.json();
            
            if (data.error) {
                this.renderError(data.error);
                return;
            }

            let html = `<h2>Local Folder vs Server Check Results</h2>`;
            html += `<p>Total Applications Checked: <strong>${data.apps_checked || 0}</strong></p>`;
            
            if (data.unmapped_apps && data.unmapped_apps.length > 0) {
                html += `<div style="padding:1rem; background:rgba(245, 158, 11, 0.2); border-radius:8px; margin-bottom:1rem; color:#fbbf24">
                    <strong>Warning:</strong> The following local application folders are not defined in mapping.json and were skipped: 
                    ${data.unmapped_apps.join(', ')}
                </div>`;
            }

            if (data.failed_connections && data.failed_connections.length > 0) {
                html += `<div style="padding:1rem; background:rgba(239, 68, 68, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--danger)">
                    <strong>Connection Errors:</strong> Failed to fetch from the following applications
                    <ul style="margin-top:0.5rem; list-style:disc; padding-left:1.5rem;">
                        ${data.failed_connections.map(e => `<li><b>${e.app}</b>: ${e.error}</li>`).join('')}
                    </ul>
                </div>`;
            }

            if (data.mismatches.length > 0 || data.missing_on_server.length > 0) {
                html += `<div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; padding: 0.75rem; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
                    <button class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.85rem; margin:0;" onclick="app.selectAll(true)">Select All</button>
                    <button class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.85rem; margin:0;" onclick="app.selectAll(false)">Deselect All</button>
                    <span style="color:var(--text-secondary); font-size:0.9rem;">Select items below to dynamically construct custom deployment payload.</span>
                </div>`;
            }

            // Build Modified List with custom buttons for Local vs Server
            if (data.mismatches.length > 0) {
                html += `<div class="result-group">
                    <h3>Modified (Content Mismatch) <span class="badge badge-warning">${data.mismatches.length}</span></h3>
                    <ul class="result-list">`;
                
                if (!window._diffData) window._diffData = [];
                data.mismatches.forEach((item, index) => {
                    window._diffData[index] = item;
                    html += `
                        <li>
                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                <input type="checkbox" class="deploy-checkbox" data-app="${item.app}" data-resource="${item.resource}" checked style="width: 1.1rem; height: 1.1rem; cursor: pointer; flex-shrink: 0; margin-top: 2px;">
                                <div>
                                    <strong style="display:block;">${item.resource}</strong> 
                                    <span style="color:var(--text-secondary); font-size:0.8rem;">App: ${item.app} | Type: ${item.type}</span>
                                </div>
                            </div>
                            ${item.type === 'process' 
                                ? `<button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size:0.85rem;" onclick="app.openDiffModal(${index})">View Diagram diff</button>` 
                                : `<span style="font-size:0.8rem; color:var(--text-secondary)">DMN (Check console diff)</span>`}
                        </li>
                    `;
                });
                html += `</ul></div>`;
            }

            html += this.renderSelectableList("Missing on Server", data.missing_on_server, "badge-danger", "resource", "app");
            html += this.renderList("Matches", data.matches, "badge-success", false, "resource", "app");

            document.getElementById('results-container').innerHTML = html;
        } catch (e) {
            this.renderError(e.message);
        }
    },

    async prepareLocalSync() {
        const selectedItems = [];
        document.querySelectorAll('.deploy-checkbox:checked').forEach(cb => {
            selectedItems.push({
                app: cb.getAttribute('data-app'),
                resource: cb.getAttribute('data-resource')
            });
        });

        if (selectedItems.length === 0) {
            alert("Please select at least one file to deploy!");
            return;
        }

        this.setLoading("Fetching un-synced Local files safely");
        try {
            const res = await fetch('/api/local-sync/prepare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selected_items: selectedItems })
            });
            const data = await res.json();
            
            if (res.status !== 200) throw new Error(data.error || "Unknown Error");

            this.sessionId = data.session_id;

            let html = `<h2>Local Folder Sync Preview</h2>`;
            html += `<p>Please review the missing and modified deployments grouped by Application Name. Each bundle will be deployed to its mapped Context Path.</p>`;
            
            for (const [appName, files] of Object.entries(data.deployments)) {
                html += `
                    <div class="result-group">
                        <h3>📁 ${appName} <span class="badge" style="background: rgba(255,255,255,0.1);">${files.length} files</span></h3>
                        <ul class="result-list">
                            ${files.map(f => `<li><span>${f}</span></li>`).join('')}
                        </ul>
                    </div>
                `;
            }

            html += `
                <div class="sync-confirm-box">
                    <p style="margin-bottom: 1rem;">Ready to dynamically deploy these Local Folders to their respective Servers?</p>
                    <button class="btn btn-primary" onclick="app.executeLocalSync()" style="width: 100%;">
                        🚀 Confirm & Deploy
                    </button>
                </div>
            `;

            document.getElementById('results-container').innerHTML = html;
        } catch (e) {
            this.renderError(e.message);
        }
    },

    async executeLocalSync() {
        this.setLoading("Deploying bundled models across target Server endpoints");
        try {
            const baseUrl = document.getElementById('config-target-base').value;
            const res = await fetch('/api/local-sync/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: this.sessionId, baseUrl: baseUrl })
            });
            const data = await res.json();
            
            let html = `<h2>Dynamic Deployment Complete</h2>`;
            
            if (data.failed && data.failed.length > 0) {
                html += `<div style="padding:1rem; background:rgba(239, 68, 68, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--danger)">
                    <strong>Warning:</strong> Some application deployments failed.
                </div>`;
                html += this.renderList("Failed Deployments", data.failed, "badge-danger", false, "app");
            } else {
                html += `<div style="padding:1rem; background:rgba(16, 185, 129, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--success)">
                    <strong>Success!</strong> All local modifications synced to endpoints successfully.
                </div>`;
            }

            if (data.success && data.success.length > 0) {
                html += this.renderList("Successful Deployments (App Name -> ID)", data.success, "badge-success", false, "app", "id");
            }

            document.getElementById('results-container').innerHTML = html;

        } catch (e) {
            this.renderError(e.message);
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
            const sourceUrl = document.getElementById('config-source').value;
            const targetUrl = document.getElementById('config-target-base').value;
            const res = await fetch(`/api/sync/prepare?sourceUrl=${encodeURIComponent(sourceUrl)}&targetUrl=${encodeURIComponent(targetUrl)}`);
            const data = await res.json();
            
            if (res.status !== 200) throw new Error(data.error || "Unknown Error");

            this.sessionId = data.session_id;

            let html = `<h2>Sync Preview (Multi-App)</h2>`;
            html += `<p>Please review the deployments grouped by application below. If everything looks correct, confirm the sync.</p>`;
            
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
                    <p style="margin-bottom: 1rem;">Ready to dynamically deploy these bundles across their target micro-services?</p>
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
        this.setLoading("Comparing Multi-App Servers by Mapping");
        try {
            const sourceUrl = document.getElementById('config-source').value;
            const targetUrl = document.getElementById('config-target-base').value;
            const res = await fetch(`/api/compare?sourceUrl=${encodeURIComponent(sourceUrl)}&targetUrl=${encodeURIComponent(targetUrl)}`);
            if (!res.ok) {
                const text = await res.text();
                throw new Error(`Server Error (${res.status}): ` + text.substring(0, 150));
            }
            const data = await res.json();
            
            if (data.error) {
                this.renderError(data.error);
                return;
            }

            let html = `<h2>Multi-App Server Comparison Results</h2>`;
            html += `<p>Total Applications Checked: <strong>${data.apps_checked || 0}</strong></p>`;
            
            if (data.failed_connections && data.failed_connections.length > 0) {
                html += `<div style="padding:1rem; background:rgba(239, 68, 68, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--danger)">
                    <strong>Warning:</strong> Could not connect to some mapped endpoints.
                </div>`;
                html += this.renderList("Connection Errors", data.failed_connections, "badge-danger", false, "app", "url");
            }
            
            if (data.modified.length === 0 && data.missing_in_target.length === 0) {
                if (!data.failed_connections || data.failed_connections.length === 0) {
                    html += `<div style="padding:1rem; background:rgba(16, 185, 129, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--success)">
                        <strong>Perfect Match:</strong> All applications mirror each other perfectly across the cluster!
                    </div>`;
                }
            } else {
                html += `<p style="margin-bottom:1rem;">Found differences across mapped micro-services:</p>`;
            }

            // Aggregate data by Application Name
            const apps = {};
            const ensureApp = (app) => { if(!apps[app]) apps[app] = { matches: [], modified: [], missing: [] }; return apps[app]; };
            data.matches.forEach(item => ensureApp(item.app).matches.push(item));
            if (!window._diffData) window._diffData = [];
            data.modified.forEach((item, idx) => { window._diffData[idx] = item; ensureApp(item.app).modified.push({...item, originalIndex: idx}); });
            data.missing_in_target.forEach(item => ensureApp(item.app).missing.push(item));

            // Generate beautifully grouped HTML
            for (const [appName, content] of Object.entries(apps)) {
                html += `<div class="result-group" style="padding: 1.5rem; background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 1.5rem;">`;
                html += `<h3 style="margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.5rem; color: var(--primary);">📦 ${appName}</h3>`;

                if (content.modified.length > 0) {
                    html += `<h4 style="margin-top: 1rem; color: var(--warning);">Modified (Content Mismatch)</h4>
                             <ul class="result-list">`;
                    content.modified.forEach(item => {
                        html += `
                            <li style="display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <strong style="display:block;">${item.resource}</strong> 
                                    <span style="color:var(--text-secondary); font-size:0.8rem;">Key: ${item.key} | Type: ${item.type}</span>
                                </div>
                                ${item.type === 'process' 
                                    ? `<button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size:0.85rem;" onclick="app.openDiffModal(${item.originalIndex})">View Diagram diff</button>` 
                                    : `<span style="font-size:0.8rem; color:var(--text-secondary)">DMN (Check CLI for text diff)</span>`}
                            </li>`;
                    });
                    html += `</ul>`;
                }

                if (content.missing.length > 0) {
                    html += `<h4 style="margin-top: 1rem; color: var(--danger);">Missing in Target</h4>
                             <ul class="result-list">`;
                    content.missing.forEach(item => {
                        html += `<li><strong>${item.resource}</strong> <span style="color:var(--text-secondary); font-size:0.8rem;">Key: ${item.key}</span></li>`;
                    });
                    html += `</ul>`;
                }

                if (content.matches.length > 0) {
                    html += `<h4 style="margin-top: 1rem; color: var(--success);">Matches</h4>
                             <ul class="result-list">`;
                    content.matches.forEach(item => {
                        html += `<li><strong>${item.resource}</strong> <span style="color:var(--text-secondary); font-size:0.8rem;">Key: ${item.key}</span></li>`;
                    });
                    html += `</ul>`;
                }

                html += `</div>`;
            }

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
        this.setLoading("Deploying bundles to Target Micro-Services");
        try {
            const baseUrl = document.getElementById('config-target-base').value;
            const res = await fetch('/api/sync/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: this.sessionId, baseUrl: baseUrl })
            });
            const data = await res.json();
            
            let html = `<h2>Dynamic Deployment Complete</h2>`;
            
            if (data.failed && data.failed.length > 0) {
                html += `<div style="padding:1rem; background:rgba(239, 68, 68, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--danger)">
                    <strong>Warning:</strong> Some application deployments failed.
                </div>`;
                html += this.renderList("Failed Deployments", data.failed, "badge-danger", false, "app");
            } else {
                html += `<div style="padding:1rem; background:rgba(16, 185, 129, 0.2); border-radius:8px; margin-bottom:1rem; color:var(--success)">
                    <strong>Success!</strong> All application bundles were dynamically deployed successfully.
                </div>`;
            }

            if (data.success && data.success.length > 0) {
                html += this.renderList("Successful Deployments (App Name -> ID)", data.success, "badge-success", false, "app", "id");
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
    },

    renderSelectableList(title, items, badgeClass, primaryKey="resource", secondaryKey="app") {
        if (!items || items.length === 0) return '';
        return `
            <div class="result-group">
                <h3>${title} <span class="badge ${badgeClass}">${items.length}</span></h3>
                <ul class="result-list">
                    ${items.map(item => `
                        <li>
                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                <input type="checkbox" class="deploy-checkbox" data-app="${item[secondaryKey]}" data-resource="${item[primaryKey]}" checked style="width: 1.1rem; height: 1.1rem; cursor: pointer; flex-shrink: 0; margin-top: 2px;">
                                <div>
                                    <strong style="display:block;">${item[primaryKey] || "Unknown"}</strong> 
                                    ${item[secondaryKey] ? `<span style="color:var(--text-secondary); font-size:0.8rem;">App: ${item[secondaryKey]}</span>` : ''}
                                </div>
                            </div>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    },

    selectAll(state) {
        document.querySelectorAll('.deploy-checkbox').forEach(cb => cb.checked = state);
    }
};

document.addEventListener('DOMContentLoaded', () => app.init());
