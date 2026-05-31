const queryInput = document.getElementById('research-query');
const runButton = document.getElementById('run-research');
const emptyState = document.getElementById('research-empty');
const resultBody = document.getElementById('research-result');
const resultQuery = document.getElementById('result-query');
const resultSummary = document.getElementById('result-summary');
const resultSources = document.getElementById('result-sources');
const matchCount = document.getElementById('match-count');

function renderResearchResult(data) {
  resultQuery.innerText = data.query || 'Research query';
  resultSummary.innerText = data.summary || 'No governed context was returned.';
  matchCount.innerText = `${data.matchesCount || 0} matches`;
  resultSources.innerHTML = (data.sources || []).map(source => `<li>${source}</li>`).join('');
  emptyState.classList.add('hide');
  resultBody.classList.remove('hide');
}

async function runResearch() {
  const query = queryInput.value.trim();
  if (!query) {
    queryInput.focus();
    return;
  }

  runButton.disabled = true;
  runButton.innerText = 'Researching...';
  try {
    const response = await fetch(`${API_BASE}/workflows/analyst/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
    renderResearchResult(data);
  } catch (error) {
    renderResearchResult({
      query,
      summary: `Research failed: ${error.message}`,
      matchesCount: 0,
      sources: []
    });
  } finally {
    runButton.disabled = false;
    runButton.innerText = 'Run Research';
  }
}

runButton.addEventListener('click', runResearch);
queryInput.addEventListener('keydown', event => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') runResearch();
});

document.querySelectorAll('[data-query]').forEach(button => {
  button.addEventListener('click', () => {
    queryInput.value = button.getAttribute('data-query') || '';
    queryInput.focus();
  });
});
