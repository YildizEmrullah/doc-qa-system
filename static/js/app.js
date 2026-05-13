'use strict';

/* ── API ─────────────────────────────────────────────────────── */
const API = {
  BASE: '/api',
  async get(path) {
    const r = await fetch(this.BASE + path);
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Hata'); }
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(this.BASE + path, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Hata'); }
    return r.json();
  },
  async upload(path, fd) {
    const r = await fetch(this.BASE + path, { method:'POST', body:fd });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Yükleme hatası'); }
    return r.json();
  },
  async delete(path) {
    const r = await fetch(this.BASE + path, { method:'DELETE' });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Silme hatası'); }
    return r.json();
  },
};

/* ── Toast ───────────────────────────────────────────────────── */
const Toast = {
  show(msg, type='info', duration=3500) {
    const icons = { success:'✓', error:'✕', info:'ℹ', warning:'⚠' };
    const el = document.createElement('div');
    el.className = `toast-item ${type}`;
    el.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
    document.getElementById('toastContainer').appendChild(el);
    setTimeout(() => el.remove(), duration);
  },
  success(m) { this.show(m,'success'); },
  error(m)   { this.show(m,'error',5000); },
  info(m)    { this.show(m,'info'); },
  warning(m) { this.show(m,'warning',4000); },
};

/* ── Upload Progress ─────────────────────────────────────────── */
const UploadProgress = {
  steps: ['pStep1','pStep2','pStep3','pStep4'],
  timer: null,

  start(filename) {
    clearInterval(this.timer);
    document.getElementById('uploadZone').classList.add('d-none');
    document.getElementById('uploadProgress').classList.remove('d-none');
    document.getElementById('uploadError').classList.add('d-none');
    document.getElementById('progressFilename').textContent = filename.length > 28 ? filename.slice(0,25)+'…' : filename;
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressPct').textContent = '0%';
    this.steps.forEach(id => {
      const el = document.getElementById(id);
      el.className = 'step-row small text-muted';
      el.querySelector('i').className = 'bi bi-circle me-1';
    });
    const pcts = [15,40,75,90];
    let i = 0;
    const go = () => {
      if (i > 0) {
        const prev = document.getElementById(this.steps[i-1]);
        prev.className = 'step-row small done';
        prev.querySelector('i').className = 'bi bi-check-circle-fill me-1';
      }
      if (i < this.steps.length) {
        const cur = document.getElementById(this.steps[i]);
        cur.className = 'step-row small active';
        cur.querySelector('i').className = 'bi bi-arrow-right-circle-fill me-1';
        document.getElementById('progressBar').style.width = pcts[i]+'%';
        document.getElementById('progressPct').textContent = pcts[i]+'%';
        i++;
      }
    };
    go();
    this.timer = setInterval(go, 900);
  },

  complete() {
    clearInterval(this.timer);
    this.steps.forEach(id => {
      const el = document.getElementById(id);
      el.className = 'step-row small done';
      el.querySelector('i').className = 'bi bi-check-circle-fill me-1';
    });
    document.getElementById('progressBar').style.width = '100%';
    document.getElementById('progressPct').textContent = '100%';
    setTimeout(() => this.reset(), 1500);
  },

  error(msg) {
    clearInterval(this.timer);
    this.reset();
    const e = document.getElementById('uploadError');
    e.textContent = '⚠ ' + msg;
    e.classList.remove('d-none');
    setTimeout(() => e.classList.add('d-none'), 5000);
  },

  reset() {
    document.getElementById('uploadZone').classList.remove('d-none');
    document.getElementById('uploadProgress').classList.add('d-none');
    document.getElementById('fileInput').value = '';
  },
};

/* ── Ana Uygulama ────────────────────────────────────────────── */
class DocuAskApp {
  constructor() {
    this.documents   = [];
    this.activeDocId = null;
    this.isAsking    = false;

    this._bind();
    this._load();
  }

  _bind() {
    // Upload
    document.getElementById('uploadZone').addEventListener('click', () => document.getElementById('fileInput').click());
    document.getElementById('fileInput').addEventListener('change', e => { if(e.target.files[0]) this._upload(e.target.files[0]); });
    const zone = document.getElementById('uploadZone');
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('drag-over'); if(e.dataTransfer.files[0]) this._upload(e.dataTransfer.files[0]); });

    // Soru
    document.getElementById('sendBtn').addEventListener('click', () => this._ask());
    document.getElementById('questionInput').addEventListener('keydown', e => { if(e.key==='Enter' && !e.shiftKey) { e.preventDefault(); this._ask(); } });
    document.getElementById('questionInput').addEventListener('input', () => {
      const len = document.getElementById('questionInput').value.length;
      document.getElementById('charCount').textContent = len+' / 1000';
      this._resizeTextarea();
    });

    // Filtre temizle
    document.getElementById('clearDocFilter').addEventListener('click', () => this._setActive(null));

    // Sohbet temizle
    document.getElementById('clearChatBtn').addEventListener('click', () => this._clearChat());
  }

  async _load() {
    await Promise.all([this._loadDocs(), this._loadStats()]);
    this._checkHealth();
  }

  async _checkHealth() {
    try {
      const d = await API.get('/health');
      const badge = document.getElementById('statusBadge');
      if (d.groq_configured) {
        badge.className = 'badge bg-success';
        badge.textContent = 'Groq / Llama-3.3 Bağlı';
      } else if (d.openai_configured) {
        badge.className = 'badge bg-success';
        badge.textContent = 'OpenAI Bağlı';
      } else {
        badge.className = 'badge bg-warning text-dark';
        badge.textContent = 'Demo Modu';
      }
    } catch {
      document.getElementById('statusBadge').className = 'badge bg-danger';
      document.getElementById('statusBadge').textContent = 'Bağlantı Hatası';
    }
  }

  async _loadDocs() {
    try {
      const d = await API.get('/documents');
      this.documents = d.documents;
      this._renderDocs();
    } catch {}
  }

  async _loadStats() {
    try {
      const s = await API.get('/documents/stats');
      document.getElementById('scDocs').textContent   = s.total_documents;
      document.getElementById('scChunks').textContent = s.total_chunks;
      document.getElementById('scModel').textContent  = this._shortModel(s.embedding_model);
      document.getElementById('scLlm').textContent    = s.openai_configured ? s.llm_model : 'Demo';
    } catch {}
  }

  _shortModel(name='') {
    const p = name.split('/');
    return p[p.length-1].slice(0,18);
  }

  _renderDocs() {
    const list = document.getElementById('documentList');
    document.getElementById('docCountBadge').textContent = this.documents.length;

    if (!this.documents.length) {
      list.innerHTML = `<div id="docEmpty" class="text-center text-muted py-4 small"><i class="bi bi-inbox fs-3 d-block mb-1"></i>Henüz doküman yüklenmedi</div>`;
      return;
    }

    list.innerHTML = this.documents.map(doc => `
      <div class="doc-item ${doc.id===this.activeDocId?'active':''}" data-id="${doc.id}">
        <span class="badge ${doc.file_type==='pdf'?'bg-danger':'bg-primary'} bg-opacity-75">${doc.file_type.toUpperCase()}</span>
        <div class="overflow-hidden">
          <div class="doc-item-name" title="${doc.original_name}">${doc.original_name}</div>
          <div class="doc-item-meta">${doc.chunk_count} chunk · ${doc.page_count} sayfa</div>
        </div>
        <button class="doc-delete-btn" data-id="${doc.id}" title="Sil"><i class="bi bi-trash"></i></button>
      </div>
    `).join('');

    list.querySelectorAll('.doc-item').forEach(el => {
      el.addEventListener('click', e => {
        if (e.target.closest('.doc-delete-btn')) return;
        const id = el.dataset.id;
        const doc = this.documents.find(d => d.id===id);
        this._setActive(id===this.activeDocId ? null : id, doc?.original_name);
      });
    });

    list.querySelectorAll('.doc-delete-btn').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const doc = this.documents.find(d => d.id===id);
        this._deletedoc(id, doc?.original_name);
      });
    });
  }

  _setActive(id, name='') {
    this.activeDocId = id;
    this._renderDocs();
    const pill = document.getElementById('activeDocPill');
    const noFilter = document.getElementById('noFilterMsg');
    if (id) {
      pill.classList.replace('d-none','d-flex');
      noFilter.classList.add('d-none');
      document.getElementById('activeDocName').textContent = name;
      document.getElementById('questionInput').placeholder = `"${name}" hakkında soru yazın...`;
    } else {
      pill.classList.replace('d-flex','d-none');
      noFilter.classList.remove('d-none');
      document.getElementById('questionInput').placeholder = 'Doküman hakkında soru yazın...';
    }
  }

  async _deletedoc(id, name) {
    if (!confirm(`"${name}" silinsin mi?`)) return;
    try {
      await API.delete('/documents/'+id);
      Toast.success(`"${name}" silindi.`);
      if (this.activeDocId===id) this._setActive(null);
      await Promise.all([this._loadDocs(), this._loadStats()]);
    } catch(e) { Toast.error(e.message); }
  }

  async _upload(file) {
    const ext = '.'+file.name.split('.').pop().toLowerCase();
    if (!['.pdf','.txt'].includes(ext)) { Toast.error('Sadece PDF veya TXT yükleyin.'); return; }
    if (file.size > 50*1024*1024) { Toast.error('Dosya 50 MB sınırını aşıyor.'); return; }

    UploadProgress.start(file.name);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await API.upload('/upload', fd);
      UploadProgress.complete();
      Toast.success(`"${file.name}" yüklendi — ${r.chunk_count} chunk.`);
      await Promise.all([this._loadDocs(), this._loadStats()]);
    } catch(e) {
      UploadProgress.error(e.message);
      Toast.error('Yükleme: '+e.message);
    }
  }

  async _ask() {
    const q = document.getElementById('questionInput').value.trim();
    if (!q || q.length < 3) { Toast.warning('Lütfen en az 3 karakterlik bir soru yazın.'); return; }
    if (this.isAsking) return;
    this.isAsking = true;

    document.getElementById('welcomeScreen').style.display = 'none';
    this._addUserMsg(q);
    document.getElementById('questionInput').value = '';
    document.getElementById('charCount').textContent = '0 / 1000';
    this._resizeTextarea();
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('questionInput').disabled = true;

    const typing = this._addTyping();
    try {
      const r = await API.post('/ask', { question:q, document_id:this.activeDocId||undefined, top_k:5 });
      typing.remove();
      this._addAIMsg(r, q);
    } catch(e) {
      typing.remove();
      this._addErrorMsg(e.message);
      Toast.error(e.message);
    } finally {
      this.isAsking = false;
      document.getElementById('sendBtn').disabled = false;
      document.getElementById('questionInput').disabled = false;
      this._scroll();
      document.getElementById('questionInput').focus();
      document.getElementById('clearChatBtn').classList.remove('d-none');
    }
  }

  _addUserMsg(text) {
    const div = document.createElement('div');
    div.className = 'msg-user';
    div.innerHTML = `<div class="msg-user-bubble">${this._esc(text)}</div>`;
    document.getElementById('messages').appendChild(div);
    document.getElementById('clearChatBtn').classList.remove('d-none');
    this._scroll();
  }

  _addTyping() {
    const div = document.createElement('div');
    div.className = 'msg-ai';
    div.innerHTML = `
      <div class="msg-ai-header">
        <div class="ai-avatar"><i class="bi bi-robot"></i></div>
        <span class="msg-ai-label">DocuAsk</span>
      </div>
      <div class="typing-indicator">
        <div class="typing-dots">
          <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
        </div>
        <span class="text-muted small">Yanıtlanıyor...</span>
      </div>`;
    document.getElementById('messages').appendChild(div);
    this._scroll();
    return div;
  }

  _addAIMsg(result, question) {
    const time = new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'});
    const md   = typeof marked !== 'undefined' ? marked.parse(result.answer) : this._esc(result.answer);

    const div = document.createElement('div');
    div.className = 'msg-ai';
    div.innerHTML = `
      <div class="msg-ai-header">
        <div class="ai-avatar"><i class="bi bi-robot"></i></div>
        <span class="msg-ai-label">DocuAsk</span>
        <span class="msg-ai-time">${time} · ${result.processing_time_ms}ms</span>
      </div>
      <div class="msg-ai-bubble">${md}</div>
      <div class="msg-ai-actions">
        <button class="copy-btn"><i class="bi bi-clipboard me-1"></i>Kopyala</button>
      </div>`;

    if (result.sources?.length) {
      div.appendChild(this._buildSources(result.sources, question));
    }

    div.querySelector('.copy-btn').addEventListener('click', e => this._copy(result.answer, e.currentTarget));
    document.getElementById('messages').appendChild(div);
    this._scroll();
  }

  _buildSources(sources, question) {
    const wrap = document.createElement('div');
    wrap.className = 'mt-2';

    const cards = sources.map(s => {
      const score   = Math.round(s.similarity_score * 100);
      const preview = this._highlight(s.text.slice(0,280), question);
      return `
        <div class="source-card">
          <div class="d-flex gap-2 flex-wrap mb-1">
            <span class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25">📄 ${this._esc(s.filename)}</span>
            <span class="badge bg-secondary bg-opacity-10 text-secondary">Sayfa ${s.page_number}</span>
            <span class="badge bg-success bg-opacity-10 text-success">%${score} eşleşme</span>
          </div>
          <div class="source-text">${preview}${s.text.length>280?'…':''}</div>
        </div>`;
    }).join('');

    wrap.innerHTML = `
      <button class="sources-toggle-btn">
        <i class="bi bi-journal-text"></i> ${sources.length} Kaynak
        <i class="bi bi-chevron-down ms-1"></i>
      </button>
      <div class="sources-body">${cards}</div>`;

    wrap.querySelector('.sources-toggle-btn').addEventListener('click', e => {
      const btn  = e.currentTarget;
      const body = wrap.querySelector('.sources-body');
      body.classList.toggle('open');
      btn.querySelector('.bi-chevron-down,.bi-chevron-up').classList.toggle('bi-chevron-down');
      btn.querySelector('.bi-chevron-down,.bi-chevron-up').classList.toggle('bi-chevron-up');
    });

    return wrap;
  }

  _addErrorMsg(msg) {
    const div = document.createElement('div');
    div.className = 'msg-ai';
    div.innerHTML = `
      <div class="msg-ai-header">
        <div class="ai-avatar bg-danger-subtle"><i class="bi bi-exclamation-triangle text-danger"></i></div>
        <span class="msg-ai-label text-danger">Hata</span>
      </div>
      <div class="alert alert-danger py-2 mb-0">${this._esc(msg)}</div>`;
    document.getElementById('messages').appendChild(div);
  }

  _copy(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
      btn.classList.add('copied');
      btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Kopyalandı!';
      setTimeout(() => {
        btn.classList.remove('copied');
        btn.innerHTML = '<i class="bi bi-clipboard me-1"></i>Kopyala';
      }, 2000);
    }).catch(() => Toast.error('Kopyalama başarısız.'));
  }

  _clearChat() {
    document.getElementById('messages').innerHTML = '';
    document.getElementById('welcomeScreen').style.display = '';
    document.getElementById('clearChatBtn').classList.add('d-none');
    Toast.info('Sohbet temizlendi.');
  }

  _scroll() { setTimeout(() => { const c = document.getElementById('chatArea'); c.scrollTop = c.scrollHeight; }, 50); }

  _resizeTextarea() {
    const ta = document.getElementById('questionInput');
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120)+'px';
  }

  _esc(s='') {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
  }

  _highlight(text, query='') {
    let safe = this._esc(text);
    query.split(/\s+/).filter(t=>t.length>2).forEach(term => {
      safe = safe.replace(new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')})`, 'gi'), '<mark>$1</mark>');
    });
    return safe;
  }

  setQuestion(text) {
    document.getElementById('questionInput').value = text;
    document.getElementById('charCount').textContent = text.length+' / 1000';
    this._resizeTextarea();
    document.getElementById('questionInput').focus();
  }
}

/* ── Marked config ───────────────────────────────────────────── */
if (typeof marked !== 'undefined') {
  marked.setOptions({ breaks:true, gfm:true });
}

/* ── Başlat ──────────────────────────────────────────────────── */
let app;
document.addEventListener('DOMContentLoaded', () => { app = new DocuAskApp(); });
