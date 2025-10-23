async function fetchProfile(){
  const res = await fetch('/api/profile');
  if (!res.ok) return null;
  return res.json();
}

function renderSummary(p){
  const rows = [
    ['Industry', p.industry || '—'],
    ['Tone', p.tone || '—'],
    ['Platforms', (p.platforms||[]).join(', ') || '—'],
    ['Goals', (p.goals||[]).join(', ') || '—'],
    ['Company', p.company || '—']
  ];
  const container = document.getElementById('summary-rows');
  container.innerHTML = '';
  rows.forEach(([k,v]) => {
    const el = document.createElement('div');
    el.className = 'text-sm';
    el.innerHTML = `<strong class="block">${k}</strong><span>${v}</span>`;
    container.appendChild(el);
  });
}

async function main(){
  const profile = await fetchProfile();
  if (!profile) return;
  renderSummary(profile);
  document.getElementById('summary-content-version').textContent = (window.CONTENT_META && window.CONTENT_META.version) ? window.CONTENT_META.version : 'local';

  document.getElementById('generate-1').addEventListener('click', async () => {
    const data = await fetch('/api/generate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({...profile, days:1}) });
    const j = await data.json();
    window.RESULTS = j.posts || [];
    renderPostsComplete(j.posts || []);
  });
  document.getElementById('generate-30').addEventListener('click', async () => {
    const data = await fetch('/api/generate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({...profile, days:30}) });
    const j = await data.json();
    renderPostsComplete(j.posts || []);
  });
}

function renderPostsComplete(posts){
  const out = document.getElementById('results-complete');
  out.innerHTML = '';
  if (!posts.length) { out.innerHTML = '<div class="text-sm text-slate-600">No posts yet.</div>'; return; }
  posts.forEach(p=>{
    const el = document.createElement('div'); el.className = 'border rounded p-3';
    el.innerHTML = `<div class="text-sm font-medium mb-1">${p.platform} • ${p.pillar}</div><pre class="caption text-sm">${p.caption}</pre>`;
    out.appendChild(el);
  });
}

main().catch(console.error);
