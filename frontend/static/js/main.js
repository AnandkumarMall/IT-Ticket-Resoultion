/**
 * main.js
 * Global JS for IT Ticket Resolution Engine Flask Frontend
 */

// ── Tab switching ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

  // Generic tab init
  document.querySelectorAll('.tabs').forEach(tabGroup => {
    const buttons = tabGroup.querySelectorAll('.tab-btn');
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.tab;
        if (!target) return;

        // Deactivate all in this tab group's sibling panes
        buttons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Find panes: siblings after the .tabs element
        let parent = tabGroup.parentElement;
        parent.querySelectorAll('.tab-pane').forEach(pane => {
          pane.classList.toggle('active', pane.id === target);
        });
      });
    });
  });

  // ── Auto-dismiss flash messages after 5 s ──────────────────
  const container = document.getElementById('flash-container');
  if (container) {
    setTimeout(() => {
      container.querySelectorAll('.alert').forEach(el => {
        el.style.transition = 'opacity 0.5s';
        el.style.opacity    = '0';
        setTimeout(() => el.remove(), 500);
      });
    }, 5000);
  }

  // ── Add spinner to any form submit button on submit ─────────
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function (e) {
      // Don't double-disable if already handled (e.g. ticket form)
      const btn = form.querySelector('button[type="submit"]');
      if (btn && !btn.dataset.handled) {
        btn.dataset.handled = 'true';
        // Small delay so the spinner is visible
        setTimeout(() => {
          btn.innerHTML = '<span class="spinner"></span> Please wait…';
          btn.disabled  = true;
        }, 50);
      }
    });
  });

  // ── Highlight active nav link ───────────────────────────────
  const currentPath = window.location.pathname;
  document.querySelectorAll('.btn-nav').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.style.color      = 'var(--indigo-400)';
      link.style.background = 'rgba(99,102,241,0.12)';
    }
  });
});
