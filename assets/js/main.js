/* ---- Sidebar layout interactions ---- */
(function () {
  'use strict';

  /* ---- Reading progress bar ---- */
  var progressFill = document.querySelector('.progress-fill');
  if (progressFill) {
    var ticking = false;
    function updateProgress() {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      var pct = max > 0 ? (h.scrollTop / max) * 100 : 0;
      progressFill.style.width = pct + '%';
      ticking = false;
    }
    window.addEventListener('scroll', function () {
      if (!ticking) {
        window.requestAnimationFrame(updateProgress);
        ticking = true;
      }
    }, { passive: true });
    updateProgress();
  }

  /* ---- Mobile drawer toggle ---- */
  var sidebar = document.querySelector('.sidebar');
  var toggle = document.querySelector('.sidebar-toggle');
  var overlay = document.querySelector('.sidebar-overlay');

  function openSidebar() {
    if (sidebar) sidebar.classList.add('open');
    if (overlay) overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  if (toggle) {
    toggle.addEventListener('click', function () {
      if (sidebar && sidebar.classList.contains('open')) closeSidebar();
      else openSidebar();
    });
  }
  if (overlay) overlay.addEventListener('click', closeSidebar);
  /* Close drawer when a nav link is tapped (mobile) */
  if (sidebar) {
    sidebar.querySelectorAll('.sidebar-nav a').forEach(function (a) {
      a.addEventListener('click', function () {
        if (window.innerWidth < 900) closeSidebar();
      });
    });
  }
  /* ESC to close */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSidebar();
  });

  /* ---- Scrollspy on homepage sections ---- */
  /* Match section id to nav link by href path segment:
     section "about"        → nav link href ending in "/" (home)
     section "publications" → nav link href containing "/publications/"
     section "news"         → nav link href containing "/news/"  */
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.sidebar-nav a'));
  if (!navLinks.length || !('IntersectionObserver' in window)) return;

  function findLinkForSection(id) {
    if (id === 'about') {
      return navLinks.filter(function (l) {
        var h = l.getAttribute('href') || '';
        return /\/(en|zh)\/?$/.test(h.replace(/\/+$/, '/'));
      })[0];
    }
    return navLinks.filter(function (l) {
      return (l.getAttribute('href') || '').indexOf('/' + id + '/') !== -1;
    })[0];
  }

  /* Only run on homepage (where these sections exist) */
  var homeSections = ['about', 'publications', 'news']
    .map(function (id) {
      var el = document.getElementById(id);
      var link = el ? findLinkForSection(id) : null;
      return el && link ? { el: el, link: link } : null;
    })
    .filter(Boolean);

  if (homeSections.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var match = homeSections.filter(function (s) { return s.el === entry.target; })[0];
          if (match) {
            navLinks.forEach(function (l) { l.classList.remove('active'); });
            match.link.classList.add('active');
          }
        }
      });
    }, { rootMargin: '-20% 0px -70% 0px', threshold: 0 });
    homeSections.forEach(function (s) { observer.observe(s.el); });
  }
})();
