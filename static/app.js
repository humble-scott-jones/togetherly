let CFG = null;
let FLAGS = null;

async function loadFlags(){
  try{
    const r = await fetch('/static/content/flags.json', { cache: 'no-store' });
    if (r.ok) FLAGS = await r.json();
  }catch(e){ /* swallow */ }
}

async function loadConfig(){
  const res = await fetch('/static/content/config.json', { cache: 'no-store' });
  if (!res.ok) throw new Error('Could not load config.json');
  CFG = await res.json();
  window.CFG = CFG; // handy for debugging
  window.FLAGS = FLAGS;

  // render using CFG
  renderIndustryChoices(CFG.industries || []);
  renderToneChoices(CFG.tones || []);
  renderPlatformChoices(CFG.platforms || []);
  showStep(step);
  updateSummary();
  // now that config is rendered, try to load any saved profile (so industries map correctly)
  try{ await loadSavedProfile(); }catch(e){/* ignore */}
}

let step = 1;
const answers = {
  industry: "", tone: "", platforms: ["instagram"],
  brand_keywords: [], niche_keywords: [], include_images: true,
  company: "",
  goals: [], details: {}
};

const prevBtn = document.getElementById("prev");
const nextBtn = document.getElementById("next");
const results = document.getElementById("results");
const stepsBar = document.getElementById("steps");
const btnSample = document.getElementById("btn-sample");
const btn30 = document.getElementById("btn-30");

// load optional flags then config
loadFlags().then(loadConfig).catch(err => { console.error(err); });

// attempt to load saved profile for this session and prefill fields
async function loadSavedProfile(){
  try{
  const res = await fetch('/api/profile', { credentials: 'include' });
    if (!res.ok) return;
    const p = await res.json();
    if (!p || !p.id) return;
    // prefill inputs
    if (p.company) {
      const c = document.getElementById('company');
      if (c && !c.value) c.value = p.company;
      answers.company = p.company;
    }
    if (p.brand_keywords && p.brand_keywords.length){
      // load saved keywords but we'll reconcile with industry suggested keywords when industry is set
      answers.brand_keywords = p.brand_keywords || [];
    }
    if (p.platforms && p.platforms.length) answers.platforms = p.platforms;
    if (p.industry) answers.industry = p.industry;
    if (p.tone) answers.tone = p.tone;
    if (p.goals && p.goals.length) answers.goals = p.goals;
    if (p.details) answers.details = p.details || {};
    updateSummary();
  }catch(e){/* ignore */}
}

document.addEventListener('DOMContentLoaded', () => {
  // load content metadata
  (async ()=>{
    try{
  const r = await fetch('/api/content', { credentials: 'include' });
      if (!r.ok) return;
      const j = await r.json();
      const el = document.getElementById('content-version');
      if (el) el.textContent = j.version || 'local';
      window.CONTENT_META = j;
    }catch(e){/* ignore */}
    // query server for current user
    try{
  const r2 = await fetch('/api/current_user', { credentials: 'include' });
      if (r2.ok){
        const u = await r2.json();
        if (u && u.id){ window.CURRENT_USER = u; }
      }
      renderAuthUi();
    }catch(e){/* ignore */}
  })();
  // normalize company on blur
  const c = document.getElementById('company');
  if (c){
    c.addEventListener('blur', () => { c.value = c.value.trim().replace(/\s+/g,' ').split(' ').map(w=>w[0]?w[0].toUpperCase()+w.slice(1):'').join(' '); answers.company = c.value; updateSummary(); });
  }

  // dev create-user form (if present)
  const devForm = document.getElementById('dev-create-form');
  if (devForm){
    devForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const email = document.getElementById('dev-email').value.trim();
      const pw = document.getElementById('dev-password').value || 'password';
      const isPaid = !!document.getElementById('dev-paid').checked;
      const btn = document.getElementById('dev-create-btn'); setButtonLoading(btn, true);
      try{
        const r = await fetch('/__dev__/create_user', { method: 'POST', credentials: 'include', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ email, password: pw, is_paid: isPaid }) });
        const j = await r.json().catch(()=>null);
        if (!r.ok){ alert((j && j.error) || 'Could not create dev user'); return; }
        window.CURRENT_USER = j;
        renderAuthUi();
        showToast('Dev user created and signed in');
      }catch(e){ alert('Dev create failed'); }
      finally{ setButtonLoading(btn, false); }
    });
  }
  // localize next-billing display on account page if present
  try{
    const nb = document.getElementById('next-billing');
    if (nb){
      const iso = nb.getAttribute('data-iso') || '';
      if (iso){
        const dt = new Date(iso);
        if (!isNaN(dt.getTime())){
          const human = dt.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
          const now = new Date();
          const diff = Math.max(0, Math.floor((dt - now) / (1000*60*60*24)));
          nb.textContent = human + (isFinite(diff) ? (' (in ' + diff + ' days)') : '');
        }
      }
    }
  }catch(e){/* ignore */}
});

function renderAuthUi(){
  const link = document.querySelector('header a[href="#"]');
  if (!link) return;
  // ensure we don't attach duplicate handlers
  link.replaceWith(link.cloneNode(true));
  const newLink = document.querySelector('header a[href="#"]');
  if (window.CURRENT_USER && window.CURRENT_USER.id){
    newLink.textContent = window.CURRENT_USER.email || 'Account';
    newLink.href = '/account';
    // left-click navigates to account; right-click still opens portal
    newLink.addEventListener('click', (e)=>{});
  } else {
    newLink.textContent = 'Sign in';
    newLink.href = '#';
    newLink.addEventListener('click', async (e)=>{ e.preventDefault(); openAuthModal('login'); });
  }
}

// Auth modal helpers
function openAuthModal(view){
  const modal = document.getElementById('auth-modal');
  if (!modal) return;
  modal.classList.remove('hidden');
  const container = modal.querySelector('[tabindex="-1"]');
  if (container && typeof container.focus === 'function') container.focus();
  document.getElementById('auth-title').textContent = view === 'signup' ? 'Create account' : (view === 'reset' ? 'Reset password' : 'Sign in');
  // hide all forms
  ['login-form','signup-form','reset-form','confirm-reset-form'].forEach(id => { const el = document.getElementById(id); if (el) el.classList.add('hidden'); });
  if (view === 'signup') document.getElementById('signup-form').classList.remove('hidden');
  else if (view === 'reset') document.getElementById('reset-form').classList.remove('hidden');
  else if (view === 'confirm-reset') document.getElementById('confirm-reset-form').classList.remove('hidden');
  else document.getElementById('login-form').classList.remove('hidden');
  trapFocus(modal);
}
function closeAuthModal(){ document.getElementById('auth-modal')?.classList.add('hidden'); }

document.addEventListener('DOMContentLoaded', () => {
  // modal switch buttons
  document.getElementById('show-signup')?.addEventListener('click', () => openAuthModal('signup'));
  document.getElementById('show-login')?.addEventListener('click', () => openAuthModal('login'));
  document.getElementById('show-reset')?.addEventListener('click', () => openAuthModal('reset'));
  document.getElementById('auth-close')?.addEventListener('click', closeAuthModal);
  document.getElementById('reset-back')?.addEventListener('click', () => openAuthModal('login'));
  document.getElementById('confirm-back')?.addEventListener('click', () => openAuthModal('login'));

  // login submit
  document.getElementById('login-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('auth-email').value.trim();
    const pw = document.getElementById('auth-password').value;
    const msgEl = document.getElementById('auth-message');
    try{
      setButtonLoading(e.submitter || e.target.querySelector('button[type=submit]'), true);
  const r = await fetch('/api/login', { method: 'POST', credentials: 'include', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ email, password: pw }) });
      const j = await r.json().catch(()=>null);
      if (!r.ok){ showAuthMessage((j && j.error) || 'Sign in failed'); setButtonLoading(null,false); return; }
      window.CURRENT_USER = j; renderAuthUi(); closeAuthModal(); showToast('Signed in');
    }catch(err){ showAuthMessage('Sign in failed'); }
    finally{ setButtonLoading(null,false); }
  });

  // signup submit
  document.getElementById('signup-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('signup-email').value.trim();
    const pw = document.getElementById('signup-password').value;
    try{
      const btn = e.submitter || e.target.querySelector('button[type=submit]'); setButtonLoading(btn, true);
  const r = await fetch('/api/signup', { method: 'POST', credentials: 'include', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ email, password: pw }) });
      const j = await r.json().catch(()=>null);
      if (!r.ok){ showAuthMessage((j && j.error) || 'Sign up failed'); return; }
      window.CURRENT_USER = j; renderAuthUi(); closeAuthModal(); showToast('Account created');
    }catch(err){ showAuthMessage('Sign up failed'); }
    finally{ setButtonLoading(null,false); }
  });

  // request reset
  document.getElementById('request-reset')?.addEventListener('click', async () => {
    const email = document.getElementById('reset-email').value.trim();
    if (!email) return alert('Email required');
    try{
      const btn = document.getElementById('request-reset'); setButtonLoading(btn, true);
  const r = await fetch('/api/request-password-reset', { method: 'POST', credentials: 'include', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ email }) });
      const j = await r.json().catch(()=>null);
      if (!r.ok){ showAuthMessage((j && j.error) || 'Request failed'); return; }
      // show token-based confirm form for dev/testing
      openAuthModal('confirm-reset');
      if (j && j.token) document.getElementById('confirm-token').value = j.token;
      showToast('Password reset token generated (dev)');
    }catch(e){ showAuthMessage('Request failed'); }
    finally{ setButtonLoading(null,false); }
  });

  // confirm reset
  document.getElementById('confirm-reset')?.addEventListener('click', async () => {
    const token = document.getElementById('confirm-token').value.trim();
    const pw = document.getElementById('confirm-password').value;
    if (!token || !pw) return alert('Token and password required');
    try{
      const btn = document.getElementById('confirm-reset'); setButtonLoading(btn, true);
  const r = await fetch('/api/confirm-password-reset', { method: 'POST', credentials: 'include', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ token, password: pw }) });
      const j = await r.json().catch(()=>null);
      if (!r.ok){ showAuthMessage((j && j.error) || 'Reset failed'); return; }
      showToast('Password reset. Please sign in.');
      openAuthModal('login');
    }catch(e){ showAuthMessage('Reset failed'); }
    finally{ setButtonLoading(null,false); }
  });
});

// UI helpers: show inline messages & toasts
function showAuthMessage(msg){ const el = document.getElementById('auth-message'); if (el){ el.textContent = msg; el.classList.remove('hidden'); } else alert(msg); }
function clearAuthMessage(){ const el = document.getElementById('auth-message'); if (el){ el.textContent=''; el.classList.add('hidden'); } }
function showPaywallMessage(msg){ const el = document.getElementById('paywall-message'); if (el){ el.textContent = msg; el.classList.remove('hidden'); } }
function clearPaywallMessage(){ const el = document.getElementById('paywall-message'); if (el){ el.textContent=''; el.classList.add('hidden'); } }
function showToast(msg){ const t = document.createElement('div'); t.className='fixed bottom-6 right-6 bg-slate-800 text-white px-4 py-2 rounded shadow'; t.textContent=msg; document.body.appendChild(t); setTimeout(()=>t.classList.add('opacity-0'), 2200); setTimeout(()=>t.remove(), 2800); }

function setButtonLoading(btn, loading){
  if (!btn) return; 
  if (loading){ btn.dataset.orig = btn.innerHTML; btn.disabled = true; btn.innerHTML = btn.dataset.loadingText || 'Loading…'; }
  else { if (btn.dataset.orig) btn.innerHTML = btn.dataset.orig; btn.disabled = false; }
}

// focus trap helper (basic)
function trapFocus(modal){
  const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  const first = focusable[0];
  const last = focusable[focusable.length-1];
  function keyHandler(e){
    if (e.key === 'Escape') { modal.classList.add('hidden'); document.removeEventListener('keydown', keyHandler); }
    if (e.key === 'Tab'){
      if (e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
    }
  }
  document.addEventListener('keydown', keyHandler);
}

// client-side company validation: returns error message or empty
function validateCompany(name){
  if (!name) return '';
  if (name.length > 100) return 'Company name is too long (max 100 chars).';
  // disallow angle brackets and control characters which are commonly problematic
  if (/[*<>\\\x00-\x1F]/.test(name)) return 'Company name contains invalid characters.';
  if (!/^[\w \-\'\.\&]+$/.test(name)) return 'Company name contains invalid characters.';
  return '';
}

function renderIndustryChoices(list){
  const wrap = document.getElementById("industries");
  wrap.innerHTML = "";
  list.forEach(opt => {
    const div = document.createElement("button");
    div.className = "choice"; div.setAttribute("data-key", opt.key);
    div.innerHTML = `<div class="emoji">${opt.icon}</div><div class="title">${opt.label}</div>`;
    div.addEventListener("click", () => {
      wrap.querySelectorAll(".choice").forEach(c=>c.classList.remove("selected"));
      div.classList.add("selected");
      // store both key and label for reliable lookups
      answers.industry = opt.label;
      answers.industry_key = opt.key;
      renderIndustryQuestions(opt.key);
      // set suggested keywords and note placeholder for this industry
      try{
        const noteInput = document.getElementById('note');
        const meta = (CFG && CFG.industries || []).find(i => i.key === opt.key) || {};
        // render suggested keywords as chips
        const sk = document.getElementById('suggested-keywords');
        if (sk){
          sk.innerHTML = '';
          const kws = meta.suggested_keywords || [];
          kws.forEach(k => {
            const btn = document.createElement('button');
            btn.className = 'choice text-sm'; btn.textContent = k;
            btn.addEventListener('click', () => {
              toggleKeyword(k);
              btn.classList.toggle('selected');
            });
            sk.appendChild(btn);
          });
        }
        if (noteInput){
          noteInput.placeholder = meta.note_placeholder || noteInput.placeholder;
        }
        // set answers.brand_keywords to the canonical suggested keywords for this industry
        // but don't overwrite any existing saved keywords
        if (!answers.brand_keywords || answers.brand_keywords.length === 0) {
          answers.brand_keywords = (meta.suggested_keywords || []).slice(0,4);
        }
        // mark selected state on the rendered chips
        try{ const sk2 = document.getElementById('suggested-keywords'); if (sk2){ Array.from(sk2.children).forEach(btn => { if (answers.brand_keywords.includes(btn.textContent)) btn.classList.add('selected'); }) } }catch(e){}
      }catch(e){/* ignore */}
  if (nextBtn && typeof nextBtn.focus === 'function') nextBtn.focus();
      updateSummary();
    });
    // if this industry matches the already-selected industry, mark it as selected
    if ((answers.industry_key && answers.industry_key === opt.key) || (!answers.industry_key && answers.industry === opt.label)){
      div.classList.add('selected');
      // ensure questions and placeholders render for the preselected industry
      try{ renderIndustryQuestions(opt.key); const kwInput = document.getElementById('keywords'); const meta = (CFG && CFG.industries || []).find(i => i.key === opt.key) || {}; if (kwInput && !kwInput.value && meta.suggested_keywords) kwInput.value = meta.suggested_keywords.slice(0,4).join(', '); }catch(e){}
    }
    wrap.appendChild(div);
  });
}

// keyword helpers
function toggleKeyword(k){
  answers.brand_keywords = answers.brand_keywords || [];
  const idx = answers.brand_keywords.indexOf(k);
  if (idx === -1) answers.brand_keywords.push(k);
  else answers.brand_keywords.splice(idx,1);
  updateSummary();
}

// handle extra keywords input (comma-separated or Enter)
document.addEventListener('DOMContentLoaded', () => {
  const extra = document.getElementById('extra-keywords');
  if (extra){
    extra.addEventListener('keydown', (e) => {
      if (e.key === 'Enter'){
        e.preventDefault();
        const parts = extra.value.split(',').map(s=>s.trim()).filter(Boolean);
        answers.brand_keywords = (answers.brand_keywords||[]).concat(parts);
        extra.value = '';
        updateSummary();
      }
    });
    extra.addEventListener('blur', () => {
      const parts = extra.value.split(',').map(s=>s.trim()).filter(Boolean);
      if (parts.length){ answers.brand_keywords = (answers.brand_keywords||[]).concat(parts); extra.value = ''; updateSummary(); }
    });
  }
});

function renderToneChoices(list){
  const wrap = document.getElementById("tones");
  wrap.innerHTML = "";
  list.forEach(opt => {
    const div = document.createElement("button");
    div.className = "choice"; div.setAttribute("data-key", opt.key);
    div.innerHTML = `<div class="title">${opt.label}</div>`;
    div.addEventListener("click", () => {
      wrap.querySelectorAll(".choice").forEach(c=>c.classList.remove("selected"));
      div.classList.add("selected");
      answers.tone = opt.key;
      updateSummary();
    });
    wrap.appendChild(div);
  });
}

function renderPlatformChoices(list){
  const wrap = document.getElementById("platforms");
  wrap.innerHTML = "";
  list.forEach(opt => {
    const div = document.createElement("button");
    div.className = "choice"; div.setAttribute("data-key", opt.key);
    div.innerHTML = `<div class="title">${opt.label}</div>`;
    div.addEventListener("click", () => {
      const k = opt.key;
      const idx = answers.platforms.indexOf(k);
      if (idx === -1) { answers.platforms.push(k); div.classList.add("selected"); }
      else { answers.platforms.splice(idx,1); div.classList.remove("selected"); }
      if (answers.platforms.length === 0) answers.platforms = ["instagram"];
      updateSummary();
    });
    if (answers.platforms.includes(opt.key)) div.classList.add("selected");
    wrap.appendChild(div);
  });
}

function renderIndustryQuestions(key){
  const wrap = document.getElementById("industry-questions");
  wrap.innerHTML = "";
  // preserve existing answers.goals and answers.details when switching industries
  const map = (CFG && CFG.questions) || {};
  (map[key] || []).forEach(q => {
    if (q.type === "chips"){
      const box = document.createElement("div");
      box.innerHTML = `<div class="text-sm font-medium mb-1">${q.label}</div>`;
      const grid = document.createElement("div");
      grid.className = "grid grid-cols-2 md:grid-cols-3 gap-2";
      q.options.forEach(opt => {
        const chip = document.createElement("button");
        chip.className = "choice"; chip.textContent = opt;
        // initialize selected state
        try{
          if (q.key === 'goals'){
            if ((answers.goals || []).indexOf(opt) !== -1) chip.classList.add('selected');
          } else {
            if ((answers.details && answers.details[q.key]) === opt) chip.classList.add('selected');
          }
        }catch(e){}
        chip.addEventListener("click", () => {
          // if this is the 'goals' question, allow multi-select
          if (q.key === 'goals'){
            answers.goals = answers.goals || [];
            const idx = answers.goals.indexOf(opt);
            if (idx === -1){ answers.goals.push(opt); chip.classList.add("selected"); }
            else { answers.goals.splice(idx,1); chip.classList.remove("selected"); }
          } else {
            // single-select behavior stored under answers.details[q.key]
            answers.details = answers.details || {};
            if (answers.details[q.key] === opt){
              // toggle off
              delete answers.details[q.key];
              chip.classList.remove('selected');
            } else {
              // deselect other chips in this grid
              Array.from(grid.children).forEach(c => c.classList.remove('selected'));
              answers.details[q.key] = opt;
              chip.classList.add('selected');
            }
          }
          updateSummary();
        });
        grid.appendChild(chip);
      });
      box.appendChild(grid);
      wrap.appendChild(box);
    }
    if (q.type === "text"){
      const box = document.createElement("div");
      box.innerHTML = `<label class="block text-sm font-medium mb-1">${q.label}</label>\n      <input class="input" placeholder="${q.placeholder||""}" />`;
      const input = box.querySelector("input");
      // prefill if previously saved
      try{ if (answers.details && answers.details[q.key]) input.value = answers.details[q.key]; }catch(e){}
      input.addEventListener("input", () => { answers.details = answers.details || {}; answers.details[q.key] = input.value.trim(); updateSummary(); });
      wrap.appendChild(box);
    }
  });
}

function showStep(n){
  // hide all panels (only if panels exist on the page)
  const panels = document.querySelectorAll(".step-panel");
  if (panels && panels.length){
    panels.forEach(s=>s.classList.add("hidden"));
    const active = document.querySelector(`.step-panel[data-step="${n}"]`);
    if (active) active.classList.remove("hidden");
  }
  if (prevBtn) prevBtn.disabled = n === 1;
  if (nextBtn) nextBtn.textContent = n >= 4 ? "Finish" : "Next";
  if (stepsBar){
    const dots = stepsBar.querySelectorAll(".step") || [];
    dots.forEach((d,i)=> d.classList.toggle("active", (i+1) <= n));
  }
}

if (prevBtn) prevBtn.addEventListener("click", ()=>{ step = Math.max(1, step-1); showStep(step); });
if (nextBtn) nextBtn.addEventListener("click", async ()=>{
  if (step === 4){
    // collect keywords from selected chips and extra input
    const extra = document.getElementById('extra-keywords');
    if (extra && extra.value.trim()){
      const parts = extra.value.split(',').map(s=>s.trim()).filter(Boolean);
      answers.brand_keywords = (answers.brand_keywords || []).concat(parts);
      extra.value = '';
    }
    // ensure niche_keywords mirrors brand_keywords for now
    answers.niche_keywords = answers.brand_keywords || [];
    answers.include_images = document.getElementById("include_images").checked;
    try{
      await saveProfile();
    }catch(err){
      console.error('saveProfile failed', err);
      const msg = (err && err.message) ? err.message : 'Save failed — check console for details.';
      // remove any existing error
      const existingError = document.getElementById('company-error');
      if (existingError) existingError.remove();
      const el = document.createElement('div'); el.id = 'company-error'; el.className = 'text-xs text-red-600 mt-1'; el.textContent = msg;
      const companyInput = document.getElementById('company');
      if (companyInput && companyInput.parentElement){
        companyInput.parentElement.appendChild(el);
      }else{
        // fallback: append to wizard area
        const wiz = document.getElementById('wiz');
        (wiz || document.body).appendChild(el);
      }
      return;
    }
  }
  step = Math.min(4, step+1);
  showStep(step);
});

async function saveProfile(){
  const version = (CFG && CFG.version) ? CFG.version : "local";
  // ensure the latest company value is captured
  const companyInput = document.getElementById('company');
  if (companyInput) answers.company = companyInput.value.trim();
  // validate company before saving
  const err = validateCompany(answers.company);
  clearFieldError('company');
  if (err){
    showFieldError('company', err);
    return; // don't save while invalid
  }

  const resp = await fetch("/api/profile?content_version=" + encodeURIComponent(version), {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(answers)
  });
  if (!resp.ok){
    let j = null;
    try{ j = await resp.json(); }catch(e){ j = null; }
    // server may return structured field errors in { errors: { field: msg } }
    if (j && j.errors){
      Object.keys(j.errors).forEach(f => showFieldError(f, j.errors[f]));
      const formMsg = j.error || 'Please correct the highlighted fields.';
      showFormError(formMsg);
      throw new Error(formMsg);
    }
    const msg = (j && j.error) ? j.error : `Save failed (HTTP ${resp.status})`;
    showFormError(msg);
    throw new Error(msg);
  }
  if (btn30) btn30.disabled = false;
  updateSummary();
  // show the setup-complete inline summary if present (fall back to modal), then redirect to /complete
  try{
    const inline = document.getElementById('setup-summary-inline');
    const modal = document.getElementById('setup-modal') || document.getElementById('modal');
    const ms = document.getElementById('modal-summary');
    if (ms && window.__setup_summary){
      ms.innerHTML = '';
      window.__setup_summary.forEach(([k,v]) => {
        const li = document.createElement('li');
        li.className = 'flex justify-between';
        li.innerHTML = `<span class="font-medium">${k}</span><span>${escapeHtml(v)}</span>`;
        ms.appendChild(li);
      });
    }
    const mv = document.getElementById('modal-content-version');
    if (mv) mv.textContent = (window.CONTENT_META && window.CONTENT_META.version) ? window.CONTENT_META.version : (CFG && CFG.version) || 'local';
  if (inline) inline.classList.remove('hidden');
  else if (modal) modal.classList.remove('hidden');
  }catch(e){/* ignore */}
}

// wire company input to answers
document.addEventListener('DOMContentLoaded', () => {
  const c = document.getElementById('company');
  if (c){
    c.addEventListener('input', (e) => {
      answers.company = e.target.value.trim();
      // show immediate inline validation feedback
      clearFieldError('company');
      const msg = validateCompany(answers.company);
      if (msg){
        showFieldError('company', msg);
        // also visually disable Next/Finish button
        if (nextBtn) nextBtn.disabled = true;
      } else {
        if (nextBtn) nextBtn.disabled = false;
      }
      updateSummary();
    });
  }
});

// helper functions for field and form errors
function showFieldError(field, message){
  const id = `error-${field}`;
  const el = document.getElementById(id);
  if (el){ el.textContent = message || ''; el.classList.remove('hidden'); }
  else {
    // fallback: create a small inline element after the field
    const f = document.getElementById(field);
    if (f && f.parentElement){
      const div = document.createElement('div'); div.id = id; div.className = 'text-xs text-red-600 mt-1'; div.textContent = message || '';
      f.parentElement.appendChild(div);
    }
  }
}
function clearFieldError(field){
  const id = `error-${field}`;
  const el = document.getElementById(id);
  if (el){ el.textContent = ''; el.classList.add('hidden'); }
}
function showFormError(message){
  const el = document.getElementById('error-form');
  if (el){ el.textContent = message || ''; el.classList.remove('hidden'); }
}
function clearFormError(){
  const el = document.getElementById('error-form');
  if (el){ el.textContent = ''; el.classList.add('hidden'); }
}

if (btnSample) btnSample.addEventListener("click", async ()=>{
  await maybeSaveDefaults();
  renderPosts(await generate(1));
});
if (btn30) btn30.addEventListener("click", async ()=>{
  await maybeSaveDefaults();
  renderPosts(await generate(30));
});

async function maybeSaveDefaults(){
  if (!answers.industry) answers.industry = "Business";
  if (!answers.tone) answers.tone = "friendly";
  if (!answers.platforms || answers.platforms.length === 0) answers.platforms = ["instagram"];
  await saveProfile();
}

async function generate(days){
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ ...answers, days })
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function renderPosts(data){
  const posts = data.posts || [];
  results.innerHTML = "";
  if (!posts.length){ results.innerHTML = `<div class="text-sm text-slate-600">No posts yet.</div>`; return; }
  const byDay = groupBy(posts, "day_index");
  for (const day of Object.keys(byDay).sort((a,b)=>+a-+b)){
    const items = byDay[day];
    const section = document.createElement("section");
    section.className = "post";
    section.innerHTML = `<div class="flex items-baseline justify-between mb-2">
      <h4 class="font-medium">Day ${day} • ${items[0].date}</h4>
      <span class="text-xs text-slate-500">${items.length} platform(s)</span>
    </div>`;
    items.forEach(p => section.appendChild(renderCard(p)));
    results.appendChild(section);
  }
}

function renderCard(post){
  const card = document.createElement("div");
  card.className = "border rounded-lg p-3 mt-2";
  // normalize reel object to the legacy view shape so older UI keeps working
  function normalizeReel(r){
    if (!r) return null;
    const out = {};
    out.hook = r.hook || r.hooks || (Array.isArray(r.ranked_hooks) ? r.ranked_hooks[0] : '');
    out.script_beats = r.script_beats || r.scriptBeats || r.script || [];
    // normalize shot_list items to {type, description}
    out.shot_list = [];
    const rawShots = r.shot_list || r.shots || [];
    rawShots.forEach(s => {
      if (!s) return;
      if (typeof s === 'string'){
        out.shot_list.push({ type: s, description: '' });
      } else if (s.type && s.description){
        out.shot_list.push({ type: s.type, description: s.description });
      } else if (s.shot_type){
        out.shot_list.push({ type: s.shot_type, description: s.notes || '' });
      } else if (s.type){
        out.shot_list.push({ type: s.type, description: s.notes || '' });
      } else {
        // fallback stringify
        out.shot_list.push({ type: JSON.stringify(s), description: '' });
      }
    });
    out.on_screen_text = r.on_screen_text || r.onScreenText || r.onScreen || [];
    // hashtags: support both array and {primary, optional}
    if (Array.isArray(r.hashtags)) out.hashtags = r.hashtags;
    else if (r.hashtags && (r.hashtags.primary || r.hashtags.optional)) out.hashtags = [(r.hashtags.primary||[]).join(' '), (r.hashtags.optional||[]).join(' ')].filter(Boolean).join(' ').split(' ').filter(Boolean);
    else out.hashtags = [];
    out.cta = r.cta || '';
    out.thumbnail_prompt = r.thumbnail_prompt || r.thumbnail || r.thumbnailPrompt || '';
    out.srt_prompt = r.srt_prompt || r.srt || r.srtText || '';
    out.ranked_hooks = r.ranked_hooks || [];
    return out;
  }

  const r = normalizeReel(post.reel);

  card.innerHTML = `
    <div class="text-sm font-medium mb-1">${capitalize(post.platform)} • ${post.pillar}</div>
    ${post.image_url ? `<img class="w-full h-40 object-cover rounded mb-2" src="${post.image_url}" alt="Suggested image" />` : ""}
    <div class="text-xs text-slate-500 mb-2"><strong>Image prompt:</strong> ${escapeHtml(post.image_prompt)}</div>
    <pre class="caption text-sm">${escapeHtml(post.caption)}</pre>
    ${r ? `
      <div class="mt-3 p-3 bg-slate-50 rounded">
        <div class="text-sm font-medium mb-1">Reel plan</div>
        <div class="text-sm mb-2"><strong>Hook:</strong> ${escapeHtml(r.hook)}</div>
        <div class="text-sm mb-2"><strong>Script beats:</strong>
          <ol class="list-decimal ml-5 text-sm text-slate-700">${(r.script_beats||[]).map(b => `<li>${escapeHtml(b)}</li>`).join('')}</ol>
        </div>
        <div class="text-sm mb-2"><strong>Shot list:</strong>
          <ul class="list-disc ml-5 text-sm text-slate-700">${(r.shot_list||[]).map(s => `<li>${escapeHtml((s.type||'') + (s.description ? ': ' + s.description : ''))}</li>`).join('')}</ul>
        </div>
        <div class="text-sm mb-2"><strong>On-screen text:</strong> ${escapeHtml((r.on_screen_text||[]).join(' • '))}</div>
        <div class="text-sm mb-2"><strong>Hashtags:</strong> ${escapeHtml((r.hashtags||[]).join(' '))}</div>
        <div class="text-sm mb-2"><strong>CTA:</strong> ${escapeHtml(r.cta || '')}</div>
        <div class="flex gap-2 mt-2">
          <button class="btn-ghost text-xs" data-copy-reel-script>Copy Reel Script</button>
          <button class="btn-ghost text-xs" data-copy-srt>Copy SRT Prompt</button>
          <button class="btn-ghost text-xs" data-copy-thumb>Copy Thumbnail Prompt</button>
        </div>
      </div>
    ` : ''}
    <div class="mt-3 flex items-center gap-2">
      <button class="btn-ghost text-xs" data-copy="${escapeAttr(post.caption)}">Copy</button>
      <button class="btn-ghost text-xs" data-like="1" data-day="${post.day_index}" data-platform="${post.platform}">👍</button>
      <button class="btn-ghost text-xs" data-like="-1" data-day="${post.day_index}" data-platform="${post.platform}">👎</button>
    </div>
  `;
  card.querySelector("[data-copy]")?.addEventListener("click", async (ev) => {
    const txt = ev.currentTarget.getAttribute("data-copy") || "";
    await navigator.clipboard.writeText(txt);
    ev.currentTarget.textContent = "Copied!";
    setTimeout(() => (ev.currentTarget.textContent = "Copy"), 1200);
  });
  // reel copy buttons
  if (post.reel){
    // use normalized reel if present
    const reelNode = (function(){
      // try to find the normalized block we rendered above
      const container = card.querySelector('.mt-3.p-3');
      return container ? (post.reel && (post.reel._normalized || null)) : null;
    })();
    // fallback to constructing values from post.reel
    const hook = (post.reel && (post.reel.hook || (post.reel.ranked_hooks && post.reel.ranked_hooks[0]) || ''));
    const scriptArr = (post.reel && (post.reel.script_beats || post.reel.scriptBeats || post.reel.script || []));
    const scriptText = `${hook}\n\n${(scriptArr||[]).join('\n')}`;
    const srtText = (post.reel && (post.reel.srt_prompt || post.reel.srt || ''));
    const thumbText = (post.reel && (post.reel.thumbnail_prompt || post.reel.thumbnail || ''));

    const btnScript = card.querySelector('[data-copy-reel-script]');
    const btnSrt = card.querySelector('[data-copy-srt]');
    const btnThumb = card.querySelector('[data-copy-thumb]');
    btnScript?.addEventListener('click', async (ev) => {
      try{ await navigator.clipboard.writeText(scriptText); ev.currentTarget.textContent = 'Copied!'; setTimeout(()=>ev.currentTarget.textContent='Copy Reel Script',1200);}catch(e){console.error(e)}
    });
    btnSrt?.addEventListener('click', async (ev) => {
      try{ await navigator.clipboard.writeText(srtText || ''); ev.currentTarget.textContent = 'Copied!'; setTimeout(()=>ev.currentTarget.textContent='Copy SRT Prompt',1200);}catch(e){console.error(e)}
    });
    btnThumb?.addEventListener('click', async (ev) => {
      try{ await navigator.clipboard.writeText(thumbText || ''); ev.currentTarget.textContent = 'Copied!'; setTimeout(()=>ev.currentTarget.textContent='Copy Thumbnail Prompt',1200);}catch(e){console.error(e)}
    });
  }
  card.querySelectorAll("[data-like]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const rating = +btn.getAttribute("data-like");
      const post_day = +btn.getAttribute("data-day");
      const platform = btn.getAttribute("data-platform");
      await fetch("/api/feedback", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ rating, post_day, platform })
      });
      if (btn){
        btn.textContent = rating > 0 ? "👍 Thanks" : "👎 Noted";
        try{ btn.disabled = true; }catch(e){}
      }
    });
  });
  return card;
}

function updateSummary(){
  // Keep a small copy of the computed rows in memory; modal will render them when opened
  window.__setup_summary = [
    ["Industry", answers.industry || "—"],
    ["Tone", answers.tone || "—"],
    ["Platforms", answers.platforms.join(", ") || "—"],
    ["Goals", (answers.goals||[]).join(", ") || "—"],
    ["Company", answers.company || "—"]
  ];
  // If there's an inline summary card, render per-section progress
  try{ renderInlineSummary(); }catch(e){/* ignore */}
}

function renderInlineSummary(){
  const container = document.getElementById('modal-summary');
  if (!container) return;
  container.innerHTML = '';
  const sections = [
    { key: 'Industry', step: 1, value: answers.industry },
    { key: 'Details', step: 2, value: Object.keys(answers.details || {}).length || (answers.goals && answers.goals.length) },
    { key: 'Tone & Platforms', step: 3, value: answers.tone && answers.platforms && answers.platforms.length ? true : false },
    { key: 'Keywords & Note', step: 4, value: (answers.brand_keywords && answers.brand_keywords.length) || (answers.details && answers.details.note) || answers.company }
  ];
  sections.forEach(s => {
    const li = document.createElement('li');
    li.className = 'flex items-center justify-between';
    const left = document.createElement('div');
    left.className = 'flex items-center gap-3';
    const status = document.createElement('span');
    const done = !!s.value && s.value !== 0 && s.value !== '—';
    // nicer emoji status
    status.textContent = done ? '✅' : '◻️';
    status.className = done ? 'text-green-600' : 'text-slate-400';
    const label = document.createElement('button');
    label.className = 'text-left text-sm text-slate-700 hover:underline';
    label.textContent = s.key;
    label.addEventListener('click', () => { step = s.step; showStep(step); const wiz = document.getElementById('wiz'); if (wiz) wiz.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
    left.appendChild(status);
    left.appendChild(label);
    const right = document.createElement('div');
    right.className = 'text-sm text-slate-500 text-right';
    // friendly summaries per section
    let summary = '';
    if (s.step === 1) summary = answers.industry || '—';
    else if (s.step === 2) summary = (answers.goals && answers.goals.length) ? answers.goals.join(', ') : '—';
    else if (s.step === 3) summary = (answers.tone ? answers.tone : '—') + (answers.platforms && answers.platforms.length ? ' • ' + answers.platforms.join(', ') : '');
    else if (s.step === 4) summary = (answers.brand_keywords && answers.brand_keywords.length) ? answers.brand_keywords.slice(0,3).join(', ') : (answers.company || '—');
    right.textContent = summary;
    li.appendChild(left);
    li.appendChild(right);
    container.appendChild(li);
  });
}

function groupBy(arr, key){
  return arr.reduce((acc, x) => { (acc[x[key]] ||= []).push(x); return acc; }, {});
}
function capitalize(s){ return s ? s[0].toUpperCase() + s.slice(1) : s; }
function escapeHtml(s){ return (s||"").replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function escapeAttr(s){ return (s||"").replace(/"/g, "&quot;"); }

// Summary wiring (inline or modal): attach handlers once DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const inline = document.getElementById('setup-summary-inline');
  const modal = document.getElementById('setup-modal') || document.getElementById('modal');
  const closeBtn = document.getElementById('modal-close');
  const xBtn = document.getElementById('modal-x');
  const gen1Btn = document.getElementById('modal-generate-1');
  const gen30Btn = document.getElementById('modal-generate-30');
  const gen7Btn = document.getElementById('modal-generate-7');
  const genReelsBtn = document.getElementById('modal-generate-reels');

  // Close handlers: hide inline or modal depending on what exists
  closeBtn?.addEventListener('click', () => { if (inline) inline.classList.add('hidden'); if (modal) modal.classList.add('hidden'); });
  xBtn?.addEventListener('click', () => { if (inline) inline.classList.add('hidden'); if (modal) modal.classList.add('hidden'); });

  gen1Btn?.addEventListener('click', async () => {
    if (inline) inline.classList.add('hidden');
    if (modal) modal.classList.add('hidden');
    try{
      await maybeSaveDefaults();
      const data = await generate(1);
      renderPosts(data);
    }catch(err){ console.error('generate(1) failed', err); }
  });
  genReelsBtn?.addEventListener('click', async () => {
    // generate a short reels-only sample (5 reels)
    if (inline) inline.classList.add('hidden');
    if (modal) modal.classList.add('hidden');
    try{
      clearFormError();
      await maybeSaveDefaults();
      // call generate endpoint requesting only short_video platform
      const res = await fetch('/api/generate', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ ...answers, days: 5, platforms: ['short_video'] }) });
      if (!res.ok){ const j = await res.json().catch(()=>null); throw new Error((j && j.error) || ('HTTP ' + res.status)); }
      const data = await res.json();
      renderPosts(data);
    }catch(err){ console.error('generate(reels) failed', err); }
  });
  gen7Btn?.addEventListener('click', async () => {
    // gate to paid users if the flag is set
    const gate = (window.FLAGS && window.FLAGS.gate7DayToPaid) ? true : false;
    const userPaid = window.CURRENT_USER && window.CURRENT_USER.is_paid;
    if (gate && !userPaid){
      // open paywall modal instead of inline error
      const modal = document.getElementById('paywall-modal');
      if (modal) modal.classList.remove('hidden');
      return;
    }
    // proceed
    if (inline) inline.classList.add('hidden');
    if (modal) modal.classList.add('hidden');
    try{
      clearFormError();
      await maybeSaveDefaults();
      const data = await generate(7);
      renderPosts(data);
    }catch(err){ console.error('generate(7) failed', err); }
  });

  gen30Btn?.addEventListener('click', async () => {
    if (inline) inline.classList.add('hidden');
    if (modal) modal.classList.add('hidden');
    try{
      await maybeSaveDefaults();
      const data = await generate(30);
      renderPosts(data);
    }catch(err){ console.error('generate(30) failed', err); }
  });
  // show 7-day button based on flags
  try{ if (window.FLAGS && window.FLAGS.show7Day){ gen7Btn?.classList.remove('hidden'); } }catch(e){}
  // paywall modal handlers
  const payModal = document.getElementById('paywall-modal');
  const payCancel = document.getElementById('paywall-cancel');
  const paySubscribe = document.getElementById('paywall-subscribe');
  payCancel?.addEventListener('click', () => { if (payModal) payModal.classList.add('hidden'); });
  paySubscribe?.addEventListener('click', async () => {
    // show card input area and initialize Stripe Elements if needed
    const wrap = document.getElementById('stripe-elements-wrap');
    if (wrap) wrap.classList.remove('hidden');
    // ensure publishable key is loaded and Stripe is initialized
    try{
      if (!window.STRIPE){
        const r = await fetch('/api/stripe-publishable-key');
        if (!r.ok) throw new Error('Could not fetch publishable key');
        const j = await r.json();
        if (!j.ok) throw new Error(j.error || 'No publishable key');
        const pk = j.publishableKey;
        const script = document.createElement('script');
        script.src = 'https://js.stripe.com/v3/';
        document.head.appendChild(script);
        await new Promise(res => { script.onload = res; script.onerror = () => res(); });
        window.STRIPE = Stripe(pk);
        const elements = window.STRIPE.elements();
        window.__card = elements.create('card');
        window.__card.mount('#card-element');
        window.__card.on('change', (ev) => {
          const ce = document.getElementById('card-errors');
          if (!ev.complete && ev.error){ ce.textContent = ev.error.message; ce.classList.remove('hidden'); }
          else { ce.textContent = ''; ce.classList.add('hidden'); }
        });
      }
      // create a PaymentMethod via Stripe.js using the card element
      setButtonLoading(paySubscribe, true);
      // choose price id from env/config if available
      const priceId = (window.CFG && window.CFG.stripe_price_id) ? window.CFG.stripe_price_id : null;
      const pmRes = await window.STRIPE.createPaymentMethod({ type: 'card', card: window.__card });
      if (pmRes.error){ const ce = document.getElementById('card-errors'); if (ce){ ce.textContent = pmRes.error.message; ce.classList.remove('hidden'); } setButtonLoading(paySubscribe,false); return; }
      const payment_method = pmRes.paymentMethod.id;
      // call server to create subscription
      const r2 = await fetch('/api/create-subscription', { method: 'POST', credentials: 'include', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ price_id: priceId, payment_method }) });
      const j2 = await r2.json().catch(()=>null);
      if (!r2.ok || !j2 || !j2.ok){ alert((j2 && j2.error) || 'Subscription creation failed'); setButtonLoading(paySubscribe,false); return; }
      // if server returned a client_secret, confirm payment on the client
      if (j2.client_secret){
        const ci = await window.STRIPE.confirmCardPayment(j2.client_secret, { payment_method: payment_method });
        if (ci.error){ alert(ci.error.message || 'Payment confirmation failed'); setButtonLoading(paySubscribe,false); return; }
      }
      // success: mark current user as paid in UI and close modal
      window.CURRENT_USER = window.CURRENT_USER || {};
      window.CURRENT_USER.is_paid = true;
      renderAuthUi();
      showToast('Subscription active');
      const modal = document.getElementById('paywall-modal'); if (modal) modal.classList.add('hidden');
    }catch(e){ console.error(e); alert('Subscription failed: ' + (e && e.message)); }
    finally{ setButtonLoading(paySubscribe,false); }
  });
  // Manage subscription: attach to header account link via context menu (right-click)
  const headerLink = document.querySelector('header a[href="#"]');
  headerLink?.addEventListener('contextmenu', async (e) => {
    e.preventDefault();
    // try to open portal
    try{
      const r = await fetch('/api/create-portal-session', { method: 'POST' });
      if (!r.ok){ const j = await r.json().catch(()=>null); alert((j && j.error) || 'Could not open billing portal'); return; }
      const j = await r.json(); if (j && j.url) window.location.href = j.url;
    }catch(err){ console.error(err); alert('Could not open billing portal'); }
  });
});
