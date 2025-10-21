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
    const res = await fetch('/api/profile');
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
      const k = document.getElementById('keywords');
      if (k && !k.value) k.value = (p.brand_keywords || []).join(', ');
      answers.brand_keywords = p.brand_keywords || [];
    }
    if (p.platforms && p.platforms.length) answers.platforms = p.platforms;
    if (p.industry) answers.industry = p.industry;
    if (p.tone) answers.tone = p.tone;
    updateSummary();
  }catch(e){/* ignore */}
}

document.addEventListener('DOMContentLoaded', () => {
  // load content metadata
  (async ()=>{
    try{
      const r = await fetch('/api/content');
      if (!r.ok) return;
      const j = await r.json();
      const el = document.getElementById('content-version');
      if (el) el.textContent = j.version || 'local';
      window.CONTENT_META = j;
    }catch(e){/* ignore */}
  })();
  // normalize company on blur
  const c = document.getElementById('company');
  if (c){
    c.addEventListener('blur', () => { c.value = c.value.trim().replace(/\s+/g,' ').split(' ').map(w=>w[0]?w[0].toUpperCase()+w.slice(1):'').join(' '); answers.company = c.value; updateSummary(); });
  }
});

// client-side company validation: returns error message or empty
function validateCompany(name){
  if (!name) return '';
  if (name.length > 100) return 'Company name is too long (max 100 chars).';
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
        const kwInput = document.getElementById('keywords');
        const noteInput = document.getElementById('note');
        const meta = (CFG && CFG.industries || []).find(i => i.key === opt.key) || {};
        if (kwInput && !kwInput.value){
          if (meta.suggested_keywords) kwInput.placeholder = meta.suggested_keywords.join(', ');
        }
        if (noteInput){
          noteInput.placeholder = meta.note_placeholder || noteInput.placeholder;
        }
        // if user hasn't typed keywords, prefill them as a convenience
        if (kwInput && !kwInput.value && meta.suggested_keywords){
          // do not auto-save into answers unless user types or proceeds
          // but for convenience we can pre-populate the visible value (optional)
          kwInput.value = meta.suggested_keywords.slice(0,4).join(', ');
        }
      }catch(e){/* ignore */}
      nextBtn.focus();
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
  answers.goals = [];
  answers.details = {};
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
        chip.addEventListener("click", () => {
          const idx = answers.goals.indexOf(opt);
          if (idx === -1){ answers.goals.push(opt); chip.classList.add("selected"); }
          else { answers.goals.splice(idx,1); chip.classList.remove("selected"); }
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
      input.addEventListener("input", () => { answers.details[q.key] = input.value.trim(); updateSummary(); });
      wrap.appendChild(box);
    }
  });
}

function showStep(n){
  document.querySelectorAll(".step-panel").forEach(s=>s.classList.add("hidden"));
  document.querySelector(`.step-panel[data-step="${n}"]`).classList.remove("hidden");
  prevBtn.disabled = n === 1;
  nextBtn.textContent = n >= 4 ? "Finish" : "Next";
  const dots = stepsBar.querySelectorAll(".step");
  dots.forEach((d,i)=> d.classList.toggle("active", (i+1) <= n));
}

if (prevBtn) prevBtn.addEventListener("click", ()=>{ step = Math.max(1, step-1); showStep(step); });
if (nextBtn) nextBtn.addEventListener("click", ()=>{
  if (step === 4){
    const kws = document.getElementById("keywords").value.trim();
    if (kws){
      const parts = kws.split(",").map(s=>s.trim()).filter(Boolean);
      answers.brand_keywords = parts;
      answers.niche_keywords = parts;
    }
    answers.include_images = document.getElementById("include_images").checked;
    saveProfile();
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
  const existingError = document.getElementById('company-error');
  if (existingError) existingError.remove();
  if (err){
    const el = document.createElement('div'); el.id = 'company-error'; el.className = 'text-xs text-red-600 mt-1'; el.textContent = err;
    companyInput?.parentElement?.appendChild(el);
    return; // don't save while invalid
  }

  const resp = await fetch("/api/profile?content_version=" + encodeURIComponent(version), {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(answers)
  });
  if (!resp.ok){
    let j = null;
    try{ j = await resp.json(); }catch(e){}
    const msg = (j && j.error) ? j.error : `Save failed (HTTP ${resp.status})`;
    const existingError = document.getElementById('company-error');
    if (existingError) existingError.remove();
    const el = document.createElement('div'); el.id = 'company-error'; el.className = 'text-xs text-red-600 mt-1'; el.textContent = msg;
    const companyInput = document.getElementById('company');
    companyInput?.parentElement?.appendChild(el);
    throw new Error(msg);
  }
  btn30.disabled = false;
  updateSummary();
  // show the setup-complete modal if present
  try{
    const modal = document.getElementById('setup-modal') || document.getElementById('modal');
    if (modal){
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
      modal.classList.remove('hidden');
    }
  }catch(e){/* ignore */}
}

// wire company input to answers
document.addEventListener('DOMContentLoaded', () => {
  const c = document.getElementById('company');
  if (c){
    c.addEventListener('input', (e) => { answers.company = e.target.value.trim(); updateSummary(); });
  }
});

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
  card.innerHTML = `
    <div class="text-sm font-medium mb-1">${capitalize(post.platform)} • ${post.pillar}</div>
    ${post.image_url ? `<img class="w-full h-40 object-cover rounded mb-2" src="${post.image_url}" alt="Suggested image" />` : ""}
    <div class="text-xs text-slate-500 mb-2"><strong>Image prompt:</strong> ${escapeHtml(post.image_prompt)}</div>
    <pre class="caption text-sm">${escapeHtml(post.caption)}</pre>
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
      btn.textContent = rating > 0 ? "👍 Thanks" : "👎 Noted";
      btn.disabled = true;
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
}

function groupBy(arr, key){
  return arr.reduce((acc, x) => { (acc[x[key]] ||= []).push(x); return acc; }, {});
}
function capitalize(s){ return s ? s[0].toUpperCase() + s.slice(1) : s; }
function escapeHtml(s){ return (s||"").replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function escapeAttr(s){ return (s||"").replace(/"/g, "&quot;"); }

// Modal wiring: attach handlers once DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('setup-modal');
  if (!modal) return;
  const closeBtn = document.getElementById('modal-close');
  const xBtn = document.getElementById('modal-x');
  const gen1Btn = document.getElementById('modal-generate-1');
  const gen30Btn = document.getElementById('modal-generate-30');

  closeBtn?.addEventListener('click', () => modal.classList.add('hidden'));
  xBtn?.addEventListener('click', () => modal.classList.add('hidden'));

  gen1Btn?.addEventListener('click', async () => {
    modal.classList.add('hidden');
    try{
      await maybeSaveDefaults();
      const data = await generate(1);
      renderPosts(data);
    }catch(err){ console.error('generate(1) failed', err); }
  });

  gen30Btn?.addEventListener('click', async () => {
    modal.classList.add('hidden');
    try{
      await maybeSaveDefaults();
      const data = await generate(30);
      renderPosts(data);
    }catch(err){ console.error('generate(30) failed', err); }
  });
});
