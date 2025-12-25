/**
 * RTA Break Tracker - Web Application JavaScript
 */

// ==================== AGENT VIEW ====================

let selectedBreakType = null;
let selectedFile = null;

// Initialize agent view
if (document.getElementById('breakTypes')) {
    initAgentView();
}

function initAgentView() {
    // Break type selection
    document.querySelectorAll('.break-type-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            if (this.classList.contains('disabled')) return;
            
            // Clear previous selection
            document.querySelectorAll('.break-type-btn').forEach(b => b.classList.remove('selected'));
            
            // Select this one
            this.classList.add('selected');
            selectedBreakType = this.dataset.type;
            
            updateSubmitButton();
        });
    });
    
    // File input
    const fileInput = document.getElementById('fileInput');
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    // Paste button
    document.getElementById('pasteBtn').addEventListener('click', async function() {
        try {
            const items = await navigator.clipboard.read();
            for (const item of items) {
                for (const type of item.types) {
                    if (type.startsWith('image/')) {
                        const blob = await item.getType(type);
                        const file = new File([blob], 'clipboard.png', { type: type });
                        handleFileSelect(file);
                        return;
                    }
                }
            }
            showMessage('No image found in clipboard', true);
        } catch (err) {
            showMessage('Failed to paste: ' + err.message, true);
        }
    });
    
    // Keyboard paste (Ctrl+V)
    document.addEventListener('paste', function(e) {
        const items = e.clipboardData.items;
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                const blob = items[i].getAsFile();
                handleFileSelect(blob);
                e.preventDefault();
                return;
            }
        }
    });
    
    // Drag and drop
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });
    
    // Submit button
    document.getElementById('submitBtn').addEventListener('click', submitBreak);
    
    // Update elapsed time every minute
    if (window.agentData && window.agentData.hasActiveBreak) {
        updateElapsedTime();
        setInterval(updateElapsedTime, 60000);
    }
}

function handleFileSelect(file) {
    if (!file.type.startsWith('image/')) {
        showMessage('Please select an image file', true);
        return;
    }
    
    selectedFile = file;
    document.getElementById('uploadIcon').textContent = '✅';
    document.getElementById('uploadArea').classList.add('has-file');
    document.getElementById('selectedFile').textContent = '✅ ' + (file.name || 'Pasted from clipboard');
    
    updateSubmitButton();
}

function updateSubmitButton() {
    const btn = document.getElementById('submitBtn');
    if (!btn) return;
    
    const hasActiveBreak = window.agentData && window.agentData.hasActiveBreak;
    const breakInfo = window.agentData && window.agentData.breakInfo;
    const activeBreakType = window.agentData && window.agentData.activeBreakType;
    
    if (hasActiveBreak) {
        // End break mode - show break name
        btn.disabled = !selectedFile;
        if (activeBreakType && breakInfo && breakInfo[activeBreakType]) {
            const breakName = breakInfo[activeBreakType].name;
            btn.textContent = `🏁 End ${breakName}`;
        } else {
            btn.textContent = '🏁 Submit Break End';
        }
    } else {
        // Start break mode - show break name
        btn.disabled = !selectedFile || !selectedBreakType;
        
        if (selectedBreakType === 'punch_out') {
            btn.textContent = '🔴 Punch Out';
        } else if (selectedBreakType === 'punch_in') {
            btn.textContent = '🟢 Punch In';
        } else if (selectedBreakType && breakInfo && breakInfo[selectedBreakType]) {
            const breakName = breakInfo[selectedBreakType].name;
            btn.textContent = `🚀 Submit ${breakName}`;
        } else {
            btn.textContent = '🚀 Submit Break Start';
        }
    }
}

async function submitBreak() {
    const btn = document.getElementById('submitBtn');
    const hasActiveBreak = window.agentData && window.agentData.hasActiveBreak;
    
    if (!selectedFile) {
        showMessage('Please select a screenshot', true);
        return;
    }
    
    btn.disabled = true;
    btn.textContent = 'Submitting...';
    
    const formData = new FormData();
    formData.append('screenshot', selectedFile);
    
    let url, successMessage;
    
    if (hasActiveBreak) {
        url = '/api/break/end';
    } else {
        if (!selectedBreakType) {
            showMessage('Please select a break type', true);
            btn.disabled = false;
            updateSubmitButton();
            return;
        }
        url = '/api/break/start';
        formData.append('break_type', selectedBreakType);
    }
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, false);
            // Reload page after short delay
            setTimeout(() => location.reload(), 1500);
        } else {
            showMessage(data.error || 'An error occurred', true);
            updateSubmitButton();
        }
    } catch (err) {
        showMessage('Network error: ' + err.message, true);
        updateSubmitButton();
    }
}

function updateElapsedTime() {
    if (!window.agentData || !window.agentData.activeBreakStart) return;
    
    const start = new Date(window.agentData.activeBreakStart);
    const now = new Date();
    const elapsed = Math.floor((now - start) / 60000);
    
    const elapsedSpan = document.getElementById('elapsedTime');
    if (elapsedSpan) {
        elapsedSpan.textContent = elapsed;
    }
    
    // Update status box to show if overdue
    const statusBox = document.getElementById('statusBox');
    if (statusBox && window.agentData.activeBreakType && window.agentData.breakDurations) {
        const allowedDuration = window.agentData.activeBreakAllowedDuration || 
                               window.agentData.breakDurations[window.agentData.activeBreakType] || 15;
        const isOverdue = elapsed > allowedDuration;
        
        if (isOverdue) {
            statusBox.classList.add('status-overdue');
            statusBox.classList.remove('status-on-break');
        } else {
            statusBox.classList.remove('status-overdue');
            statusBox.classList.add('status-on-break');
        }
    }
}

function showMessage(text, isError) {
    const msg = document.getElementById('message');
    msg.textContent = text;
    msg.className = 'message ' + (isError ? 'error' : 'success');
    
    setTimeout(() => {
        msg.textContent = '';
        msg.className = 'message';
    }, 5000);
}


// ==================== DASHBOARD ====================

if (document.getElementById('breaksContainer')) {
    initDashboard();
}

function initDashboard() {
    // Load breaks on page load
    loadBreaks();
    
    // Date filter buttons
    document.querySelectorAll('[data-date]').forEach(btn => {
        btn.addEventListener('click', function() {
            const mode = this.dataset.date;
            setDateFilter(mode);
        });
    });
    
    // Custom date
    document.getElementById('goDateBtn').addEventListener('click', function() {
        const customDate = document.getElementById('customDate').value;
        if (customDate) {
            window.dashboardData.startDate = customDate;
            window.dashboardData.endDate = customDate;
            updateDateLabel('Custom (' + customDate + ')');
            loadBreaks();
        }
    });
    
    // Agent filter
    document.getElementById('agentFilter').addEventListener('change', loadBreaks);
    
    // Type filter
    document.getElementById('typeFilter').addEventListener('change', loadBreaks);
    
    // Search
    document.getElementById('searchInput').addEventListener('input', function() {
        filterDisplayedBreaks(this.value.toLowerCase());
    });
    
    // Auto refresh every 60 seconds (only if no error)
    setInterval(() => {
        // Only auto-refresh if not showing an error
        const container = document.getElementById('breaksContainer');
        if (!container.innerHTML.includes('error-message')) {
            loadBreaks();
        }
    }, 60000);
}

function setDateFilter(mode) {
    const today = new Date();
    let startDate, endDate, label;
    
    // Update button styles
    document.querySelectorAll('[data-date]').forEach(btn => {
        btn.classList.remove('btn-primary');
        if (btn.dataset.date === mode) {
            btn.classList.add('btn-primary');
        }
    });
    
    if (mode === 'today') {
        startDate = endDate = formatDate(today);
        label = 'Today';
    } else if (mode === 'yesterday') {
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        startDate = endDate = formatDate(yesterday);
        label = 'Yesterday';
    } else if (mode === 'week') {
        const weekAgo = new Date(today);
        weekAgo.setDate(weekAgo.getDate() - 6);
        startDate = formatDate(weekAgo);
        endDate = formatDate(today);
        label = 'Last 7 days';
    }
    
    window.dashboardData.startDate = startDate;
    window.dashboardData.endDate = endDate;
    updateDateLabel(label);
    loadBreaks();
}

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

function updateDateLabel(label) {
    document.getElementById('currentDateLabel').textContent = '📆 Showing: ' + label;
}

async function loadBreaks() {
    const container = document.getElementById('breaksContainer');
    container.innerHTML = '<div class="loading">Loading breaks...</div>';
    
    const agentId = document.getElementById('agentFilter').value;
    const breakType = document.getElementById('typeFilter').value;
    
    const params = new URLSearchParams({
        start_date: window.dashboardData.startDate,
        end_date: window.dashboardData.endDate
    });
    
    if (agentId) params.append('agent_id', agentId);
    if (breakType) params.append('break_type', breakType);
    
    try {
        const response = await fetch('/api/breaks?' + params.toString());
        
        // Handle 403 - not authorized (not logged in as RTM)
        if (response.status === 403) {
            container.innerHTML = '<div class="error-message">⚠️ Access denied. Please log in as RTM admin.</div>';
            return;
        }
        
        // Handle 401 - session expired
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.error) {
            container.innerHTML = `<div class="error-message">⚠️ ${data.error}</div>`;
            return;
        }
        
        document.getElementById('recordsCount').textContent = 
            `Showing ${data.total_breaks} breaks from ${data.agents.length} agents`;
        
        if (data.agents.length === 0) {
            container.innerHTML = '<div class="empty-message">📭 No break records found</div>';
            return;
        }
        
        container.innerHTML = '';
        
        data.agents.forEach(agent => {
            const agentCard = createAgentCard(agent);
            container.appendChild(agentCard);
        });
        
    } catch (err) {
        container.innerHTML = '<div class="error-message">Failed to load breaks: ' + err.message + '</div>';
    }
}

function createAgentCard(agent) {
    const card = document.createElement('div');
    card.className = 'agent-card';
    card.dataset.agentName = agent.agent_name.toLowerCase();
    
    card.innerHTML = `
        <div class="agent-card-header">
            <span class="agent-name">👤 ${agent.agent_name}</span>
            <span class="break-count">📋 ${agent.breaks.length} break(s)</span>
        </div>
        <div class="agent-breaks">
            ${agent.breaks.map(br => createBreakMiniCard(br)).join('')}
        </div>
    `;
    
    return card;
}

function createBreakMiniCard(br) {
    let statusClass = 'completed';
    let statusText = `✅ ${br.duration_minutes}m`;
    
    if (br.is_active) {
        statusClass = 'active';
        statusText = `⏳ ${br.elapsed_minutes}m`;
    } else if (br.is_overdue) {
        statusClass = 'overdue';
        statusText = `⚠️ ${br.duration_minutes}m`;
    }
    
    const startTime = new Date(br.start_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    const endTime = br.end_time 
        ? new Date(br.end_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
        : '...';
    
    return `
        <div class="break-mini-card ${statusClass}">
            <div class="break-mini-header">
                <span class="break-mini-type">${br.break_emoji} ${br.break_name}</span>
                <span class="break-mini-status ${statusClass}">${statusText}</span>
            </div>
            <div class="break-mini-time">🕐 ${startTime} → ${endTime}</div>
            <div class="break-screenshots">
                <div class="screenshot-box">
                    <div class="screenshot-label">Start</div>
                    ${br.start_screenshot 
                        ? `<img src="/uploads/${br.start_screenshot}" class="screenshot-thumb" onclick="showImage('/uploads/${br.start_screenshot}', 'Start Screenshot')">`
                        : '<div class="screenshot-empty">—</div>'
                    }
                </div>
                <div class="screenshot-box">
                    <div class="screenshot-label">End</div>
                    ${br.end_screenshot 
                        ? `<img src="/uploads/${br.end_screenshot}" class="screenshot-thumb" onclick="showImage('/uploads/${br.end_screenshot}', 'End Screenshot')">`
                        : '<div class="screenshot-empty">—</div>'
                    }
                </div>
            </div>
            <div class="break-notes">
                <input type="text" placeholder="Notes..." value="${br.notes}" onchange="saveNotes(${br.id}, this.value)">
                <button class="btn btn-sm btn-primary" onclick="saveNotes(${br.id}, this.previousElementSibling.value)">💾</button>
            </div>
        </div>
    `;
}

function filterDisplayedBreaks(query) {
    document.querySelectorAll('.agent-card').forEach(card => {
        const name = card.dataset.agentName;
        card.style.display = name.includes(query) ? 'block' : 'none';
    });
}

async function saveNotes(breakId, notes) {
    try {
        const response = await fetch(`/api/break/${breakId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes })
        });
        
        const data = await response.json();
        if (!data.success) {
            alert('Failed to save notes');
        }
    } catch (err) {
        alert('Error saving notes: ' + err.message);
    }
}

// ==================== MODALS ====================

function showAddAgentModal() {
    document.getElementById('addAgentModal').style.display = 'flex';
    document.getElementById('agentName').value = '';
    document.getElementById('agentUsername').value = '';
    document.getElementById('agentPassword').value = '';
    document.getElementById('agentError').textContent = '';
}

function hideAddAgentModal() {
    document.getElementById('addAgentModal').style.display = 'none';
}

async function createAgent() {
    const name = document.getElementById('agentName').value.trim();
    const username = document.getElementById('agentUsername').value.trim();
    const password = document.getElementById('agentPassword').value;
    
    if (!name || !username || !password) {
        document.getElementById('agentError').textContent = '⚠️ All fields are required';
        return;
    }
    
    try {
        const response = await fetch('/api/agent/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: name, username: username, password: password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            hideAddAgentModal();
            location.reload();
        } else {
            document.getElementById('agentError').textContent = '⚠️ ' + data.error;
        }
    } catch (err) {
        document.getElementById('agentError').textContent = '⚠️ Network error';
    }
}

// ==================== AGENT MANAGEMENT ====================

let deleteAgentId = null;

async function showAgentList() {
    const modal = document.getElementById('agentListModal');
    const container = document.getElementById('agentListContainer');
    
    modal.style.display = 'flex';
    container.innerHTML = '<div class="loading">Loading agents...</div>';
    
    try {
        const response = await fetch('/api/agents');
        const data = await response.json();
        
        if (data.error) {
            container.innerHTML = '<div class="error-message">' + data.error + '</div>';
            return;
        }
        
        if (data.agents.length === 0) {
            container.innerHTML = '<div class="empty-message">No agents found. Add your first agent!</div>';
            return;
        }
        
        container.innerHTML = data.agents.map(agent => `
            <div class="agent-list-item">
                <div class="agent-list-info">
                    <span class="agent-list-name">👤 ${agent.full_name}</span>
                    <span class="agent-list-username">@${agent.username}</span>
                </div>
                <button class="btn btn-danger btn-sm" onclick="showDeleteAgentModal(${agent.id}, '${agent.full_name}')">
                    🗑️ Delete
                </button>
            </div>
        `).join('');
        
    } catch (err) {
        container.innerHTML = '<div class="error-message">Failed to load agents: ' + err.message + '</div>';
    }
}

function hideAgentList() {
    document.getElementById('agentListModal').style.display = 'none';
}

function showDeleteAgentModal(agentId, agentName) {
    deleteAgentId = agentId;
    document.getElementById('deleteAgentMessage').textContent = 
        `Are you sure you want to delete agent "${agentName}"?`;
    document.getElementById('deleteAgentModal').style.display = 'flex';
}

function hideDeleteAgentModal() {
    document.getElementById('deleteAgentModal').style.display = 'none';
    deleteAgentId = null;
}

async function confirmDeleteAgent() {
    if (!deleteAgentId) return;
    
    const btn = document.getElementById('confirmDeleteBtn');
    btn.disabled = true;
    btn.textContent = 'Deleting...';
    
    try {
        const response = await fetch(`/api/agent/${deleteAgentId}/delete`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            hideDeleteAgentModal();
            showAgentList(); // Refresh the list
            // Show success message
            alert(`✅ ${data.message}\n\nDeleted:\n- ${data.deleted.user} user\n- ${data.deleted.shifts} shifts\n- ${data.deleted.breaks} break records`);
            // Reload page to update agent count
            location.reload();
        } else {
            alert('❌ Error: ' + data.error);
            btn.disabled = false;
            btn.textContent = '🗑️ Delete Agent';
        }
    } catch (err) {
        alert('❌ Network error: ' + err.message);
        btn.disabled = false;
        btn.textContent = '🗑️ Delete Agent';
    }
}

function showImage(src, title) {
    document.getElementById('modalImage').src = src;
    document.getElementById('imageModalTitle').textContent = title;
    document.getElementById('imageModal').style.display = 'flex';
}

function hideImageModal() {
    document.getElementById('imageModal').style.display = 'none';
}

// ==================== SHIFT MANAGEMENT ====================

function showShiftModal() {
    document.getElementById('shiftModal').style.display = 'flex';
    // Set default dates (today to 2 weeks from today)
    const today = new Date();
    const twoWeeksLater = new Date(today);
    twoWeeksLater.setDate(twoWeeksLater.getDate() + 13); // 14 days total (today + 13 more)
    
    document.getElementById('shiftStartDate').value = formatDate(today);
    document.getElementById('shiftEndDate').value = formatDate(twoWeeksLater);
    document.getElementById('shiftError').textContent = '';
    document.getElementById('shiftSuccess').style.display = 'none';
    
    // Select all agents by default
    selectAllAgents();
}

function hideShiftModal() {
    document.getElementById('shiftModal').style.display = 'none';
}

function setTwoWeeks() {
    const today = new Date();
    const twoWeeksLater = new Date(today);
    twoWeeksLater.setDate(twoWeeksLater.getDate() + 13); // 14 days total
    
    document.getElementById('shiftStartDate').value = formatDate(today);
    document.getElementById('shiftEndDate').value = formatDate(twoWeeksLater);
}

function setShiftTemplate(start, end) {
    document.getElementById('shiftStartTime').value = start;
    document.getElementById('shiftEndTime').value = end;
}

function selectAllAgents() {
    document.querySelectorAll('.agent-checkbox').forEach(cb => cb.checked = true);
}

function deselectAllAgents() {
    document.querySelectorAll('.agent-checkbox').forEach(cb => cb.checked = false);
}

async function saveBulkShifts() {
    const startDate = document.getElementById('shiftStartDate').value;
    const endDate = document.getElementById('shiftEndDate').value;
    const startTime = document.getElementById('shiftStartTime').value;
    const endTime = document.getElementById('shiftEndTime').value;
    
    if (!startDate || !endDate || !startTime || !endTime) {
        document.getElementById('shiftError').textContent = '⚠️ Please fill in all fields';
        return;
    }
    
    // Validate date range
    const start = new Date(startDate);
    const end = new Date(endDate);
    const daysDiff = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
    
    if (daysDiff > 14) {
        document.getElementById('shiftError').textContent = '⚠️ Date range cannot exceed 14 days (2 weeks)';
        return;
    }
    
    if (daysDiff < 1) {
        document.getElementById('shiftError').textContent = '⚠️ End date must be after start date';
        return;
    }
    
    const selectedAgents = [];
    document.querySelectorAll('.agent-checkbox:checked').forEach(cb => {
        selectedAgents.push(parseInt(cb.value));
    });
    
    if (selectedAgents.length === 0) {
        document.getElementById('shiftError').textContent = '⚠️ Please select at least one agent';
        return;
    }
    
    document.getElementById('shiftError').textContent = '';
    document.getElementById('shiftSuccess').style.display = 'none';
    
    try {
        const response = await fetch('/api/shift/bulk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_ids: selectedAgents,
                start_date: startDate,
                end_date: endDate,
                start_time: startTime,
                end_time: endTime
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('shiftSuccess').textContent = `✅ ${data.message}`;
            document.getElementById('shiftSuccess').style.display = 'block';
            document.getElementById('shiftError').textContent = '';
            
            // Clear form after 2 seconds
            setTimeout(() => {
                hideShiftModal();
            }, 2000);
        } else {
            document.getElementById('shiftError').textContent = '⚠️ ' + data.error;
        }
    } catch (err) {
        document.getElementById('shiftError').textContent = '⚠️ Network error: ' + err.message;
    }
}

// Close modals on escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        hideAddAgentModal();
        hideImageModal();
        hideShiftModal();
    }
});

// Close modals on background click
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.style.display = 'none';
        }
    });
});

// ==================== TAB NAVIGATION ====================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });
    
    // Show/hide tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
        content.classList.remove('active');
    });
    
    const tabContent = document.getElementById('tab-' + tabName);
    if (tabContent) {
        tabContent.style.display = 'block';
        tabContent.classList.add('active');
        
        // Load data when switching to reports tab
        if (tabName === 'reports') {
            const today = new Date();
            document.getElementById('reportStartDate').value = formatDate(today);
            document.getElementById('reportEndDate').value = formatDate(today);
        }
    }
}

// ==================== REPORTS & METRICS ====================

function setReportPeriod(period) {
    const today = new Date();
    let startDate, endDate;
    
    if (period === 'today') {
        startDate = endDate = formatDate(today);
    } else if (period === 'yesterday') {
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        startDate = endDate = formatDate(yesterday);
    } else if (period === 'week') {
        const weekAgo = new Date(today);
        weekAgo.setDate(weekAgo.getDate() - 6);
        startDate = formatDate(weekAgo);
        endDate = formatDate(today);
    } else if (period === 'month') {
        const monthAgo = new Date(today);
        monthAgo.setDate(monthAgo.getDate() - 29);
        startDate = formatDate(monthAgo);
        endDate = formatDate(today);
    }
    
    document.getElementById('reportStartDate').value = startDate;
    document.getElementById('reportEndDate').value = endDate;
    
    loadMetrics();
}

async function loadMetrics() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;
    
    if (!startDate || !endDate) {
        alert('Please select a date range');
        return;
    }
    
    const tbody = document.getElementById('metricsTableBody');
    tbody.innerHTML = '<tr><td colspan="13" class="loading">Loading metrics...</td></tr>';
    
    try {
        const response = await fetch(`/api/report/metrics?start_date=${startDate}&end_date=${endDate}`);
        const data = await response.json();
        
        if (data.error) {
            tbody.innerHTML = `<tr><td colspan="13" class="error-message">${data.error}</td></tr>`;
            return;
        }
        
        // Update summary cards
        document.getElementById('avgUtilization').textContent = data.totals.avg_utilization + '%';
        document.getElementById('avgAdherence').textContent = data.totals.avg_adherence + '%';
        document.getElementById('avgConformance').textContent = data.totals.avg_conformance + '%';
        document.getElementById('totalIncidents').textContent = data.totals.incidents;
        document.getElementById('totalExceeding').textContent = data.totals.exceeding_break_minutes + ' min';
        document.getElementById('totalEmergency').textContent = data.totals.emergency_count;
        document.getElementById('summaryCards').style.display = 'grid';
        
        // Populate table
        if (data.agents.length === 0) {
            tbody.innerHTML = '<tr><td colspan="13" class="empty-message">No agents found</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        data.agents.forEach(agent => {
            let statusClass, statusText;
            
            if (agent.incidents === 0 && agent.exceeding_break_minutes === 0) {
                statusClass = 'status-good';
                statusText = '✅ Good';
            } else if (agent.incidents <= 2 || agent.exceeding_break_minutes <= 15) {
                statusClass = 'status-warning';
                statusText = '⚠️ Warning';
            } else {
                statusClass = 'status-bad';
                statusText = '❌ Review';
            }
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${agent.agent_name}</td>
                <td>${agent.total_scheduled_hours}h</td>
                <td>${agent.total_breaks}</td>
                <td>${agent.total_break_minutes} min</td>
                <td>${agent.exceeding_break_minutes} min</td>
                <td>${agent.incidents}</td>
                <td>${agent.emergency_count}</td>
                <td>${agent.lunch_count || 0}</td>
                <td>${agent.coaching_count || 0}</td>
                <td>${agent.utilization}%</td>
                <td>${agent.adherence}%</td>
                <td>${agent.conformance}%</td>
                <td class="${statusClass}">${statusText}</td>
            `;
            tbody.appendChild(row);
        });
        
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="13" class="error-message">Error: ${err.message}</td></tr>`;
    }
}

function exportToExcel() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;
    
    if (!startDate || !endDate) {
        alert('Please select a date range first');
        return;
    }
    
    // Trigger download
    window.location.href = `/api/report/export?start_date=${startDate}&end_date=${endDate}`;
}

