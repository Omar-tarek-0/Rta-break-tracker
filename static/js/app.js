/**
 * RTA Break Tracker - Web Application JavaScript
 */

// ==================== AGENT VIEW ====================

let selectedBreakType = null;
let selectedFile = null;

// Initialize agent view
if (document.getElementById('breakTypes') || document.querySelector('.punch-section')) {
    initAgentView();
}

function initAgentView() {
    // Check if we're in punch-in mode (pre-select punch_in)
    const punchBtn = document.querySelector('.punch-section .punch-btn');
    if (punchBtn && window.agentData && window.agentData.punchStatus === 'not_punched_in') {
        selectedBreakType = 'punch_in';
    }
    
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
    const punchStatus = window.agentData && window.agentData.punchStatus;
    
    if (punchStatus === 'not_punched_in') {
        // Punch in mode
        btn.disabled = !selectedFile;
        btn.textContent = '🟢 Punch In';
    } else if (hasActiveBreak) {
        // End break mode
        btn.disabled = !selectedFile;
        btn.textContent = '🏁 Submit Break End';
    } else {
        // Start break mode
        btn.disabled = !selectedFile || !selectedBreakType;
        
        // Show appropriate button text
        if (selectedBreakType === 'punch_out') {
            btn.textContent = '🔴 Punch Out';
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

function showImage(src, title) {
    document.getElementById('modalImage').src = src;
    document.getElementById('imageModalTitle').textContent = title;
    document.getElementById('imageModal').style.display = 'flex';
}

function hideImageModal() {
    document.getElementById('imageModal').style.display = 'none';
}

// Close modals on escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        hideAddAgentModal();
        hideImageModal();
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

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const tabId = this.dataset.tab;
        
        // Update button states
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        
        // Show/hide tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.style.display = 'none';
            content.classList.remove('active');
        });
        
        const tabContent = document.getElementById('tab-' + tabId);
        if (tabContent) {
            tabContent.style.display = 'flex';
            tabContent.classList.add('active');
            
            // Load data for the tab
            if (tabId === 'shifts') {
                loadShifts();
            }
        }
    });
});


// ==================== SHIFT MANAGEMENT ====================

let shiftsData = {};

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

async function loadShifts() {
    const shiftDate = document.getElementById('shiftDate').value;
    if (!shiftDate) return;
    
    try {
        const response = await fetch(`/api/shifts?start_date=${shiftDate}&end_date=${shiftDate}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading shifts:', data.error);
            return;
        }
        
        // Store shifts data
        shiftsData = {};
        data.shifts.forEach(shift => {
            shiftsData[shift.agent_id] = shift;
        });
        
        // Update table display
        updateShiftsTable();
        
    } catch (err) {
        console.error('Failed to load shifts:', err);
    }
}

function updateShiftsTable() {
    document.querySelectorAll('#shiftsTableBody tr').forEach(row => {
        const agentId = parseInt(row.dataset.agentId);
        const shiftDisplay = row.querySelector('.shift-display');
        const hoursDisplay = row.querySelector('.hours-display');
        
        if (shiftsData[agentId]) {
            const shift = shiftsData[agentId];
            shiftDisplay.innerHTML = `<span class="has-shift">🕐 ${shift.start_time} - ${shift.end_time}</span>`;
            hoursDisplay.textContent = shift.duration_hours + 'h';
        } else {
            shiftDisplay.innerHTML = '<span class="no-shift">No shift set</span>';
            hoursDisplay.textContent = '-';
        }
    });
}

async function saveSelectedShifts() {
    const selectedAgents = [];
    document.querySelectorAll('.agent-checkbox:checked').forEach(cb => {
        selectedAgents.push(parseInt(cb.value));
    });
    
    if (selectedAgents.length === 0) {
        alert('Please select at least one agent');
        return;
    }
    
    const shiftDate = document.getElementById('shiftDate').value;
    const startTime = document.getElementById('shiftStartTime').value;
    const endTime = document.getElementById('shiftEndTime').value;
    
    if (!shiftDate || !startTime || !endTime) {
        alert('Please fill in all shift details');
        return;
    }
    
    try {
        const response = await fetch('/api/shift/bulk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_ids: selectedAgents,
                shift_date: shiftDate,
                start_time: startTime,
                end_time: endTime
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(data.message);
            deselectAllAgents();
            loadShifts();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Network error: ' + err.message);
    }
}

async function deleteShift(agentId) {
    const shift = shiftsData[agentId];
    if (!shift) {
        alert('No shift to delete for this agent on selected date');
        return;
    }
    
    if (!confirm('Delete this shift?')) return;
    
    try {
        const response = await fetch(`/api/shift/${shift.id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadShifts();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Network error: ' + err.message);
    }
}

// Load shifts when date changes
if (document.getElementById('shiftDate')) {
    document.getElementById('shiftDate').addEventListener('change', loadShifts);
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
    tbody.innerHTML = '<tr><td colspan="9" class="loading">Loading metrics...</td></tr>';
    
    try {
        const response = await fetch(`/api/report/metrics?start_date=${startDate}&end_date=${endDate}`);
        const data = await response.json();
        
        if (data.error) {
            tbody.innerHTML = `<tr><td colspan="9" class="error-message">${data.error}</td></tr>`;
            return;
        }
        
        // Update summary cards
        document.getElementById('avgUtilization').textContent = data.totals.avg_utilization + '%';
        document.getElementById('avgAdherence').textContent = data.totals.avg_adherence + '%';
        document.getElementById('avgConformance').textContent = data.totals.avg_conformance + '%';
        document.getElementById('totalIncidents').textContent = data.totals.incidents;
        document.getElementById('totalExceeding').textContent = data.totals.exceeding_break_minutes + ' min';
        document.getElementById('totalEmergency').textContent = data.totals.emergency_count;
        
        // Update period label
        document.getElementById('reportPeriodLabel').textContent = `${startDate} to ${endDate}`;
        
        // Populate table
        if (data.agents.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="empty-message">No agents found</td></tr>';
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
                <td>${agent.utilization}%</td>
                <td>${agent.adherence}%</td>
                <td class="${statusClass}">${statusText}</td>
            `;
            tbody.appendChild(row);
        });
        
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="9" class="error-message">Error: ${err.message}</td></tr>`;
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

