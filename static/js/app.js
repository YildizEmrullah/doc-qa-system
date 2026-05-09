/**
 * DocuAsk — Uygulama JavaScript
 * Vanilla JS ile soru-cevap arayüzü, doküman yönetimi ve API entegrasyonu.
 */

'use strict';

/* ══════════════════════════════════════════════════════════════
   API İstek Yardımcısı
   ══════════════════════════════════════════════════════════════ */
const API = {
  BASE: '/api',

  async get(path) {
    const res = await fetch(this.BASE + path);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Sunucu hatası');
    }
    return res.json();
  },

  async post(path, body) {
    const res = await fetch(this.BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Sunucu hatası');
    }
    return res.json();
  },

  async upload(path, formData) {
    const res = await fetch(this.BASE + path, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Yükleme hatası');
    }
    return res.json();
  },

  async delete(path) {
    const res = await fetch(this.BASE + path, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Silme hatası');
    }
    return res.json();
  },
};

/* ══════════════════════════════════════════════════════════════
   Toast Bildirimleri
   ══════════════════════════════════════════════════════════════ */
const Toast = {
  container: null,

  init() { this.container = document.getElementById('toastContainer'); },

  show(message, type = 'info', duration = 3500) {
    const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || 'ℹ'}</span>
      <span class="toast-msg">${message}</span>
    `;
    this.container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('hiding');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  success(msg) { this.show(msg, 'success'); },
  error(msg)   { this.show(msg, 'error', 5000); },
  info(msg)    { this.show(msg, 'info'); },
  warning(msg) { this.show(msg, 'warning', 4500); },
};

/* ══════════════════════════════════════════════════════════════
   Yükleme İlerleme Göstergesi
   ══════════════════════════════════════════════════════════════ */
const UploadProgress = {
  steps: ['pStep1', 'pStep2', 'pStep3', 'pStep4'],
  currentStep: 0,
  timer: null,

  start(filename) {
    this.currentStep = 0;
    clearInterval(this.timer);

    const zone     = document.getElementById('uploadZone');
    const progress = document.getElementById('uploadProgress');
    const error    = document.getElementById('uploadError');

    zone.style.display     = 'none';
    progress.style.display = 'block';
    error.style.display    = 'none';

    document.getElementById('progressFilename').textContent =
      filename.length > 28 ? filename.slice(0, 25) + '…' : filename;
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressPct').textContent  = '0%';

    // Adımları sıfırla
    this.steps.forEach(id => {
      const row = document.getElementById(id);
      row.classList.remove('active', 'done');
      row.querySelector('.step-dot').className = 'step-dot pending';
    });

    // Adımları simüle et (gerçek işlem arka planda devam eder)
    const durations = [15, 25, 50, 85];
    let i = 0;

    const advance = () => {
      if (i >= this.steps.length) return;
      this._activateStep(i);
      const pct = durations[i];
      document.getElementById('progressBar').style.width = pct + '%';
      document.getElementById('progressPct').textContent  = pct + '%';
      i++;
    };

    advance();
    this.timer = setInterval(() => advance(), 800);
  },

  complete() {
    clearInterval(this.timer);

    // Tüm adımları tamamlandı olarak işaretle
    this.steps.forEach(id => {
      const row = document.getElementById(id);
      row.classList.remove('active');
      row.classList.add('done');
      row.querySelector('.step-dot').className = 'step-dot done';
    });

    document.getElementById('progressBar').style.width = '100%';
    document.getElementById('progressPct').textContent  = '100%';

    setTimeout(() => this.reset(), 1800);
  },

  error(message) {
    clearInterval(this.timer);
    this.reset();

    const errEl = document.getElementById('uploadError');
    errEl.textContent    = '⚠ ' + message;
    errEl.style.display  = 'block';

    setTimeout(() => { errEl.style.display = 'none'; }, 5000);
  },

  reset() {
    document.getElementById('uploadZone').style.display     = '';
    document.getElementById('uploadProgress').style.display = 'none';
    document.getElementById('fileInput').value              = '';
  },

  _activateStep(index) {
    if (index > 0) {
      const prev = document.getElementById(this.steps[index - 1]);
      prev.classList.remove('active');
      prev.classList.add('done');
      prev.querySelector('.step-dot').className = 'step-dot done';
    }
    const curr = document.getElementById(this.steps[index]);
    curr.classList.add('active');
    curr.querySelector('.step-dot').className = 'step-dot active';
  },
};

/* ══════════════════════════════════════════════════════════════
   Ana Uygulama Sınıfı
   ══════════════════════════════════════════════════════════════ */
class DocuAskApp {
  constructor() {
    this.documents       = [];
    this.activeDocId     = null;   // null = tüm dokümanlarda ara
    this.questionHistory = [];
    this.isAsking        = false;

    this._initComponents();
    this._bindEvents();
    this._loadInitialData();
  }

  /* ─── Başlatma ──────────────────────────────────────────────── */

  _initComponents() {
    Toast.init();

    this.els = {
      fileInput:       document.getElementById('fileInput'),
      uploadZone:      document.getElementById('uploadZone'),
      documentList:    document.getElementById('documentList'),
      docEmpty:        document.getElementById('docEmpty'),
      docCountBadge:   document.getElementById('docCountBadge'),
      messages:        document.getElementById('messages'),
      welcomeScreen:   document.getElementById('welcomeScreen'),
      questionInput:   document.getElementById('questionInput'),
      sendBtn:         document.getElementById('sendBtn'),
      charCount:       document.getElementById('charCount'),
      chatArea:        document.getElementById('chatArea'),
      activeDocPill:   document.getElementById('activeDocPill'),
      activeDocName:   document.getElementById('activeDocName'),
      clearDocFilter:  document.getElementById('clearDocFilter'),
      clearChatBtn:    document.getElementById('clearChatBtn'),
      statusDot:       document.getElementById('statusDot'),
      statusText:      document.getElementById('statusText'),
      sidebarToggle:   document.getElementById('sidebarToggle'),
      sidebar:         document.getElementById('sidebar'),
      // İstatistikler
      scDocs:    document.getElementById('scDocs'),
      scChunks:  document.getElementById('scChunks'),
      scModel:   document.getElementById('scModel'),
      scLlm:     document.getElementById('scLlm'),
      statChunks: document.getElementById('statChunks'),
      statModel:  document.getElementById('statModel'),
    };
  }

  _bindEvents() {
    // Sidebar toggle
    this.els.sidebarToggle.addEventListener('click', () => this._toggleSidebar());

    // Dosya yükleme — tıkla
    this.els.uploadZone.addEventListener('click', () => this.els.fileInput.click());
    this.els.fileInput.addEventListener('change', e => {
      if (e.target.files[0]) this._handleFileUpload(e.target.files[0]);
    });

    // Drag & Drop
    this.els.uploadZone.addEventListener('dragover',  e => { e.preventDefault(); this.els.uploadZone.classList.add('drag-over'); });
    this.els.uploadZone.addEventListener('dragleave', () => this.els.uploadZone.classList.remove('drag-over'));
    this.els.uploadZone.addEventListener('drop',      e => {
      e.preventDefault();
      this.els.uploadZone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file) this._handleFileUpload(file);
    });

    // Soru gönderme
    this.els.sendBtn.addEventListener('click',    () => this._submitQuestion());
    this.els.questionInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._submitQuestion(); }
    });

    // Karakter sayacı & otomatik yükseklik
    this.els.questionInput.addEventListener('input', () => {
      const len = this.els.questionInput.value.length;
      this.els.charCount.textContent = `${len} / 1000`;
      this._autoResizeTextarea();
    });

    // Aktif doküman filtresini temizle
    this.els.clearDocFilter.addEventListener('click', () => this._setActiveDocument(null));

    // Sohbeti temizle
    this.els.clearChatBtn.addEventListener('click', () => this._clearChat());
  }

  async _loadInitialData() {
    await Promise.all([this._loadDocuments(), this._loadStats()]);
    this._checkHealth();
  }

  /* ─── Sağlık Kontrolü ───────────────────────────────────────── */

  async _checkHealth() {
    try {
      const data = await API.get('/health');
      if (data.groq_configured) {
        this.els.statusDot.className    = 'status-dot online';
        this.els.statusText.textContent = 'Groq / Llama-3.3 Bağlı';
      } else if (data.openai_configured) {
        this.els.statusDot.className    = 'status-dot online';
        this.els.statusText.textContent = 'OpenAI Bağlı';
      } else {
        this.els.statusDot.className    = 'status-dot warning';
        this.els.statusText.textContent = 'Demo Modu (API Key Yok)';
        Toast.warning('LLM API anahtarı bulunamadı — Demo modunda çalışılıyor.');
      }
    } catch {
      this.els.statusDot.className  = 'status-dot error';
      this.els.statusText.textContent = 'Bağlantı Hatası';
    }
  }

  /* ─── Doküman Yönetimi ──────────────────────────────────────── */

  async _loadDocuments() {
    try {
      const data = await API.get('/documents');
      this.documents = data.documents;
      this._renderDocumentList();
    } catch {
      // Sessizce geç; health check hatayı gösterir
    }
  }

  async _loadStats() {
    try {
      const s = await API.get('/documents/stats');
      this._animateCount(this.els.scDocs,   s.total_documents);
      this._animateCount(this.els.scChunks, s.total_chunks);
      this.els.scModel.textContent    = this._shortModel(s.embedding_model);
      this.els.scLlm.textContent      = s.openai_configured ? s.llm_model : 'Demo';
      this.els.statChunks.textContent = s.total_chunks;
      this.els.statModel.textContent  = this._shortModel(s.embedding_model);
    } catch { /* ignore */ }
  }

  _animateCount(el, target, duration = 600) {
    const start = parseInt(el.textContent) || 0;
    if (start === target) return;
    const step  = (target - start) / (duration / 16);
    let   cur   = start;
    const tick  = () => {
      cur += step;
      if ((step > 0 && cur >= target) || (step < 0 && cur <= target)) {
        el.textContent = target;
      } else {
        el.textContent = Math.round(cur);
        requestAnimationFrame(tick);
      }
    };
    requestAnimationFrame(tick);
  }

  _shortModel(name = '') {
    if (name.length <= 14) return name;
    const parts = name.split('/');
    return parts[parts.length - 1];
  }

  _renderDocumentList() {
    const list  = this.els.documentList;
    const count = this.documents.length;

    this.els.docCountBadge.textContent = count;

    if (count === 0) {
      list.innerHTML = '';
      list.appendChild(this.els.docEmpty);
      return;
    }

    list.innerHTML = '';
    this.documents.forEach(doc => {
      const ext   = doc.file_type || 'txt';
      const isAct = doc.id === this.activeDocId;
      const item  = document.createElement('div');
      item.className = `doc-item${isAct ? ' active' : ''}`;
      item.dataset.id = doc.id;

      item.innerHTML = `
        <div class="doc-item-icon ${ext}">${ext.toUpperCase()}</div>
        <div class="doc-item-info">
          <div class="doc-item-name" title="${doc.original_name}">${doc.original_name}</div>
          <div class="doc-item-meta">${doc.chunk_count} chunk · ${doc.page_count} sayfa</div>
        </div>
        <button class="doc-item-delete" title="Dokümanı sil" data-id="${doc.id}">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
            <path d="M10 11v6"/><path d="M14 11v6"/>
          </svg>
        </button>
      `;

      // Dokümana tıkla → filtre seç
      item.addEventListener('click', e => {
        if (e.target.closest('.doc-item-delete')) return;
        this._setActiveDocument(isAct ? null : doc.id, doc.original_name);
      });

      // Sil düğmesi
      item.querySelector('.doc-item-delete').addEventListener('click', e => {
        e.stopPropagation();
        this._deleteDocument(doc.id, doc.original_name);
      });

      list.appendChild(item);
    });
  }

  _setActiveDocument(docId, docName = 'tüm dokümanlar') {
    this.activeDocId = docId;
    this._renderDocumentList();

    if (docId) {
      this.els.activeDocPill.style.display = 'flex';
      this.els.activeDocName.textContent   = docName;
      this.els.questionInput.placeholder   = `"${docName}" hakkında soru sorun...`;
    } else {
      this.els.activeDocPill.style.display = 'none';
      this.els.questionInput.placeholder   = 'Doküman hakkında bir soru yazın...';
    }
  }

  async _deleteDocument(docId, docName) {
    if (!confirm(`"${docName}" dokümanını silmek istediğinize emin misiniz?`)) return;
    try {
      await API.delete(`/documents/${docId}`);
      Toast.success(`"${docName}" silindi.`);

      if (this.activeDocId === docId) this._setActiveDocument(null);

      await Promise.all([this._loadDocuments(), this._loadStats()]);
    } catch (err) {
      Toast.error('Silme hatası: ' + err.message);
    }
  }

  /* ─── Dosya Yükleme ─────────────────────────────────────────── */

  async _handleFileUpload(file) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!['.pdf', '.txt'].includes(ext)) {
      UploadProgress.error(`Desteklenmeyen format: "${ext}". Lütfen PDF veya TXT yükleyin.`);
      Toast.error('Desteklenmeyen dosya türü.');
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      UploadProgress.error('Dosya 50 MB sınırını aşıyor.');
      Toast.error('Dosya çok büyük (maks. 50 MB).');
      return;
    }

    UploadProgress.start(file.name);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const result = await API.upload('/upload', formData);
      UploadProgress.complete();
      Toast.success(`"${file.name}" yüklendi — ${result.chunk_count} chunk oluşturuldu.`);
      await Promise.all([this._loadDocuments(), this._loadStats()]);
    } catch (err) {
      UploadProgress.error(err.message);
      Toast.error('Yükleme hatası: ' + err.message);
    }
  }

  /* ─── Soru-Cevap ────────────────────────────────────────────── */

  async _submitQuestion() {
    const question = this.els.questionInput.value.trim();

    if (!question) {
      Toast.warning('Lütfen bir soru yazın.');
      this.els.questionInput.focus();
      return;
    }

    if (question.length < 3) {
      Toast.warning('Soru en az 3 karakter olmalıdır.');
      return;
    }

    if (this.isAsking) return;
    this.isAsking = true;

    // Hoşgeldin ekranını gizle
    this.els.welcomeScreen.style.display = 'none';

    // Kullanıcı balonunu ekle
    this._appendUserMessage(question);

    // Input'u temizle ve devre dışı bırak
    this.els.questionInput.value  = '';
    this.els.charCount.textContent = '0 / 1000';
    this._autoResizeTextarea();
    this._setSendState(false);

    // Yazıyor göstergesi
    const typingEl = this._appendTypingIndicator();

    try {
      const result = await API.post('/ask', {
        question,
        document_id: this.activeDocId || undefined,
        top_k: 5,
      });

      typingEl.remove();
      this._appendAIMessage(result, question);

      // Geçmişe ekle
      this.questionHistory.push({ question, answer: result.answer, ts: new Date() });
    } catch (err) {
      typingEl.remove();
      this._appendErrorMessage(err.message);
      Toast.error(err.message);
    } finally {
      this.isAsking = false;
      this._setSendState(true);
      this._scrollToBottom();
      this.els.questionInput.focus();
    }
  }

  /* ─── Mesaj Render Fonksiyonları ────────────────────────────── */

  _appendUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'msg-user';
    div.innerHTML = `<div class="msg-user-bubble">${this._escHtml(text)}</div>`;
    this.els.messages.appendChild(div);
    this.els.clearChatBtn.style.display = 'flex';
    this._scrollToBottom();
  }

  _appendTypingIndicator() {
    const wrap = document.createElement('div');
    wrap.className = 'msg-ai';
    wrap.innerHTML = `
      <div class="msg-ai-header">
        <div class="ai-avatar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <span class="msg-ai-label">DocuAsk</span>
      </div>
      <div class="typing-indicator">
        <div class="typing-dots">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
        <span class="typing-text">Yanıtlanıyor...</span>
      </div>
    `;
    this.els.messages.appendChild(wrap);
    this._scrollToBottom();
    return wrap;
  }

  _appendAIMessage(result, question) {
    const isDemo = result.answer.startsWith('⚠️');
    const time   = new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });

    const wrap = document.createElement('div');
    wrap.className = 'msg-ai';

    const demoBadge = isDemo
      ? `<div class="demo-badge">⚠ Demo Modu — LLM API anahtarı gerekli</div>`
      : '';

    // Markdown rendering
    const mdHtml = (typeof marked !== 'undefined')
      ? marked.parse(result.answer)
      : this._escHtml(result.answer);

    wrap.innerHTML = `
      <div class="msg-ai-header">
        <div class="ai-avatar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <span class="msg-ai-label">DocuAsk</span>
        <span class="msg-ai-time">${time} &nbsp;·&nbsp; ${result.processing_time_ms}ms</span>
      </div>
      ${demoBadge}
      <div class="msg-ai-bubble">${mdHtml}</div>
      <div class="msg-ai-actions">
        <button class="copy-btn" title="Cevabı kopyala">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          Kopyala
        </button>
      </div>
    `;

    // Kaynaklar (varsa)
    if (result.sources?.length) {
      const sourcesEl = this._buildSourcesEl(result.sources, question);
      wrap.appendChild(sourcesEl);
    }

    // Kopyala butonu
    wrap.querySelector('.copy-btn').addEventListener('click', (e) => {
      this._copyToClipboard(result.answer, e.currentTarget);
    });

    this.els.messages.appendChild(wrap);
    this.els.clearChatBtn.style.display = 'flex';
    this._scrollToBottom();
  }

  _buildSourcesEl(sources, question) {
    const section = document.createElement('div');
    section.className = 'sources-section';

    const cards = sources.map(src => {
      const score   = Math.round(src.similarity_score * 100);
      const preview = this._highlightTerms(src.text.slice(0, 280), question);
      return `
        <div class="source-card">
          <div class="source-card-header">
            <span class="source-badge file">📄 ${this._escHtml(src.filename)}</span>
            <span class="source-badge page">Sayfa ${src.page_number}</span>
            <span class="source-badge score">%${score} eşleşme</span>
          </div>
          <div class="source-text">${preview}${src.text.length > 280 ? '…' : ''}</div>
        </div>`;
    }).join('');

    section.innerHTML = `
      <button class="sources-toggle-btn">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        ${sources.length} Kaynak
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>
      <div class="sources-body">${cards}</div>
    `;

    section.querySelector('.sources-toggle-btn').addEventListener('click', (e) => {
      const btn  = e.currentTarget;
      const body = section.querySelector('.sources-body');
      btn.classList.toggle('open');
      body.classList.toggle('open');
    });

    return section;
  }

  _appendErrorMessage(message) {
    const div = document.createElement('div');
    div.className = 'msg-ai';
    div.innerHTML = `
      <div class="msg-ai-header">
        <div class="ai-avatar" style="background:#fee2e2;color:#ef4444;">✕</div>
        <span class="msg-ai-label" style="color:#ef4444;">Hata</span>
      </div>
      <div class="msg-ai-bubble" style="border-left:3px solid #ef4444;color:#991b1b;">
        ${this._escHtml(message)}
      </div>
    `;
    this.els.messages.appendChild(div);
  }

  /* ─── Yardımcı Metodlar ─────────────────────────────────────── */

  _setSendState(enabled) {
    this.els.sendBtn.disabled         = !enabled;
    this.els.questionInput.disabled   = !enabled;
  }

  _scrollToBottom() {
    setTimeout(() => {
      this.els.chatArea.scrollTop = this.els.chatArea.scrollHeight;
    }, 50);
  }

  _autoResizeTextarea() {
    const ta = this.els.questionInput;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
  }

  _toggleSidebar() {
    this.els.sidebar.classList.toggle('collapsed');
  }

  _escHtml(str = '') {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/\n/g, '<br>');
  }

  _highlightTerms(text, query = '') {
    let safe = this._escHtml(text);
    const terms = query.split(/\s+/).filter(t => t.length > 2);
    terms.forEach(term => {
      const re = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      safe = safe.replace(re, '<mark>$1</mark>');
    });
    return safe;
  }

  _copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
      btn.classList.add('copied');
      btn.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        Kopyalandı!`;
      setTimeout(() => {
        btn.classList.remove('copied');
        btn.innerHTML = `
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          Kopyala`;
      }, 2000);
    }).catch(() => Toast.error('Kopyalama başarısız.'));
  }

  _clearChat() {
    this.els.messages.innerHTML = '';
    this.questionHistory = [];
    this.els.welcomeScreen.style.display = '';
    this.els.clearChatBtn.style.display  = 'none';
    Toast.info('Sohbet temizlendi.');
  }

  /** Dışarıdan örnek sorular için çağrılabilir (welcome-screen butonları) */
  setQuestion(text) {
    this.els.questionInput.value = text;
    this.els.charCount.textContent = `${text.length} / 1000`;
    this._autoResizeTextarea();
    this.els.questionInput.focus();
  }
}

/* ══════════════════════════════════════════════════════════════
   Uygulama Başlatma
   ══════════════════════════════════════════════════════════════ */
if (typeof marked !== 'undefined') {
  marked.setOptions({ breaks: true, gfm: true });
}

let app;
document.addEventListener('DOMContentLoaded', () => {
  app = new DocuAskApp();
});
