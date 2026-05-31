let activeChannel = 'slack';
let narrativesCache = {
    slack: '',
    board: ''
};

const tabSlack = document.getElementById('tab-slack');
const tabBoard = document.getElementById('tab-board');
const previewSlack = document.getElementById('preview-slack');
const previewBoard = document.getElementById('preview-board');

const slackContent = document.getElementById('slack-msg-content');
const boardContent = document.getElementById('board-msg-content');

// Helper Slack style parser to HTML
function parseSlackMarkup(text) {
    if (!text) return '';
    let html = text;
    // Replace *bold* with <strong>
    html = html.replace(/\*(.*?)\*/g, '<strong>$1</strong>');
    // Replace _italic_ with <em>
    html = html.replace(/_(.*?)_/g, '<em>$1</em>');
    // Replace ~strike~ with <del>
    html = html.replace(/~(.*?)~/g, '<del>$1</del>');
    // Render links or tags
    html = html.replace(/@(\w+)/g, '<span style="color:#36c5f0; cursor:pointer;">@$1</span>');
    return html.replace(/\n/g, '<br/>');
}

// Helper Board Slide markdown parser to HTML
function parseBoardMarkup(text) {
    if (!text) return '';
    let html = text;
    
    // Headers
    html = html.replace(/### (.*?)(<br\/>|$|\n)/g, '<h2>$1</h2>');
    html = html.replace(/## (.*?)(<br\/>|$|\n)/g, '<h2>$1</h2>');
    html = html.replace(/# (.*?)(<br\/>|$|\n)/g, '<h1>$1</h1>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Bullets
    html = html.replace(/\* (.*?)(<br\/>|$|\n)/g, '<li>$1</li>');
    
    return html.replace(/\n/g, '<br/>');
}

// Update Active Channel Tab
function switchTab(channel) {
    activeChannel = channel;
    
    if (channel === 'slack') {
        tabSlack.classList.add('active');
        tabBoard.classList.remove('active');
        previewSlack.classList.remove('hide');
        previewBoard.classList.add('hide');
    } else {
        tabSlack.classList.remove('active');
        tabBoard.classList.add('active');
        previewSlack.classList.add('hide');
        previewBoard.classList.remove('hide');
    }
}

tabSlack.addEventListener('click', () => switchTab('slack'));
tabBoard.addEventListener('click', () => switchTab('board'));

// Perform Copywriting Generation
async function generateNarrative() {
    const btn = document.getElementById('nar-btn');
    btn.disabled = true;
    btn.innerHTML = '✨ Generating commenting copy...';
    
    const metric = document.getElementById('nar-metric').value.trim();
    const val = document.getElementById('nar-val').value.trim();
    const growth = document.getElementById('nar-growth').value.trim();
    const driver = document.getElementById('nar-driver').value.trim();
    const directives = document.getElementById('nar-prompt').value.trim();
    
    try {
        // We will fetch both channels concurrently to load caches
        const [slackRes, boardRes] = await Promise.all([
            fetch(`${API_BASE}/workflows/analytics/business-narratives`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channel: 'slack', metricName: metric, value: val, growthRate: growth, primaryDriver: driver, prompt: directives })
            }),
            fetch(`${API_BASE}/workflows/analytics/business-narratives`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channel: 'board', metricName: metric, value: val, growthRate: growth, primaryDriver: driver, prompt: directives })
            })
        ]);
        
        if (!slackRes.ok || !boardRes.ok) {
            throw new Error("Outbound gateway connection failed.");
        }
        
        const slackData = await slackRes.json();
        const boardData = await boardRes.json();
        
        narrativesCache.slack = slackData.narrative;
        narrativesCache.board = boardData.narrative;
        
        slackContent.innerHTML = parseSlackMarkup(slackData.narrative);
        boardContent.innerHTML = parseBoardMarkup(boardData.narrative);
        
    } catch(err) {
        alert("Copywriting generation failed: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '✨ Synthesize Story Narrative';
    }
}

document.getElementById('nar-btn').addEventListener('click', generateNarrative);

// Copy copywriting contents to clipboard
document.getElementById('btn-copy-clipboard').addEventListener('click', () => {
    const textToCopy = narrativesCache[activeChannel] || (activeChannel === 'slack' ? slackContent.innerText : boardContent.innerText);
    
    navigator.clipboard.writeText(textToCopy).then(() => {
        const toast = document.getElementById('toast');
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 2000);
    }).catch(err => {
        console.error("Clipboard copy failed:", err);
    });
});

// Run initial commentary generation
generateNarrative();