/**
 * EduManage Pro - College Management System
 * Main JavaScript - Common utilities and interactions
 */

'use strict';

// ============================================================
// CSRF Token Handling
// ============================================================
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || '';

/**
 * Fetch wrapper with CSRF token and error handling
 */
async function apiFetch(url, options = {}) {
  const defaults = {
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': CSRF_TOKEN,
      'X-Requested-With': 'XMLHttpRequest'
    }
  };

  const config = {
    ...defaults,
    ...options,
    headers: { ...defaults.headers, ...(options.headers || {}) }
  };

  // Don't set Content-Type for FormData (browser sets multipart boundary)
  if (options.body instanceof FormData) {
    delete config.headers['Content-Type'];
  }

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new APIError(data.message || `HTTP ${response.status}`, response.status, data);
    }

    return data;
  } catch (err) {
    if (err instanceof APIError) throw err;
    throw new APIError('Network error. Please check your connection.', 0);
  }
}

class APIError extends Error {
  constructor(message, status, data = {}) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

// ============================================================
// Toast Notifications
// ============================================================
const Toast = {
  container: null,

  init() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'flash-container';
      document.body.appendChild(this.container);
    }
  },

  show(message, type = 'info', duration = 4000) {
    this.init();

    const iconMap = {
      success: 'bi-check-circle-fill',
      danger: 'bi-exclamation-circle-fill',
      warning: 'bi-exclamation-triangle-fill',
      info: 'bi-info-circle-fill'
    };

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible flash-alert d-flex align-items-center gap-2`;
    alert.innerHTML = `
      <i class="bi ${iconMap[type] || 'bi-info-circle-fill'}"></i>
      <span>${escapeHtml(message)}</span>
      <button type="button" class="btn-close ms-auto" onclick="this.parentElement.remove()"></button>
    `;

    this.container.appendChild(alert);

    if (duration > 0) {
      setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateX(100%)';
        setTimeout(() => alert.remove(), 300);
      }, duration);
    }

    return alert;
  },

  success(msg, duration) { return this.show(msg, 'success', duration); },
  error(msg, duration) { return this.show(msg, 'danger', duration); },
  warning(msg, duration) { return this.show(msg, 'warning', duration); },
  info(msg, duration) { return this.show(msg, 'info', duration); }
};

// ============================================================
// Loading Indicator
// ============================================================
const Loader = {
  overlay: null,

  show(message = 'Loading...') {
    if (!this.overlay) {
      this.overlay = document.createElement('div');
      this.overlay.className = 'loading-overlay';
      this.overlay.innerHTML = `
        <div class="text-center">
          <div class="spinner-ring mb-3"></div>
          <p class="text-muted loader-message">${escapeHtml(message)}</p>
        </div>
      `;
      document.body.appendChild(this.overlay);
    } else {
      this.overlay.querySelector('.loader-message').textContent = message;
      this.overlay.style.display = 'flex';
    }
  },

  hide() {
    if (this.overlay) {
      this.overlay.style.display = 'none';
    }
  }
};

// ============================================================
// Sidebar Toggle
// ============================================================
const Sidebar = {
  el: null,
  mainContent: null,
  overlay: null,
  isMobile: false,

  init() {
    this.el = document.getElementById('sidebar');
    this.mainContent = document.getElementById('mainContent');
    this.overlay = document.getElementById('sidebarOverlay');

    const toggleBtn = document.getElementById('sidebarToggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => this.toggle());
    }

    if (this.overlay) {
      this.overlay.addEventListener('click', () => this.closeMobile());
    }

    this.checkMobile();
    window.addEventListener('resize', () => this.checkMobile());

    // Restore state from localStorage
    const collapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (collapsed && !this.isMobile) {
      this.collapse();
    }

    // Highlight active nav link
    this.setActiveLink();
  },

  checkMobile() {
    this.isMobile = window.innerWidth < 769;
  },

  toggle() {
    if (this.isMobile) {
      this.el.classList.contains('mobile-open') ? this.closeMobile() : this.openMobile();
    } else {
      this.el.classList.contains('collapsed') ? this.expand() : this.collapse();
    }
  },

  collapse() {
    this.el?.classList.add('collapsed');
    this.mainContent?.classList.add('expanded');
    localStorage.setItem('sidebarCollapsed', 'true');
  },

  expand() {
    this.el?.classList.remove('collapsed');
    this.mainContent?.classList.remove('expanded');
    localStorage.setItem('sidebarCollapsed', 'false');
  },

  openMobile() {
    this.el?.classList.add('mobile-open');
    this.overlay?.classList.add('active');
    document.body.style.overflow = 'hidden';
  },

  closeMobile() {
    this.el?.classList.remove('mobile-open');
    this.overlay?.classList.remove('active');
    document.body.style.overflow = '';
  },

  setActiveLink() {
    const path = window.location.pathname;
    document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
      link.classList.remove('active');
      if (link.getAttribute('href') === path ||
          (path.startsWith(link.getAttribute('href')) && link.getAttribute('href') !== '/')) {
        link.classList.add('active');
      }
    });
  }
};

// ============================================================
// Notification Badge
// ============================================================
const NotifBadge = {
  async update() {
    try {
      const data = await apiFetch('/notifications/unread-count');
      const badge = document.getElementById('notifBadge');
      if (badge) {
        badge.textContent = data.count;
        badge.style.display = data.count > 0 ? 'flex' : 'none';
      }
    } catch (_) { /* Silently fail */ }
  },

  init() {
    this.update();
    setInterval(() => this.update(), 60000); // Refresh every minute
  }
};

// ============================================================
// Confirmation Dialog
// ============================================================
const Confirm = {
  modal: null,
  resolveCallback: null,

  init() {
    const modalHtml = `
      <div class="modal fade" id="confirmModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content">
            <div class="modal-header border-0">
              <h5 class="modal-title" id="confirmTitle">Confirm Action</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="confirmBody">Are you sure?</div>
            <div class="modal-footer border-0">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="confirmCancel">Cancel</button>
              <button type="button" class="btn btn-danger" id="confirmOk">Confirm</button>
            </div>
          </div>
        </div>
      </div>
    `;

    if (!document.getElementById('confirmModal')) {
      document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    this.modal = new bootstrap.Modal(document.getElementById('confirmModal'));

    document.getElementById('confirmOk').addEventListener('click', () => {
      this.modal.hide();
      if (this.resolveCallback) this.resolveCallback(true);
    });

    document.getElementById('confirmCancel').addEventListener('click', () => {
      if (this.resolveCallback) this.resolveCallback(false);
    });

    document.getElementById('confirmModal').addEventListener('hidden.bs.modal', () => {
      if (this.resolveCallback) this.resolveCallback(false);
    });
  },

  show(title, message, confirmText = 'Confirm', confirmClass = 'btn-danger') {
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmBody').innerHTML = message;
    const okBtn = document.getElementById('confirmOk');
    okBtn.textContent = confirmText;
    okBtn.className = `btn ${confirmClass}`;

    return new Promise(resolve => {
      this.resolveCallback = resolve;
      this.modal.show();
    });
  },

  async delete(itemName) {
    return this.show(
      'Delete Confirmation',
      `Are you sure you want to delete <strong>${escapeHtml(itemName)}</strong>?<br>
       <small class="text-muted">This action cannot be easily undone.</small>`,
      'Delete',
      'btn-danger'
    );
  }
};

// ============================================================
// Form Validation Helper
// ============================================================
const FormValidator = {
  validate(form) {
    let isValid = true;

    form.querySelectorAll('[required]').forEach(input => {
      if (!input.value.trim()) {
        input.classList.add('is-invalid');
        isValid = false;
      } else {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
      }
    });

    // Email validation
    form.querySelectorAll('[type="email"]').forEach(input => {
      if (input.value && !isValidEmail(input.value)) {
        input.classList.add('is-invalid');
        isValid = false;
      }
    });

    // Password confirmation
    const pwd = form.querySelector('[name="password"]');
    const pwdConfirm = form.querySelector('[name="confirm_password"]');
    if (pwd && pwdConfirm && pwdConfirm.value && pwd.value !== pwdConfirm.value) {
      pwdConfirm.classList.add('is-invalid');
      isValid = false;
    }

    return isValid;
  },

  reset(form) {
    form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
      el.classList.remove('is-invalid', 'is-valid');
    });
  }
};

// ============================================================
// Data Table Helpers
// ============================================================
const DataTable = {
  /**
   * Initialize search filter for a table
   * @param {string} inputId - Search input element ID
   * @param {string} tableId - Table element ID
   * @param {number} columnIndex - Column index to search (or -1 for all)
   */
  initSearch(inputId, tableId, columnIndex = -1) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);

    if (!input || !table) return;

    input.addEventListener('input', () => {
      const term = input.value.toLowerCase().trim();
      const rows = table.querySelectorAll('tbody tr');

      rows.forEach(row => {
        let text;
        if (columnIndex >= 0) {
          const cell = row.cells[columnIndex];
          text = cell ? cell.textContent.toLowerCase() : '';
        } else {
          text = row.textContent.toLowerCase();
        }
        row.style.display = text.includes(term) ? '' : 'none';
      });
    });
  }
};

// ============================================================
// File Upload Preview
// ============================================================
const FilePreview = {
  init(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);

    if (!input || !preview) return;

    input.addEventListener('change', () => {
      const file = input.files[0];
      if (!file) return;

      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = e => {
          preview.src = e.target.result;
          preview.style.display = 'block';
        };
        reader.readAsDataURL(file);
      } else {
        preview.style.display = 'none';
      }

      // Show file name
      const nameEl = document.getElementById(inputId + 'Name');
      if (nameEl) nameEl.textContent = file.name;
    });

    // Drag and drop on upload area
    const area = input.closest('.file-upload-area');
    if (area) {
      area.addEventListener('dragover', e => {
        e.preventDefault();
        area.classList.add('dragover');
      });

      area.addEventListener('dragleave', () => area.classList.remove('dragover'));

      area.addEventListener('drop', e => {
        e.preventDefault();
        area.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          input.files = e.dataTransfer.files;
          input.dispatchEvent(new Event('change'));
        }
      });

      area.addEventListener('click', () => input.click());
    }
  }
};

// ============================================================
// Password Strength Indicator
// ============================================================
const PasswordStrength = {
  check(password) {
    let score = 0;
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      numbers: /\d/.test(password),
      special: /[^A-Za-z0-9]/.test(password)
    };

    score = Object.values(checks).filter(Boolean).length;

    return {
      score,
      level: score <= 1 ? 'weak' : score <= 3 ? 'fair' : score <= 4 ? 'good' : 'strong',
      checks
    };
  },

  init(inputId, indicatorId) {
    const input = document.getElementById(inputId);
    const indicator = document.getElementById(indicatorId);

    if (!input || !indicator) return;

    input.addEventListener('input', () => {
      const result = this.check(input.value);
      const colors = { weak: 'danger', fair: 'warning', good: 'info', strong: 'success' };
      const widths = { weak: 25, fair: 50, good: 75, strong: 100 };

      indicator.innerHTML = `
        <div class="progress mt-1" style="height:4px">
          <div class="progress-bar bg-${colors[result.level]}" style="width:${widths[result.level]}%"></div>
        </div>
        <small class="text-${colors[result.level]} fw-600">${result.level.charAt(0).toUpperCase() + result.level.slice(1)}</small>
      `;
    });
  }
};

// ============================================================
// Grade Calculator
// ============================================================
function calculateGrade(percentage) {
  if (percentage >= 90) return 'O';
  if (percentage >= 80) return 'A+';
  if (percentage >= 70) return 'A';
  if (percentage >= 60) return 'B+';
  if (percentage >= 50) return 'B';
  if (percentage >= 40) return 'C';
  if (percentage >= 35) return 'D';
  return 'F';
}

// ============================================================
// Marks Entry Live Calculation
// ============================================================
function initMarksCalculation() {
  document.querySelectorAll('.marks-row').forEach(row => {
    const internal = row.querySelector('.internal-marks');
    const external = row.querySelector('.external-marks');
    const practical = row.querySelector('.practical-marks');
    const totalEl = row.querySelector('.total-marks');
    const percentEl = row.querySelector('.percentage-display');
    const gradeEl = row.querySelector('.grade-display');
    const statusEl = row.querySelector('.status-display');

    const maxInternal = parseInt(row.dataset.maxInternal || 40);
    const maxExternal = parseInt(row.dataset.maxExternal || 60);
    const maxPractical = parseInt(row.dataset.maxPractical || 0);
    const maxTotal = maxInternal + maxExternal + maxPractical;

    function recalculate() {
      const i = parseFloat(internal?.value || 0);
      const e = parseFloat(external?.value || 0);
      const p = parseFloat(practical?.value || 0);
      const total = i + e + p;
      const percentage = maxTotal > 0 ? (total / maxTotal * 100) : 0;
      const grade = calculateGrade(percentage);

      if (totalEl) totalEl.textContent = total.toFixed(0);
      if (percentEl) percentEl.textContent = percentage.toFixed(2) + '%';
      if (gradeEl) {
        gradeEl.textContent = grade;
        gradeEl.className = `grade-display grade-${grade.replace('+', '')}`;
      }
      if (statusEl) {
        const pass = percentage >= 35;
        statusEl.innerHTML = pass
          ? '<span class="badge badge-pass">Pass</span>'
          : '<span class="badge badge-fail">Fail</span>';
      }
    }

    [internal, external, practical].forEach(el => {
      if (el) el.addEventListener('input', recalculate);
    });
  });
}

// ============================================================
// Attendance Bulk Select
// ============================================================
function initAttendanceBulkSelect() {
  const selectAll = document.getElementById('markAllPresent');
  if (selectAll) {
    selectAll.addEventListener('click', () => {
      document.querySelectorAll('.attendance-status[value="Present"]').forEach(radio => {
        radio.checked = true;
      });
    });
  }

  const selectAbsent = document.getElementById('markAllAbsent');
  if (selectAbsent) {
    selectAbsent.addEventListener('click', () => {
      document.querySelectorAll('.attendance-status[value="Absent"]').forEach(radio => {
        radio.checked = true;
      });
    });
  }
}

// ============================================================
// Submit Attendance
// ============================================================
async function submitAttendance(sessionId, formId) {
  const form = document.getElementById(formId);
  if (!form) return;

  const rows = form.querySelectorAll('[data-student-id]');
  const records = [];

  rows.forEach(row => {
    const studentId = row.dataset.studentId;
    const status = row.querySelector('.attendance-status:checked')?.value;
    const remarks = row.querySelector('.attendance-remarks')?.value || '';

    if (studentId && status) {
      records.push({ student_id: parseInt(studentId), status, remarks });
    }
  });

  if (records.length === 0) {
    Toast.warning('No attendance records to save.');
    return;
  }

  try {
    Loader.show('Saving attendance...');
    const data = await apiFetch('/faculty/api/attendance/mark', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, records })
    });
    Loader.hide();
    Toast.success(`Attendance saved for ${records.length} students.`);
  } catch (err) {
    Loader.hide();
    Toast.error(err.message);
  }
}

// ============================================================
// Circular Progress Drawing
// ============================================================
function drawCircularProgress(elementId, percentage) {
  const container = document.getElementById(elementId);
  if (!container) return;

  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  let colorClass = 'safe';
  if (percentage < 60) colorClass = 'danger';
  else if (percentage < 75) colorClass = 'warning';

  container.innerHTML = `
    <svg viewBox="0 0 120 120">
      <circle class="bg-circle" cx="60" cy="60" r="${radius}" />
      <circle class="progress-circle ${colorClass}" cx="60" cy="60" r="${radius}"
        stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" />
    </svg>
    <div class="percentage-text">${percentage.toFixed(1)}%</div>
  `;
}

// ============================================================
// Utility Functions
// ============================================================
function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true
  });
}

function timeAgo(dateStr) {
  const now = new Date();
  const then = new Date(dateStr);
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return formatDate(dateStr);
}

function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ============================================================
// Tab Navigation for Multi-Tab Forms
// ============================================================
const TabForm = {
  init(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    const tabs = form.querySelectorAll('[data-tab]');
    const panes = form.querySelectorAll('[data-tab-pane]');

    function showTab(tabId) {
      tabs.forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tabId);
      });
      panes.forEach(p => {
        p.style.display = p.dataset.tabPane === tabId ? 'block' : 'none';
      });
    }

    tabs.forEach(tab => {
      tab.addEventListener('click', () => showTab(tab.dataset.tab));
    });

    // Next/Previous buttons
    form.querySelectorAll('[data-tab-next]').forEach(btn => {
      btn.addEventListener('click', () => {
        const current = form.querySelector('[data-tab-pane]:not([style*="none"])');
        const next = current?.nextElementSibling;
        if (next) showTab(next.dataset.tabPane);
      });
    });

    form.querySelectorAll('[data-tab-prev]').forEach(btn => {
      btn.addEventListener('click', () => {
        const current = form.querySelector('[data-tab-pane]:not([style*="none"])');
        const prev = current?.previousElementSibling;
        if (prev) showTab(prev.dataset.tabPane);
      });
    });

    // Show first tab
    if (tabs.length > 0) showTab(tabs[0].dataset.tab);
  }
};

// ============================================================
// Initialize Everything on DOM Ready
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  // Core
  Sidebar.init();
  Confirm.init();
  NotifBadge.init();

  // Auto-dismiss flash messages
  document.querySelectorAll('.flash-alert:not([data-permanent])').forEach(alert => {
    setTimeout(() => {
      if (alert.parentElement) {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
      }
    }, 5000);
  });

  // Initialize marks calculation if marks table exists
  if (document.querySelector('.marks-row')) {
    initMarksCalculation();
  }

  // Initialize attendance controls
  if (document.getElementById('attendanceForm')) {
    initAttendanceBulkSelect();
  }

  // Initialize search boxes with data-search-table attribute
  document.querySelectorAll('[data-search-table]').forEach(input => {
    const tableId = input.dataset.searchTable;
    DataTable.initSearch(input.id, tableId);
  });

  // Password strength
  const pwdInput = document.getElementById('password');
  if (pwdInput) {
    PasswordStrength.init('password', 'passwordStrength');
  }

  // File previews
  const photoInput = document.getElementById('profilePhoto');
  if (photoInput) {
    FilePreview.init('profilePhoto', 'photoPreview');
  }

  // Tooltips
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });

  // Popovers
  document.querySelectorAll('[data-bs-toggle="popover"]').forEach(el => {
    new bootstrap.Popover(el);
  });
});

// ============================================================
// Export for use in other scripts
// ============================================================
window.CMS = {
  apiFetch,
  Toast,
  Loader,
  Confirm,
  FormValidator,
  DataTable,
  FilePreview,
  PasswordStrength,
  TabForm,
  escapeHtml,
  isValidEmail,
  formatDate,
  formatDateTime,
  timeAgo,
  debounce,
  calculateGrade,
  drawCircularProgress,
  submitAttendance
};
