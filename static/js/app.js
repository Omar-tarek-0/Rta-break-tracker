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
    
    // Show attendance records separately if they exist
    let attendanceSection = '';
    if (agent.attendance && agent.attendance.length > 0) {
        attendanceSection = `
            <div class="attendance-section" style="padding: 15px; border-bottom: 1px solid var(--border);">
                <h4 style="font-size: 13px; margin-bottom: 10px; color: var(--text-secondary);">📅 Attendance Records:</h4>
                ${agent.attendance.map(att => createAttendanceCard(att)).join('')}
            </div>
        `;
    }
    
    // Group breaks by shift_date (shift period)
    const breaksByShift = {};
    agent.breaks.forEach(br => {
        const shiftDate = br.shift_date || (br.start_time ? new Date(br.start_time).toISOString().split('T')[0] : 'unknown');
        if (!breaksByShift[shiftDate]) {
            breaksByShift[shiftDate] = [];
        }
        breaksByShift[shiftDate].push(br);
    });
    
    // Create break sections grouped by shift period
    let breaksSection = '';
    const shiftDates = Object.keys(breaksByShift).sort().reverse(); // Most recent first
    
    shiftDates.forEach(shiftDate => {
        const shiftBreaks = breaksByShift[shiftDate];
        const shiftDateFormatted = new Date(shiftDate + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        breaksSection += `
            <div class="shift-breaks-group" style="margin-bottom: 15px;">
                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 8px; padding: 5px; background: var(--surface-light); border-radius: 4px;">
                    📅 Shift Period: ${shiftDateFormatted} (${shiftBreaks.length} break${shiftBreaks.length !== 1 ? 's' : ''})
                </div>
                ${shiftBreaks.map(br => createBreakMiniCard(br)).join('')}
            </div>
        `;
    });
    
    card.innerHTML = `
        <div class="agent-card-header">
            <span class="agent-name">👤 ${agent.agent_name}</span>
            <span class="break-count">📋 ${agent.breaks.length} break(s)</span>
        </div>
        ${attendanceSection}
        <div class="agent-breaks">
            ${breaksSection}
        </div>
    `;
    
    return card;
}

function createAttendanceCard(att) {
    // If it's a paired punch in/out, show both together
    if (att.type === 'punch_pair') {
        const punchInTime = att.punch_in.time 
            ? new Date(att.punch_in.time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
            : 'N/A';
        const punchInDate = att.punch_in.date 
            ? new Date(att.punch_in.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            : '';
        
        let punchOutSection = '';
        if (att.punch_out) {
            const punchOutTime = att.punch_out.time 
                ? new Date(att.punch_out.time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
                : 'N/A';
            const punchOutDate = att.punch_out.date 
                ? new Date(att.punch_out.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                : '';
            
            punchOutSection = `
                <div style="display: flex; align-items: center; gap: 8px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border);">
                    <span style="font-size: 16px;">🔴</span>
                    <span style="font-weight: 600; flex: 1;">Punch Out</span>
                    <span style="font-size: 11px; color: var(--text-secondary);">${punchOutDate}</span>
                    <span style="font-size: 12px; color: var(--text-secondary);">🕐 ${punchOutTime}</span>
                    ${att.punch_out.screenshot 
                        ? `<img src="/uploads/${att.punch_out.screenshot}" class="screenshot-thumb" onclick="showImage('/uploads/${att.punch_out.screenshot}', 'Punch Out Screenshot')" style="width: 40px; height: 30px; object-fit: cover; border-radius: 4px; cursor: pointer;" onerror="this.onerror=null; this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iMzAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjMwIiBmaWxsPSIjZWVlIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSI4IiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+Tm90IGZvdW5kPC90ZXh0Pjwvc3Zn+'; this.style.cursor='default'; this.onclick=null;">`
                        : '<div style="width: 40px; height: 30px; background: var(--border); border-radius: 4px;"></div>'
                    }
                </div>
            `;
        }
        
        return `
            <div class="attendance-card" style="margin-bottom: 12px; padding: 12px; background: var(--surface-light); border-radius: 8px; border: 1px solid var(--border);">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 16px;">🟢</span>
                    <span style="font-weight: 600; flex: 1;">Punch In</span>
                    <span style="font-size: 11px; color: var(--text-secondary);">${punchInDate}</span>
                    <span style="font-size: 12px; color: var(--text-secondary);">🕐 ${punchInTime}</span>
                    ${att.punch_in.screenshot 
                        ? `<img src="/uploads/${att.punch_in.screenshot}" class="screenshot-thumb" onclick="showImage('/uploads/${att.punch_in.screenshot}', 'Punch In Screenshot')" style="width: 40px; height: 30px; object-fit: cover; border-radius: 4px; cursor: pointer;" onerror="this.onerror=null; this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iMzAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjMwIiBmaWxsPSIjZWVlIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSI4IiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+Tm90IGZvdW5kPC90ZXh0Pjwvc3Zn+'; this.style.cursor='default'; this.onclick=null;">`
                        : '<div style="width: 40px; height: 30px; background: var(--border); border-radius: 4px;"></div>'
                    }
                </div>
                ${punchOutSection}
            </div>
        `;
    }
    
    // Single attendance record (standalone punch out)
    const time = new Date(att.time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
    return `
        <div class="attendance-card" style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; padding: 8px; background: var(--surface-light); border-radius: 6px;">
            <span style="font-size: 16px;">${att.emoji}</span>
            <span style="font-weight: 600; flex: 1;">${att.name}</span>
            <span style="font-size: 12px; color: var(--text-secondary);">🕐 ${time}</span>
            ${att.screenshot 
                ? `<img src="/uploads/${att.screenshot}" class="screenshot-thumb" onclick="showImage('/uploads/${att.screenshot}', '${att.name} Screenshot')" style="width: 40px; height: 30px; object-fit: cover; border-radius: 4px; cursor: pointer;" onerror="this.onerror=null; this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iMzAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjMwIiBmaWxsPSIjZWVlIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSI4IiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+Tm90IGZvdW5kPC90ZXh0Pjwvc3Zn+'; this.style.cursor='default'; this.onclick=null;">`
                : '<div style="width: 40px; height: 30px; background: var(--border); border-radius: 4px;"></div>'
            }
        </div>
    `;
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
                        ? `<img src="/uploads/${br.start_screenshot}" class="screenshot-thumb" onclick="showImage('/uploads/${br.start_screenshot}', 'Start Screenshot')" onerror="this.onerror=null; this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5Ob3QgZm91bmQ8L3RleHQ+PC9zdmc+'; this.style.cursor='default'; this.onclick=null;">`
                        : '<div class="screenshot-empty">—</div>'
                    }
                </div>
                <div class="screenshot-box">
                    <div class="screenshot-label">End</div>
                    ${br.end_screenshot 
                        ? `<img src="/uploads/${br.end_screenshot}" class="screenshot-thumb" onclick="showImage('/uploads/${br.end_screenshot}', 'End Screenshot')" onerror="this.onerror=null; this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5Ob3QgZm91bmQ8L3RleHQ+PC9zdmc+'; this.style.cursor='default'; this.onclick=null;">`
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
    const img = document.getElementById('modalImage');
    img.src = src;
    img.onerror = function() {
        console.error('Failed to load image:', src);
        img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5JbWFnZSBub3QgZm91bmQ8L3RleHQ+PC9zdmc+';
        img.alt = 'Image not found';
    };
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
    tbody.innerHTML = '<tr><td colspan="15" class="loading">Loading metrics...</td></tr>';
    
    try {
        const response = await fetch(`/api/report/metrics?start_date=${startDate}&end_date=${endDate}`);
        const data = await response.json();
        
        if (data.error) {
            tbody.innerHTML = `<tr><td colspan="15" class="error-message">${data.error}</td></tr>`;
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
            tbody.innerHTML = '<tr><td colspan="15" class="empty-message">No agents found</td></tr>';
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
                <td>${agent.overtime_count || 0}</td>
                <td>${agent.overtime_minutes || 0} min</td>
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

// ==================== ATTENDANCE MANAGEMENT ====================

function setAttendancePeriod(period) {
    const today = new Date();
    let startDate, endDate;
    
    if (period === 'today') {
        startDate = endDate = formatDate(today);
    } else if (period === 'week') {
        startDate = formatDate(today);
        const weekLater = new Date(today);
        weekLater.setDate(today.getDate() + 6);
        endDate = formatDate(weekLater);
    } else if (period === 'month') {
        startDate = formatDate(today);
        const monthLater = new Date(today);
        monthLater.setDate(today.getDate() + 29);
        endDate = formatDate(monthLater);
    }
    
    document.getElementById('attendanceStartDate').value = startDate;
    document.getElementById('attendanceEndDate').value = endDate;
}

async function loadAttendance() {
    const startDate = document.getElementById('attendanceStartDate').value;
    const endDate = document.getElementById('attendanceEndDate').value;
    const agentId = document.getElementById('attendanceAgentFilter').value;
    
    if (!startDate || !endDate) {
        alert('Please select a date range');
        return;
    }
    
    const tbody = document.getElementById('attendanceTableBody');
    const summaryCards = document.getElementById('attendanceSummaryCards');
    
    tbody.innerHTML = '<tr><td colspan="9" class="loading">Loading attendance...</td></tr>';
    
    try {
        let url = `/api/attendance?start_date=${startDate}&end_date=${endDate}`;
        if (agentId) {
            url += `&agent_id=${agentId}`;
        }
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Failed to load attendance');
        }
        
        const data = await response.json();
        
        if (!data.attendance || data.attendance.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="empty-message">No attendance records found for the selected period</td></tr>';
            summaryCards.style.display = 'none';
            return;
        }
        
        // Update summary cards
        const summary = data.summary;
        document.getElementById('attendanceTotalDays').textContent = summary.total_days || 0;
        document.getElementById('attendancePresentDays').textContent = summary.present_days || 0;
        document.getElementById('attendanceAbsentDays').textContent = summary.absent_days || 0;
        document.getElementById('attendanceLateDays').textContent = summary.late_days || 0;
        document.getElementById('attendancePercentage').textContent = (summary.attendance_percentage || 0) + '%';
        document.getElementById('attendanceAvgHours').textContent = (summary.avg_hours_worked || 0) + 'h';
        summaryCards.style.display = 'flex';
        
        // Populate table
        tbody.innerHTML = '';
        
        data.attendance.forEach(record => {
            // Format times
            let punchInTime = '-';
            if (record.punch_in && record.punch_in.time) {
                const dt = new Date(record.punch_in.time);
                punchInTime = dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
            }
            
            let punchOutTime = '-';
            if (record.punch_out && record.punch_out.time) {
                const dt = new Date(record.punch_out.time);
                punchOutTime = dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
            }
            
            let shiftTime = '-';
            if (record.shift) {
                shiftTime = `${record.shift.start_time} - ${record.shift.end_time}`;
            }
            
            // Status with color coding
            let statusClass = '';
            let statusText = '';
            switch(record.status) {
                case 'on_time':
                    statusClass = 'status-good';
                    statusText = '✅ On Time';
                    break;
                case 'late':
                    statusClass = 'status-warning';
                    statusText = '⚠️ Late';
                    break;
                case 'absent':
                    statusClass = 'status-bad';
                    statusText = '❌ Absent';
                    break;
                case 'incomplete':
                    statusClass = 'status-warning';
                    statusText = '⏳ Incomplete';
                    break;
                case 'off_day':
                    statusClass = '';
                    statusText = '🏖️ Off Day';
                    break;
                case 'present_no_shift':
                    statusClass = 'status-good';
                    statusText = '✅ Present (No Shift)';
                    break;
                case 'not_scheduled':
                    statusClass = '';
                    statusText = '➖ Not Scheduled';
                    break;
                default:
                    statusText = record.status;
            }
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${record.agent_name}</td>
                <td>${new Date(record.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</td>
                <td>${shiftTime}</td>
                <td>${punchInTime}</td>
                <td>${punchOutTime}</td>
                <td class="${statusClass}">${statusText}</td>
                <td>${record.hours_worked}h</td>
                <td>${record.late_minutes > 0 ? record.late_minutes : '-'}</td>
                <td>${record.early_leave_minutes > 0 ? record.early_leave_minutes : '-'}</td>
            `;
            tbody.appendChild(row);
        });
        
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="9" class="error-message">Error: ${err.message}</td></tr>`;
        summaryCards.style.display = 'none';
    }
}

function exportAttendanceToExcel() {
    const startDate = document.getElementById('attendanceStartDate').value;
    const endDate = document.getElementById('attendanceEndDate').value;
    const agentId = document.getElementById('attendanceAgentFilter').value;
    
    if (!startDate || !endDate) {
        alert('Please select a date range');
        return;
    }
    
    let url = `/api/attendance/export?start_date=${startDate}&end_date=${endDate}`;
    if (agentId) {
        url += `&agent_id=${agentId}`;
    }
    
    window.location.href = url;
}

// ==================== SCHEDULES MODAL ====================

function showSchedulesModal() {
    document.getElementById('schedulesModal').style.display = 'flex';
    // Set default dates (today to 2 weeks ahead)
    const today = new Date();
    const twoWeeksLater = new Date(today);
    twoWeeksLater.setDate(today.getDate() + 14);
    
    document.getElementById('schedulesStartDate').value = today.toISOString().split('T')[0];
    document.getElementById('schedulesEndDate').value = twoWeeksLater.toISOString().split('T')[0];
}

function hideSchedulesModal() {
    document.getElementById('schedulesModal').style.display = 'none';
}

async function loadSchedules() {
    const startDate = document.getElementById('schedulesStartDate').value;
    const endDate = document.getElementById('schedulesEndDate').value;
    const container = document.getElementById('schedulesContainer');
    
    if (!startDate || !endDate) {
        container.innerHTML = '<div class="error-message">Please select both start and end dates</div>';
        return;
    }
    
    container.innerHTML = '<div class="loading">Loading schedules...</div>';
    
    try {
        const [shiftsResponse, offdaysResponse] = await Promise.all([
            fetch(`/api/shifts?start_date=${startDate}&end_date=${endDate}`),
            fetch(`/api/offdays?start_date=${startDate}&end_date=${endDate}`)
        ]);
        
        const shiftsData = await shiftsResponse.json();
        const offdaysData = await offdaysResponse.json();
        
        if (shiftsData.error) {
            container.innerHTML = `<div class="error-message">${shiftsData.error}</div>`;
            return;
        }
        
        if (offdaysData.error) {
            container.innerHTML = `<div class="error-message">${offdaysData.error}</div>`;
            return;
        }
        
        // Group shifts by agent
        const shiftsByAgent = {};
        if (shiftsData.shifts && shiftsData.shifts.length > 0) {
            shiftsData.shifts.forEach(shift => {
                if (!shiftsByAgent[shift.agent_id]) {
                    shiftsByAgent[shift.agent_id] = {
                        agent_name: shift.agent_name,
                        shifts: []
                    };
                }
                shiftsByAgent[shift.agent_id].shifts.push(shift);
            });
        }
        
        // Group off days by agent
        const offdaysByAgent = {};
        if (offdaysData.offdays && offdaysData.offdays.length > 0) {
            offdaysData.offdays.forEach(offday => {
                if (!offdaysByAgent[offday.agent_id]) {
                    offdaysByAgent[offday.agent_id] = {
                        agent_name: offday.agent_name,
                        offdays: []
                    };
                }
                offdaysByAgent[offday.agent_id].offdays.push(offday);
            });
        }
        
        // Combine all agents
        const allAgentIds = new Set([
            ...Object.keys(shiftsByAgent),
            ...Object.keys(offdaysByAgent)
        ]);
        
        if (allAgentIds.size === 0) {
            container.innerHTML = '<div class="empty-message">No schedules or off days found for the selected date range</div>';
            return;
        }
        
        let html = '';
        for (const agentId of allAgentIds) {
            const agentName = shiftsByAgent[agentId]?.agent_name || offdaysByAgent[agentId]?.agent_name || 'Unknown';
            html += `
                <div style="margin-bottom: 20px; padding: 15px; background: var(--surface); border-radius: 8px; border: 1px solid var(--border);">
                    <h4 style="margin: 0 0 10px 0; color: var(--text);">👤 ${agentName}</h4>
            `;
            
            // Show shifts
            if (shiftsByAgent[agentId] && shiftsByAgent[agentId].shifts.length > 0) {
                html += '<div style="margin-bottom: 10px;"><strong>📅 Shifts:</strong></div>';
                html += '<div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 15px;">';
                shiftsByAgent[agentId].shifts.forEach(shift => {
                    const shiftDate = new Date(shift.shift_date + 'T00:00:00');
                    const dateStr = shiftDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                    html += `
                        <div style="padding: 8px; background: var(--surface-light); border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                            <span>📅 ${dateStr}: ${shift.start_time} - ${shift.end_time} (${shift.duration_hours}h)</span>
                            <button class="btn btn-sm btn-danger" onclick="deleteShift(${shift.id})" style="padding: 4px 8px; font-size: 11px;">🗑️ Delete</button>
                        </div>
                    `;
                });
                html += '</div>';
            }
            
            // Show off days
            if (offdaysByAgent[agentId] && offdaysByAgent[agentId].offdays.length > 0) {
                html += '<div style="margin-bottom: 10px;"><strong>🏖️ Off Days:</strong></div>';
                html += '<div style="display: flex; flex-direction: column; gap: 8px;">';
                offdaysByAgent[agentId].offdays.forEach(offday => {
                    const offDate = new Date(offday.off_date + 'T00:00:00');
                    const dateStr = offDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                    html += `
                        <div style="padding: 8px; background: #fff3cd; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                            <span>🏖️ ${dateStr}${offday.reason ? ': ' + offday.reason : ''}</span>
                            <button class="btn btn-sm btn-danger" onclick="deleteOffDay(${offday.id})" style="padding: 4px 8px; font-size: 11px;">🗑️ Delete</button>
                        </div>
                    `;
                });
                html += '</div>';
            }
            
            html += '</div>';
        }
        
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<div class="error-message">Error loading schedules: ${err.message}</div>`;
    }
}

async function deleteShift(shiftId) {
    if (!confirm('Are you sure you want to delete this shift?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/shift/${shiftId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Shift deleted successfully!');
            loadSchedules(); // Refresh the list
        } else {
            alert(data.error || 'Failed to delete shift');
        }
    } catch (err) {
        alert('Network error: ' + err.message);
    }
}

async function deleteOffDay(offdayId) {
    if (!confirm('Are you sure you want to delete this off day?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/offday/${offdayId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Off day deleted successfully!');
            loadSchedules(); // Refresh the list
        } else {
            alert(data.error || 'Failed to delete off day');
        }
    } catch (err) {
        alert('Network error: ' + err.message);
    }
}

// ==================== MANUAL BREAK MODAL ====================

function showManualBreakModal() {
    document.getElementById('manualBreakModal').style.display = 'flex';
    // Set default dates to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('manualBreakStartDate').value = today;
    document.getElementById('manualBreakEndDate').value = today;
    // Clear previous values
    document.getElementById('manualBreakAgent').value = '';
    document.getElementById('manualBreakType').value = '';
    document.getElementById('manualBreakStartTime').value = '';
    document.getElementById('manualBreakEndTime').value = '';
    document.getElementById('manualBreakNotes').value = '';
    document.getElementById('manualBreakStartScreenshot').value = '';
    document.getElementById('manualBreakEndScreenshot').value = '';
    document.getElementById('manualBreakError').textContent = '';
    document.getElementById('manualBreakSuccess').style.display = 'none';
}

function hideManualBreakModal() {
    document.getElementById('manualBreakModal').style.display = 'none';
}

async function submitManualBreak() {
    const agentId = document.getElementById('manualBreakAgent').value;
    const breakType = document.getElementById('manualBreakType').value;
    const startDate = document.getElementById('manualBreakStartDate').value;
    const startTime = document.getElementById('manualBreakStartTime').value;
    const endDate = document.getElementById('manualBreakEndDate').value;
    const endTime = document.getElementById('manualBreakEndTime').value;
    const notes = document.getElementById('manualBreakNotes').value;
    const startScreenshot = document.getElementById('manualBreakStartScreenshot').files[0];
    const endScreenshot = document.getElementById('manualBreakEndScreenshot').files[0];
    
    const errorEl = document.getElementById('manualBreakError');
    const successEl = document.getElementById('manualBreakSuccess');
    
    // Validation - only agent, break type, start date, and start time are required
    if (!agentId || !breakType || !startDate || !startTime) {
        errorEl.textContent = 'Please fill in all required fields: Agent, Break Type, Start Date, and Start Time';
        return;
    }
    
    errorEl.textContent = '';
    successEl.style.display = 'none';
    
    // Create FormData
    const formData = new FormData();
    formData.append('agent_id', agentId);
    formData.append('break_type', breakType);
    formData.append('start_date', startDate);
    formData.append('start_time', startTime);
    // End date and time are optional
    if (endDate) formData.append('end_date', endDate);
    if (endTime) formData.append('end_time', endTime);
    if (notes) formData.append('notes', notes);
    if (startScreenshot) formData.append('start_screenshot', startScreenshot);
    if (endScreenshot) formData.append('end_screenshot', endScreenshot);
    
    try {
        const response = await fetch('/api/break/manual', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            successEl.textContent = data.message || 'Break created successfully!';
            successEl.style.display = 'block';
            errorEl.textContent = '';
            
            // Clear form after 2 seconds and reload breaks
            setTimeout(() => {
                hideManualBreakModal();
                loadBreaks();
            }, 2000);
        } else {
            errorEl.textContent = data.error || 'Failed to create break';
            successEl.style.display = 'none';
        }
    } catch (err) {
        errorEl.textContent = 'Network error: ' + err.message;
        successEl.style.display = 'none';
    }
}

// ==================== SHIFT MANAGEMENT ====================

function showAddShiftModal() {
    document.getElementById('addShiftModal').style.display = 'flex';
    
    // Set default date range (today to 2 weeks from now)
    const today = new Date();
    const twoWeeksLater = new Date(today);
    twoWeeksLater.setDate(today.getDate() + 14);
    
    document.getElementById('shiftPeriodStartDate').value = today.toISOString().split('T')[0];
    document.getElementById('shiftPeriodEndDate').value = twoWeeksLater.toISOString().split('T')[0];
    
    // Set default time (4 PM to 1 AM)
    document.getElementById('shiftStartTime').value = '16:00';
    document.getElementById('shiftEndTime').value = '01:00';
    
    // Clear previous agent selections
    document.querySelectorAll('.shift-agent-checkbox').forEach(cb => {
        cb.checked = false;
    });
    
    // Clear error message
    const errorEl = document.getElementById('addShiftError');
    if (errorEl) {
        errorEl.style.display = 'none';
        errorEl.textContent = '';
    }
}

function hideAddShiftModal() {
    document.getElementById('addShiftModal').style.display = 'none';
}

async function submitShift() {
    // Get selected agents
    const selectedAgents = [];
    document.querySelectorAll('.shift-agent-checkbox:checked').forEach(cb => {
        selectedAgents.push(parseInt(cb.value));
    });
    
    const startTime = document.getElementById('shiftStartTime').value;
    const endTime = document.getElementById('shiftEndTime').value;
    const periodStartDate = document.getElementById('shiftPeriodStartDate').value;
    const periodEndDate = document.getElementById('shiftPeriodEndDate').value;
    
    // Get selected working days
    const workingDays = [];
    const dayCheckboxes = [
        document.getElementById('dayMon'),
        document.getElementById('dayTue'),
        document.getElementById('dayWed'),
        document.getElementById('dayThu'),
        document.getElementById('dayFri'),
        document.getElementById('daySat'),
        document.getElementById('daySun')
    ];
    
    dayCheckboxes.forEach((cb, index) => {
        if (cb && cb.checked) {
            workingDays.push(index); // 0=Monday, 1=Tuesday, etc.
        }
    });
    
    if (selectedAgents.length === 0) {
        const errorEl = document.getElementById('addShiftError');
        if (errorEl) {
            errorEl.textContent = 'Please select at least one agent';
            errorEl.style.display = 'block';
        } else {
            alert('Please select at least one agent');
        }
        return;
    }
    
    if (!startTime || !endTime || !periodStartDate || !periodEndDate) {
        const errorEl = document.getElementById('addShiftError');
        if (errorEl) {
            errorEl.textContent = 'Please fill in all required fields';
            errorEl.style.display = 'block';
        } else {
            alert('Please fill in all required fields');
        }
        return;
    }
    
    if (workingDays.length === 0) {
        const errorEl = document.getElementById('addShiftError');
        if (errorEl) {
            errorEl.textContent = 'Please select at least one working day';
            errorEl.style.display = 'block';
        } else {
            alert('Please select at least one working day');
        }
        return;
    }
    
    const errorEl = document.getElementById('addShiftError');
    if (errorEl) {
        errorEl.style.display = 'none';
    }
    
    try {
        const response = await fetch('/api/shift/schedule', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                agent_ids: selectedAgents,
                start_time: startTime,
                end_time: endTime,
                period_start_date: periodStartDate,
                period_end_date: periodEndDate,
                working_days: workingDays
            })
        });
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to parse error message from JSON
            try {
                const errorData = await response.json();
                const errorMsg = errorData.error || `Server error: ${response.status}`;
                if (errorEl) {
                    errorEl.textContent = errorMsg;
                    errorEl.style.display = 'block';
                } else {
                    alert(errorMsg);
                }
            } catch {
                // If not JSON, show status text
                const errorMsg = `Server error: ${response.status} ${response.statusText}`;
                if (errorEl) {
                    errorEl.textContent = errorMsg;
                    errorEl.style.display = 'block';
                } else {
                    alert(errorMsg);
                }
            }
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            alert(data.message || `Schedule created successfully! Created ${data.shifts_created || 0} shifts and ${data.offdays_created || 0} off days.`);
            hideAddShiftModal();
            loadSchedules(); // Refresh schedules if modal is open
            // Refresh breaks if on breaks tab
            if (document.getElementById('tab-breaks') && document.getElementById('tab-breaks').classList.contains('active')) {
                loadBreaks();
            }
        } else {
            const errorMsg = data.error || 'Failed to create schedule';
            if (errorEl) {
                errorEl.textContent = errorMsg;
                errorEl.style.display = 'block';
            } else {
                alert(errorMsg);
            }
        }
    } catch (err) {
        const errorMsg = 'Network error: ' + err.message;
        if (errorEl) {
            errorEl.textContent = errorMsg;
            errorEl.style.display = 'block';
        } else {
            alert(errorMsg);
            console.error('Error creating schedule:', err);
        }
    }
}

// ==================== OFF DAY MANAGEMENT ====================

function showAddOffDayModal() {
    document.getElementById('addOffDayModal').style.display = 'flex';
    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('offDayDate').value = today;
    // Clear previous values
    document.getElementById('offDayAgent').value = '';
    document.getElementById('offDayReason').value = '';
}

function hideAddOffDayModal() {
    document.getElementById('addOffDayModal').style.display = 'none';
}

async function submitOffDay() {
    const agentId = document.getElementById('offDayAgent').value;
    const offDate = document.getElementById('offDayDate').value;
    const reason = document.getElementById('offDayReason').value;
    
    if (!agentId || !offDate) {
        alert('Please fill in Agent and Date fields');
        return;
    }
    
    try {
        const response = await fetch('/api/offday', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                agent_id: parseInt(agentId),
                off_date: offDate,
                reason: reason || ''
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(data.message || 'Off day created successfully!');
            hideAddOffDayModal();
        } else {
            alert(data.error || 'Failed to create off day');
        }
    } catch (err) {
        alert('Network error: ' + err.message);
    }
}

// Close modals when clicking outside
window.onclick = function(event) {
    const schedulesModal = document.getElementById('schedulesModal');
    const manualBreakModal = document.getElementById('manualBreakModal');
    const addShiftModal = document.getElementById('addShiftModal');
    const addOffDayModal = document.getElementById('addOffDayModal');
    
    if (event.target === schedulesModal) {
        hideSchedulesModal();
    }
    if (event.target === manualBreakModal) {
        hideManualBreakModal();
    }
    if (event.target === addShiftModal) {
        hideAddShiftModal();
    }
    if (event.target === addOffDayModal) {
        hideAddOffDayModal();
    }
}

