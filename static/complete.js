let CURRENT_USER = null;

function setCurrentUser(user){
  if (user && user.id){
    CURRENT_USER = {
      id: user.id,
      email: user.email,
      is_paid: !!user.is_paid,
      free_sample_used: !!user.free_sample_used
    };
  } else {
    CURRENT_USER = null;
  }
  window.CURRENT_USER = CURRENT_USER;
  updateButtons();
}

async function refreshCurrentUser(){
  try{
    const res = await fetch('/api/current_user', { credentials: 'include' });
    if (!res.ok){ setCurrentUser(null); return null; }
    const data = await res.json().catch(()=>null);
    if (data && data.id){ setCurrentUser(data); }
    else setCurrentUser(null);
    return CURRENT_USER;
  }catch(e){ return null; }
}

function updateButtons(){
  const sampleBtn = document.getElementById('generate-1');
  const planBtn = document.getElementById('generate-30');
  const user = CURRENT_USER || {};
  const isPaid = !!user.is_paid;
  const sampleUsed = !!user.free_sample_used;
  if (sampleBtn){
    if (!isPaid && sampleUsed){
      sampleBtn.disabled = true;
      sampleBtn.classList.add('opacity-60');
      sampleBtn.textContent = 'Free sample used';
    } else {
      sampleBtn.disabled = false;
      sampleBtn.classList.remove('opacity-60');
      sampleBtn.textContent = 'Generate 1-day sample';
    }
  }
  if (planBtn){
    planBtn.textContent = isPaid ? 'Generate 30-day plan' : 'Unlock 30-day plan';
  }
}

async function fetchProfile(){
  const res = await fetch('/api/profile', { credentials: 'include' });
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

function handleAuthRequired(){
  alert('Please sign in to generate posts.');
  window.location.href = '/';
}

async function requestGenerate(payload){
  const res = await fetch('/api/generate', {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if (res.status === 401){
    handleAuthRequired();
    throw new Error('Authentication required');
  }
  if (res.status === 403){
    let msg = 'Subscribe to continue.';
    try{
      const body = await res.json().catch(()=>null);
      if (body && body.error) msg = body.error;
    }catch(e){}
    alert(msg);
    throw new Error(msg);
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
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

async function main(){
  await refreshCurrentUser();
  const profile = await fetchProfile();
  if (!profile) return;
  renderSummary(profile);
  const versionEl = document.getElementById('summary-content-version');
  if (versionEl) versionEl.textContent = (window.CONTENT_META && window.CONTENT_META.version) ? window.CONTENT_META.version : 'local';

  const sampleBtn = document.getElementById('generate-1');
  const planBtn = document.getElementById('generate-30');

  sampleBtn?.addEventListener('click', async () => {
    if (!CURRENT_USER){ handleAuthRequired(); return; }
    if (!CURRENT_USER.is_paid && CURRENT_USER.free_sample_used){ alert('You already used your free sample. Subscribe to unlock unlimited posts.'); return; }
    try{
      const data = await requestGenerate({...profile, days: 1});
      window.RESULTS = data.posts || [];
      renderPostsComplete(window.RESULTS);
      await refreshCurrentUser();
    }catch(err){ if (err && err.message) console.debug(err.message); }
  });

  planBtn?.addEventListener('click', async () => {
    if (!CURRENT_USER){ handleAuthRequired(); return; }
    if (!CURRENT_USER.is_paid){ alert('Subscribe to unlock full plans and reels.'); return; }
    try{
      const data = await requestGenerate({...profile, days: 30});
      renderPostsComplete(data.posts || []);
      await refreshCurrentUser();
    }catch(err){ if (err && err.message) console.debug(err.message); }
  });
}

main().catch(console.error);
