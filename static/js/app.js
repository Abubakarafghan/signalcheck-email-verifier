const form = document.querySelector('#verify-form');
const previewButton = document.querySelector('#preview-btn');
const startButton = document.querySelector('#start-btn');
const preview = document.querySelector('#preview');
const statusPill = document.querySelector('#status-pill');
const progressBar = document.querySelector('#progress-bar');
const progressNumber = document.querySelector('#progress-number');
const progressLabel = document.querySelector('#progress-label');
const pauseButton = document.querySelector('#pause-btn');
const cancelButton = document.querySelector('#cancel-btn');
let jobId = null;
let pollTimer = null;
let latestResults = [];
let currentPage = 1;
let pageSize = 20;

const themeToggle = document.querySelector('#theme-toggle');
const themeLabel = document.querySelector('#theme-label');
const savedTheme = localStorage.getItem('signalcheck-theme');
if (savedTheme === 'dark') document.documentElement.dataset.theme = 'dark';
function updateThemeLabel() {
  const dark = document.documentElement.dataset.theme === 'dark';
  themeLabel.textContent = dark ? 'Light mode' : 'Dark mode';
  themeToggle.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
}
updateThemeLabel();
themeToggle.addEventListener('click', () => {
  const dark = document.documentElement.dataset.theme === 'dark';
  document.documentElement.dataset.theme = dark ? 'light' : 'dark';
  localStorage.setItem('signalcheck-theme', dark ? 'light' : 'dark');
  updateThemeLabel();
});

async function sendForm(url, method = 'POST') {
  const response = await fetch(url, { method, body: new FormData(form) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function showError(error) { preview.classList.remove('hidden'); preview.textContent = error.message; preview.style.background = '#f8e6e1'; }
function renderResults(rows) {
  latestResults = rows;
  const counts = rows.reduce((all, row) => { all[row.final_status] = (all[row.final_status] || 0) + 1; return all; }, {});
  document.querySelector('#summary').innerHTML = Object.entries(counts).map(([key, value]) => `<span><b>${value}</b> ${key.replaceAll('_', ' ')}</span>`).join('');
  renderPage();
}
function renderPage() {
  const total = latestResults.length;
  const effectivePageSize = pageSize === 'all' ? Math.max(total, 1) : pageSize;
  const pageCount = Math.max(1, Math.ceil(total / effectivePageSize));
  currentPage = Math.min(currentPage, pageCount);
  const start = total ? (currentPage - 1) * effectivePageSize : 0;
  const visibleRows = latestResults.slice(start, start + effectivePageSize);
  document.querySelector('#results-body').innerHTML = visibleRows.length ? visibleRows.map(row => `<tr><td>${escapeHtml(row.email)}</td><td><span class="badge ${row.mx_status === 'FOUND' || row.mx_status === 'IMPLICIT_MX' ? 'good' : row.mx_status === 'MISSING' ? 'bad' : 'warn'}">${row.mx_status}</span></td><td>${row.role_based ? '<span class="badge warn">ROLE</span>' : '—'}</td><td>${escapeHtml(row.smtp_result)}</td><td><span class="badge ${row.final_status === 'LIKELY_VALID' || row.final_status === 'ACCEPTED_BY_SERVER' ? 'good' : row.final_status === 'INVALID' ? 'bad' : 'warn'}">${row.final_status}</span></td><td>${escapeHtml(row.verification_reason)}</td></tr>`).join('') : '<tr><td colspan="6" class="empty">No results yet.</td></tr>';
  const shownStart = total ? start + 1 : 0;
  const shownEnd = Math.min(start + effectivePageSize, total);
  document.querySelector('#page-status').textContent = `Showing ${shownStart}–${shownEnd} of ${total}`;
  document.querySelector('#previous-page').disabled = currentPage <= 1;
  document.querySelector('#next-page').disabled = currentPage >= pageCount;
}
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[character])); }
document.querySelector('#previous-page').addEventListener('click', () => { currentPage -= 1; renderPage(); });
document.querySelector('#next-page').addEventListener('click', () => { currentPage += 1; renderPage(); });
document.querySelector('#page-size').addEventListener('change', event => { pageSize = event.target.value === 'all' ? 'all' : Number(event.target.value); currentPage = 1; renderPage(); });
previewButton.addEventListener('click', async () => { try { const data = await sendForm('/api/preview'); preview.classList.remove('hidden'); preview.style.background = ''; preview.innerHTML = `<strong>${data.total} addresses found</strong> · ${data.duplicates} duplicates<br>${data.emails.map(escapeHtml).join('<br>')}`; startButton.classList.remove('hidden'); } catch (error) { showError(error); } });
form.addEventListener('submit', async event => { event.preventDefault(); try { const data = await sendForm('/api/jobs'); jobId = data.job_id; statusPill.textContent = 'RUNNING'; statusPill.className = 'pill live'; pauseButton.disabled = false; cancelButton.disabled = false; pollTimer = setInterval(updateJob, 500); } catch (error) { showError(error); } });
async function updateJob() { const response = await fetch(`/api/jobs/${jobId}`); const job = await response.json(); const percent = job.total ? Math.round(job.processed / job.total * 100) : 0; progressBar.style.width = `${percent}%`; progressNumber.textContent = `${percent}%`; progressLabel.textContent = job.status === 'COMPLETE' ? 'Verification complete' : job.status === 'CANCELLED' ? 'Verification cancelled' : 'Checking signals'; document.querySelector('#processed').textContent = job.processed; document.querySelector('#remaining').textContent = Math.max(0, job.total - job.processed); document.querySelector('#duplicates').textContent = document.querySelector('#preview').textContent.match(/(\d+) duplicates/)?.[1] || 0; renderResults(job.results); if (job.status !== 'RUNNING') { clearInterval(pollTimer); statusPill.textContent = job.status; statusPill.className = `pill ${job.status === 'COMPLETE' ? 'done' : 'idle'}`; pauseButton.disabled = true; cancelButton.disabled = true; document.querySelector('#valid-btn').disabled = false; document.querySelector('#invalid-btn').disabled = false; document.querySelector('#csv-btn').disabled = false; document.querySelector('#xlsx-btn').disabled = false; } }
async function jobAction(action) { await fetch(`/api/jobs/${jobId}/${action}`, {method:'POST'}); if (action === 'pause') { pauseButton.textContent = 'Resume'; pauseButton.dataset.paused = 'true'; } else if (action === 'resume') { pauseButton.textContent = 'Pause'; pauseButton.dataset.paused = 'false'; } }
pauseButton.addEventListener('click', () => jobAction(pauseButton.dataset.paused === 'true' ? 'resume' : 'pause')); cancelButton.addEventListener('click', () => jobAction('cancel'));
async function exportResults(format) { const data = new FormData(); data.set('format', format); const response = await fetch(`/api/export/${jobId}`, {method:'POST', body:data}); const blob = await response.blob(); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `email-results.${format}`; link.click(); URL.revokeObjectURL(link.href); }
async function exportCategory(category) { const response = await fetch(`/api/export/${jobId}/${category}`, {method:'POST'}); const blob = await response.blob(); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${category}-emails.csv`; link.click(); URL.revokeObjectURL(link.href); }
document.querySelector('#csv-btn').addEventListener('click', () => exportResults('csv')); document.querySelector('#xlsx-btn').addEventListener('click', () => exportResults('xlsx'));
document.querySelector('#valid-btn').addEventListener('click', () => exportCategory('valid')); document.querySelector('#invalid-btn').addEventListener('click', () => exportCategory('invalid'));
