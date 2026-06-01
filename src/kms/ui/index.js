const KMS_API_BASE = '/api/v1';

// Utility to generate unique suffix matching backend structure
function uuid_suffix() {
    return Math.random().toString(36).substring(2, 8);
}

function setButtonBusy(button, busyText) {
    const originalHtml = button.innerHTML;
    button.dataset.originalHtml = originalHtml;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.classList.add('is-busy');
    button.innerHTML = busyText;
    return originalHtml;
}

function restoreButton(button, originalHtml) {
    button.disabled = false;
    button.removeAttribute('aria-busy');
    button.classList.remove('is-busy');
    button.innerHTML = originalHtml || button.dataset.originalHtml || button.innerHTML;
    delete button.dataset.originalHtml;
}

function initButtonFeedback() {
    if (document.body.dataset.buttonFeedbackBound) return;
    document.body.dataset.buttonFeedbackBound = 'true';
    document.addEventListener('click', (event) => {
        const target = event.target.closest('button, .btn, .tab-btn');
        if (!target || target.disabled || target.getAttribute('aria-disabled') === 'true') return;
        target.classList.remove('is-clicked');
        void target.offsetWidth;
        target.classList.add('is-clicked');
        window.setTimeout(() => target.classList.remove('is-clicked'), 220);
    }, true);
}

// Ensure all script logic runs safely once the DOM is fully constructed
document.addEventListener('DOMContentLoaded', () => {
    initButtonFeedback();
    // ==========================================================
    // 🧭 PORTAL TAB & CONTROLS INTERACTIVE TOGGLES
    // ==========================================================
    const tabQueryBtn = document.getElementById('tab-query-btn');
    const tabAddBtn = document.getElementById('tab-add-btn');
    const sectionQuery = document.getElementById('section-query');
    const sectionAdd = document.getElementById('section-add');

    if (tabQueryBtn && tabAddBtn && sectionQuery && sectionAdd) {
        tabQueryBtn.addEventListener('click', () => {
            tabQueryBtn.classList.add('active');
            tabAddBtn.classList.remove('active');
            sectionQuery.classList.add('active');
            sectionAdd.classList.remove('active');
        });

        tabAddBtn.addEventListener('click', () => {
            tabAddBtn.classList.add('active');
            tabQueryBtn.classList.remove('active');
            sectionAdd.classList.add('active');
            sectionQuery.classList.remove('active');
            loadPendingCandidates();
        });
    }

    const inputModeSelect = document.getElementById('kms-input-mode');
    const wrapperFile = document.getElementById('wrapper-mode-file');
    const wrapperText = document.getElementById('wrapper-mode-text');

    if (inputModeSelect && wrapperFile && wrapperText) {
        inputModeSelect.addEventListener('change', () => {
            if (inputModeSelect.value === 'file') {
                wrapperFile.classList.remove('hide');
                wrapperText.classList.add('hide');
            } else {
                wrapperFile.classList.add('hide');
                wrapperText.classList.remove('hide');
            }
        });
    }

    // ==========================================================
    // ⚖️ GLOBAL CANDIDATE REVIEWS AND ACTIVE APPROVALS
    // ==========================================================
    window.actionCandidate = async function(candidateId, status) {
        const listEl = document.getElementById('candidates-list');
        if (listEl) {
            listEl.innerHTML = `<div class="loader">⚡ Processing review: ${status} in progress...</div>`;
        }
        try {
            const res = await fetch(`${KMS_API_BASE}/kms/candidates/action`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    candidateId: candidateId,
                    status: status,
                    comments: `Reviewed and actioned via KMS Governance UI.`
                })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                await loadPendingCandidates();
            } else {
                alert(`Action failed: ${data.detail || 'Server error occurred'}`);
                await loadPendingCandidates();
            }
        } catch (err) {
            alert(`Error processing candidate review action: ${err.message}`);
            await loadPendingCandidates();
        }
    };

    // Loads and renders pending candidates awaiting approval
    async function loadPendingCandidates() {
        const listEl = document.getElementById('candidates-list');
        if (!listEl) return;
        
        try {
            const res = await fetch(`${KMS_API_BASE}/kms/candidates`);
            if (!res.ok) {
                listEl.innerHTML = '<p class="error">Failed to retrieve candidate reviews queue.</p>';
                return;
            }
            const data = await res.json();
            // Filter strictly for candidate records that require SME governance
            const pending = data.filter(c => c.review_status === 'Pending Review');
            
            if (pending.length === 0) {
                listEl.innerHTML = `
                    <p class="loader" style="color: var(--text-secondary); text-align: center; padding: 12px; border: 1px dashed var(--border-color); border-radius: 8px;">
                        🎉 Staging queue is empty! No document ingestions pending SME review.
                    </p>
                `;
                return;
            }
            
            listEl.innerHTML = '';
            pending.forEach(cand => {
                const item = document.createElement('div');
                item.className = 'alert-card';
                item.style.display = 'flex';
                item.style.flexDirection = 'column';
                item.style.gap = '8px';
                item.style.background = '#f8fafc';
                item.style.border = '1px solid var(--border-color)';
                item.style.borderRadius = '8px';
                item.style.padding = '16px';
                item.style.boxShadow = 'var(--shadow)';
                item.style.marginBottom = '8px';
                
                item.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="font-size:14px; color:var(--text-primary);">${cand.title || 'Extracted Document Candidate'}</strong>
                        <span class="badge-fill">${cand.domain}</span>
                    </div>
                    <p style="font-size:12px; color:var(--text-secondary); margin:4px 0;">${cand.summary || 'No summary extracted.'}</p>
                    <div class="details" style="font-size:11px; color:var(--text-secondary);">
                        <strong>Staging ID:</strong> <code>${cand.candidate_id}</code> | 
                        <strong>Source Document:</strong> <code>${cand.source_document || 'N/A'}</code> | 
                        <strong>SME Owner:</strong> <code>${cand.suggested_sme || 'Unassigned'}</code>
                    </div>
                    <div style="display:flex; gap:8px; margin-top:10px;">
                        <button class="btn" style="background:#10b981; font-size:11px; padding:6px 12px; font-weight:600;" onclick="window.actionCandidate('${cand.candidate_id}', 'Approved')">Approve & Ingest</button>
                        <button class="btn" style="background:#ef4444; font-size:11px; padding:6px 12px; font-weight:600;" onclick="window.actionCandidate('${cand.candidate_id}', 'Rejected')">Reject</button>
                    </div>
                `;
                listEl.appendChild(item);
            });
        } catch (err) {
            listEl.innerHTML = `<p class="error">Error loading queue: ${err.message}</p>`;
        }
    }

    // ==========================================================
    // 🔍 QUERY KNOWLEDGE SYSTEM (FAISS & SQLite)
    // ==========================================================
    const kmsBtn = document.getElementById('kms-btn');
    if (kmsBtn) {
        kmsBtn.addEventListener('click', async () => {
            const qEl = document.getElementById('kms-q');
            const resBox = document.getElementById('kms-results');
            if (!qEl || !resBox) return;

            const q = qEl.value.trim();
            if (!q) return;
            
            const originalText = setButtonBusy(kmsBtn, '⏳ Querying KMS...');
            
            resBox.innerHTML = '<div class="loader">🔍 Grounding search in central KMS (FAISS & SQLite)...</div>';
            resBox.classList.remove('hide');
            
            try {
                const res = await fetch(`${KMS_API_BASE}/kms/query`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ query: q })
                });
                if (!res.ok) {
                    resBox.innerHTML = `<p class="error">Query failed: ${res.statusText}</p>`;
                    return;
                }
                const data = await res.json();
                resBox.innerHTML = '';
                
                if ((!data.matchedChunks || data.matchedChunks.length === 0) && (!data.matchedNodes || data.matchedNodes.length === 0)) {
                    resBox.innerHTML = '<p class="warn">No matching vector chunks or knowledge graph entities found in database.</p>';
                    return;
                }
                
                // 1. Render Matched Dense Vector Chunks
                if (data.matchedChunks && data.matchedChunks.length > 0) {
                    const chunkSection = document.createElement('div');
                    chunkSection.style.marginBottom = '24px';
                    chunkSection.innerHTML = `<h3 style="font-size:14px; font-weight:700; margin-bottom:10px; border-bottom:1px solid var(--border-color); padding-bottom:6px; color:var(--accent-color);">📚 Matched Vector Chunks (SQLite & FAISS)</h3>`;
                    data.matchedChunks.forEach(chunk => {
                        const item = document.createElement('div');
                        item.style.background = '#f8fafc';
                        item.style.border = '1px solid var(--border-color)';
                        item.style.borderRadius = '6px';
                        item.style.padding = '12px';
                        item.style.marginBottom = '8px';
                        item.style.boxShadow = 'var(--shadow)';
                        item.innerHTML = `
                            <p style="font-size:13px; color:var(--text-primary); line-height:1.5; margin:0;">${chunk.text}</p>
                            <div class="details" style="font-size:11px; color:var(--text-secondary); margin-top:6px; display:flex; gap:12px;">
                                <span><strong>Source ID:</strong> <code>${chunk.node_id}</code></span>
                                <span><strong>Relevance:</strong> <span class="badge-fill" style="background:#10b9811a; color:#10b981;">${chunk.score ? Math.round(chunk.score * 100) + '%' : '100%'}</span></span>
                            </div>
                        `;
                        chunkSection.appendChild(item);
                    });
                    resBox.appendChild(chunkSection);
                }

                // 2. Render Matched Graph Lineage & Relationships
                if (data.matchedNodes && data.matchedNodes.length > 0) {
                    const graphSection = document.createElement('div');
                    graphSection.innerHTML = `<h3 style="font-size:14px; font-weight:700; margin-bottom:10px; border-bottom:1px solid var(--border-color); padding-bottom:6px; color:#6366f1;">🌐 Matched Graph Lineage & Entities (GRAPHDB)</h3>`;
                    data.matchedNodes.forEach(node => {
                        const item = document.createElement('div');
                        item.className = 'graph-match-box';
                        item.style.boxShadow = 'var(--shadow)';
                        item.style.marginBottom = '8px';
                        item.innerHTML = `
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                <strong style="font-size:13px; color:var(--text-primary);">${node.title || 'Graph Node'}</strong>
                                <span class="badge-fill" style="background:#6366f11a; color:#6366f1;">${node.type || 'Entity'}</span>
                            </div>
                            <p style="font-size:12px; color:var(--text-secondary); margin:4px 0 0 0; line-height:1.4;">${node.content}</p>
                            <div class="details" style="font-size:11px; margin-top:4px; color:var(--text-secondary);">
                                <strong>Node ID:</strong> <code>${node.node_id}</code>
                            </div>
                        `;
                        graphSection.appendChild(item);
                    });
                    resBox.appendChild(graphSection);
                }
            } catch(err) {
                resBox.innerHTML = `<p class="error">Query failed: ${err.message}</p>`;
            } finally {
                restoreButton(kmsBtn, originalText);
            }
        });
    }

    // ==========================================================
    // 📥 CORPORATE KNOWLEDGE INGESTION PIPELINE (FILE & TEXT)
    // ==========================================================
    const kmsUploadBtn = document.getElementById('kms-upload-btn');
    if (kmsUploadBtn) {
        kmsUploadBtn.addEventListener('click', async () => {
            const inputMode = inputModeSelect ? inputModeSelect.value : 'file';
            const domainEl = document.getElementById('kms-domain');
            const securityEl = document.getElementById('kms-security');
            const smeEl = document.getElementById('kms-sme');
            const autoApproveEl = document.getElementById('kms-auto-approve');
            const resBox = document.getElementById('kms-upload-results');

            if (!domainEl || !securityEl || !smeEl || !autoApproveEl || !resBox) return;

            const domain = domainEl.value;
            const security = securityEl.value;
            const sme = smeEl.value.trim();
            const autoApprove = autoApproveEl.value === 'true';
            
            resBox.classList.remove('hide');
            
            const originalText = setButtonBusy(kmsUploadBtn, '⏳ Ingesting corporate knowledge...');

            try {
                if (inputMode === 'file') {
                    // Method A: File Upload
                    const fileInput = document.getElementById('kms-file');
                    if (!fileInput || !fileInput.files.length) {
                        resBox.innerHTML = '<p class="error">Please select a document file to upload first.</p>';
                        restoreButton(kmsUploadBtn, originalText);
                        return;
                    }
                    
                    const file = fileInput.files[0];
                    resBox.innerHTML = `<div class="loader">⚙️ Reading file: ${file.name}...</div>`;
                    
                    const reader = new FileReader();
                    reader.onload = async (e) => {
                        try {
                            await transmitIngestion(file.name, e.target.result, 'Direct Uploader');
                        } finally {
                            restoreButton(kmsUploadBtn, originalText);
                        }
                    };
                    reader.onerror = () => {
                        resBox.innerHTML = '<p class="error">Failed to read the local file asset.</p>';
                        restoreButton(kmsUploadBtn, originalText);
                    };
                    reader.readAsText(file);
                } else {
                    // Method B: Copy-Paste Text
                    const textTitleEl = document.getElementById('kms-text-title');
                    const textBodyEl = document.getElementById('kms-text-body');

                    if (!textTitleEl || !textBodyEl) {
                        restoreButton(kmsUploadBtn, originalText);
                        return;
                    }

                    const textTitle = textTitleEl.value.trim();
                    const textBody = textBodyEl.value.trim();
                    
                    if (!textTitle || !textBody) {
                        resBox.innerHTML = '<p class="error">Please provide both a document title and the text content body.</p>';
                        restoreButton(kmsUploadBtn, originalText);
                        return;
                    }
                    
                    resBox.innerHTML = `<div class="loader">⚡ Staging copy-pasted text details...</div>`;
                    const virtualFilename = `pasted_${textTitle.toLowerCase().replace(/[^a-z0-9]/g, '_')}_${uuid_suffix()}.txt`;
                    try {
                        await transmitIngestion(virtualFilename, textBody, 'Text Ingestion Paste');
                    } finally {
                        restoreButton(kmsUploadBtn, originalText);
                    }
                }
            } catch (err) {
                resBox.innerHTML = `<p class="error">Ingestion error: ${err.message}</p>`;
                restoreButton(kmsUploadBtn, originalText);
            }

            // Internal helper to POST payload to API
            async function transmitIngestion(filename, content, applicationName) {
                try {
                    const payload = {
                        filename: filename,
                        content: content,
                        owner: 'UI Uploader',
                        securityClassification: security,
                        sme: sme || 'Marcus Vance',
                        businessDomain: domain,
                        prompt: '',
                        autoApprove: autoApprove
                    };
                    
                    const res = await fetch(`${KMS_API_BASE}/kms/upload`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });
                    
                    const data = await res.json();
                    if (res.ok && data.success) {
                        if (autoApprove) {
                            resBox.innerHTML = `
                                <p class="success-msg">🎉 Ingestion Completed & Indexed Automatically!</p>
                                <div class="details" style="margin-top: 8px;">
                                    <strong>Candidate ID:</strong> <code>${data.candidateId}</code><br/>
                                    <strong>Status:</strong> <span class="badge-fill" style="background:#10b9812a; color:#10b981;">${data.status}</span><br/>
                                    <strong>Action Details:</strong> Instantly embedded in FAISS and saved to ` + "`vector_chunks`" + ` in aipdb.
                                </div>
                            `;
                        } else {
                            resBox.innerHTML = `
                                <p class="success-msg" style="color: #6366f1;">⏳ Document Uploaded & Staged for SME Review!</p>
                                <div class="details" style="margin-top: 8px;">
                                    <strong>Candidate ID:</strong> <code>${data.candidateId}</code><br/>
                                    <strong>Status:</strong> <span class="badge-fill" style="background:#6366f12a; color:#6366f1;">${data.status}</span><br/>
                                    <strong>Action Details:</strong> Chunks are NOT indexed yet. Go to 'Pending Candidate Ingestions' below to approve.
                                </div>
                            `;
                        }
                        
                        // Reset inputs
                        const fileEl = document.getElementById('kms-file');
                        if (fileEl) fileEl.value = '';
                        const textTitleEl = document.getElementById('kms-text-title');
                        if (textTitleEl) textTitleEl.value = '';
                        const textBodyEl = document.getElementById('kms-text-body');
                        if (textBodyEl) textBodyEl.value = '';
                        
                        // Refresh list
                        await loadPendingCandidates();
                    } else {
                        resBox.innerHTML = `<p class="error">Upload failed: ${data.detail || 'Unknown server error'}</p>`;
                    }
                } catch (err) {
                    resBox.innerHTML = `<p class="error">Ingestion error: ${err.message}</p>`;
                }
            }
        });
    }

    // Initial load of candidates queue on boot
    loadPendingCandidates();
});
