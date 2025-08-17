// A.R.G.U.S. v2.0 JavaScript

let socket;
let trafficChart;

// WebSocket接続
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Socket.IO接続
    socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocket接続完了');
    });
    
    socket.on('stats_update', function(data) {
        updateDashboardStats(data);
    });
    
    // 初期データ読み込み
    loadStatistics();
    loadRules();
    
    // チャート初期化
    initializeChart();
    
    // デフォルトでダッシュボードを表示
    showTab('dashboard');
}

// タブ切り替え
function showTab(tabName) {
    // すべてのタブを非アクティブに
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // 選択されたタブをアクティブに
    document.getElementById(tabName).classList.add('active');
    document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
    
    // タブ固有の処理
    if (tabName === 'traffic') {
        refreshTrafficLogs();
    } else if (tabName === 'rules') {
        loadRules();
    }
}

// 統計情報読み込み
async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        const data = await response.json();
        updateDashboardStats(data);
        updateChart(data.stats);
    } catch (error) {
        console.error('統計情報読み込みエラー:', error);
    }
}

// ダッシュボード統計更新
function updateDashboardStats(data) {
    document.getElementById('total-requests').textContent = data.total_requests || 0;
    document.getElementById('total-blocked').textContent = data.total_blocked || 0;
    document.getElementById('total-bytes').textContent = formatBytes(data.total_bytes || 0);
    
    // 最近のログ更新
    updateRecentLogs(data.recent_logs || []);
}

// 最近のログ更新
function updateRecentLogs(logs) {
    const container = document.getElementById('recent-logs');
    container.innerHTML = '';
    
    logs.slice(0, 10).forEach(log => {
        const logItem = document.createElement('div');
        logItem.className = `log-item ${log.is_blocked ? 'blocked' : ''}`;
        
        const time = new Date(log.timestamp).toLocaleTimeString();
        const status = log.is_blocked ? 'ブロック' : '許可';
        const statusClass = log.is_blocked ? 'blocked' : 'allowed';
        
        logItem.innerHTML = `
            <span class="log-time">${time}</span>
            <div class="log-content">
                <strong>${log.client_ip}</strong> → 
                <code>${truncateUrl(log.url, 50)}</code>
            </div>
            <span class="log-status ${statusClass}">${status}</span>
        `;
        
        container.appendChild(logItem);
    });
}

// チャート初期化
function initializeChart() {
    const ctx = document.getElementById('trafficChart').getContext('2d');
    trafficChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '総リクエスト',
                data: [],
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4
            }, {
                label: 'ブロック',
                data: [],
                borderColor: '#f44336',
                backgroundColor: 'rgba(244, 67, 54, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// チャート更新
function updateChart(stats) {
    if (!trafficChart || !stats) return;
    
    const labels = [];
    const totalData = [];
    const blockedData = [];
    
    stats.slice(-24).forEach(stat => {
        const label = `${stat.date} ${stat.hour}:00`;
        labels.push(label);
        totalData.push(stat.total_requests || 0);
        blockedData.push(stat.blocked_requests || 0);
    });
    
    trafficChart.data.labels = labels;
    trafficChart.data.datasets[0].data = totalData;
    trafficChart.data.datasets[1].data = blockedData;
    trafficChart.update();
}

// 通信ログ更新
async function refreshTrafficLogs() {
    try {
        const response = await fetch('/api/traffic-logs?limit=100');
        const logs = await response.json();
        updateTrafficTable(logs);
    } catch (error) {
        console.error('通信ログ読み込みエラー:', error);
    }
}

// 通信テーブル更新
function updateTrafficTable(logs) {
    const tbody = document.getElementById('traffic-tbody');
    tbody.innerHTML = '';
    
    logs.forEach(log => {
        const row = document.createElement('tr');
        row.className = log.is_blocked ? 'blocked-row' : '';
        
        const time = new Date(log.timestamp).toLocaleString();
        const status = log.is_blocked ? 'ブロック' : log.status_code || 'N/A';
        const statusClass = log.is_blocked ? 'blocked' : 'allowed';
        
        row.innerHTML = `
            <td>${time}</td>
            <td>${log.client_ip}</td>
            <td>${log.method}</td>
            <td title="${log.url}">${truncateUrl(log.url, 60)}</td>
            <td><span class="log-status ${statusClass}">${status}</span></td>
            <td>${log.is_blocked ? '🚫' : '✅'}</td>
            <td><button class="btn btn-sm" onclick="showTrafficDetail(${log.id})">詳細</button></td>
        `;
        
        tbody.appendChild(row);
    });
}

// 通信詳細表示
async function showTrafficDetail(logId) {
    try {
        const response = await fetch(`/api/traffic-detail/${logId}`);
        const detail = await response.json();
        
        if (detail.error) {
            alert(detail.error);
            return;
        }
        
        const modal = document.getElementById('detail-modal');
        const content = document.getElementById('detail-content');
        
        content.innerHTML = `
            <div class="detail-section">
                <h3>基本情報</h3>
                <p><strong>時刻:</strong> ${new Date(detail.timestamp).toLocaleString()}</p>
                <p><strong>クライアント:</strong> ${detail.client_ip}</p>
                <p><strong>メソッド:</strong> ${detail.method}</p>
                <p><strong>URL:</strong> <code>${detail.url}</code></p>
                <p><strong>ステータス:</strong> ${detail.status_code || 'N/A'}</p>
                <p><strong>ブロック状態:</strong> ${detail.is_blocked ? '🚫 ブロック済み' : '✅ 許可済み'}</p>
                ${detail.block_reason ? `<p><strong>ブロック理由:</strong> ${detail.block_reason}</p>` : ''}
            </div>
            
            <div class="detail-section">
                <h3>リクエストヘッダー</h3>
                <pre>${formatHeaders(detail.request_headers)}</pre>
            </div>
            
            ${detail.request_body ? `
            <div class="detail-section">
                <h3>リクエストボディ</h3>
                <pre>${detail.request_body}</pre>
            </div>
            ` : ''}
            
            <div class="detail-section">
                <h3>レスポンスヘッダー</h3>
                <pre>${formatHeaders(detail.response_headers)}</pre>
            </div>
            
            ${detail.response_body ? `
            <div class="detail-section">
                <h3>レスポンスボディ</h3>
                <pre>${truncateText(detail.response_body, 5000)}</pre>
            </div>
            ` : ''}
        `;
        
        modal.style.display = 'block';
    } catch (error) {
        console.error('詳細情報読み込みエラー:', error);
        alert('詳細情報の読み込みに失敗しました');
    }
}

// 詳細モーダル閉じる
function closeDetailModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

// ルール読み込み
async function loadRules() {
    try {
        const response = await fetch('/api/rules');
        const data = await response.json();
        
        updateRulesList('domains-list', data.domains, 'domain');
        updateRulesList('keywords-list', data.keywords, 'keyword');
        
        // フィルタリングスイッチ更新
        document.getElementById('filtering-toggle').checked = data.settings.filtering_enabled;
    } catch (error) {
        console.error('ルール読み込みエラー:', error);
    }
}

// ルールリスト更新
function updateRulesList(listId, rules, type) {
    const list = document.getElementById(listId);
    list.innerHTML = '';
    
    rules.forEach(rule => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span class="rule-text">${rule}</span>
            <button class="rule-delete" onclick="removeRule('${type}', '${rule}')">削除</button>
        `;
        list.appendChild(li);
    });
}

// ドメイン追加
async function addDomain() {
    const input = document.getElementById('new-domain');
    const domain = input.value.trim();
    
    if (!domain) {
        alert('ドメインを入力してください');
        return;
    }
    
    try {
        const response = await fetch('/api/rules/domains', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({domain: domain})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            input.value = '';
            loadRules();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.error, 'error');
        }
    } catch (error) {
        console.error('ドメイン追加エラー:', error);
        showMessage('ドメインの追加に失敗しました', 'error');
    }
}

// キーワード追加
async function addKeyword() {
    const input = document.getElementById('new-keyword');
    const keyword = input.value.trim();
    
    if (!keyword) {
        alert('キーワードを入力してください');
        return;
    }
    
    try {
        const response = await fetch('/api/rules/keywords', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({keyword: keyword})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            input.value = '';
            loadRules();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.error, 'error');
        }
    } catch (error) {
        console.error('キーワード追加エラー:', error);
        showMessage('キーワードの追加に失敗しました', 'error');
    }
}

// ルール削除
async function removeRule(type, rule) {
    if (!confirm(`「${rule}」を削除しますか？`)) {
        return;
    }
    
    try {
        const endpoint = type === 'domain' ? 'domains' : 'keywords';
        const response = await fetch(`/api/rules/${endpoint}/${encodeURIComponent(rule)}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            loadRules();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.error, 'error');
        }
    } catch (error) {
        console.error('ルール削除エラー:', error);
        showMessage('ルールの削除に失敗しました', 'error');
    }
}

// フィルタリング有効/無効切り替え
async function toggleFiltering() {
    const enabled = document.getElementById('filtering-toggle').checked;
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({filtering_enabled: enabled})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(result.message, 'success');
        } else {
            showMessage(result.error || '設定の更新に失敗しました', 'error');
        }
    } catch (error) {
        console.error('設定更新エラー:', error);
        showMessage('設定の更新に失敗しました', 'error');
    }
}


// 証明書ダウンロード
function downloadCertificate() {
    window.location.href = '/api/certificate';
}

// ユーティリティ関数
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function truncateUrl(url, maxLength) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '\n... (切り詰められました)';
}

function formatHeaders(headers) {
    if (!headers) return '(なし)';
    if (typeof headers === 'string') {
        try {
            headers = JSON.parse(headers);
        } catch {
            return headers;
        }
    }
    return Object.entries(headers)
        .map(([key, value]) => `${key}: ${value}`)
        .join('\n');
}

function showMessage(message, type) {
    // 簡易メッセージ表示（改善の余地あり）
    const color = type === 'success' ? '#4caf50' : '#f44336';
    const div = document.createElement('div');
    div.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${color};
        color: white;
        border-radius: 5px;
        z-index: 9999;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    `;
    div.textContent = message;
    document.body.appendChild(div);
    
    setTimeout(() => {
        div.remove();
    }, 3000);
}

// モーダル外クリックで閉じる
window.onclick = function(event) {
    const modal = document.getElementById('detail-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
};

// キーボードショートカット
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeDetailModal();
    }
});