/**
 * Progressive-enhancement scroll reveal.
 * Elements marked `.reveal` are visible by default (see style.css) so the
 * page works with JS disabled; this only adds the animated entrance and
 * bails out entirely for prefers-reduced-motion.
 */
(function () {
  var root = document.documentElement;
  root.classList.add('js');

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var targets = document.querySelectorAll('.reveal');

  if (prefersReducedMotion || !('IntersectionObserver' in window) || !targets.length) {
    targets.forEach(function (el) {
      el.classList.add('is-visible');
    });
    return;
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );

  targets.forEach(function (el) {
    observer.observe(el);
  });
})();

/**
 * Mobile nav toggle.
 * `.site-nav__links` is visible by default (see style.css) so the menu
 * works with JS disabled; this only adds the collapse/hamburger behaviour.
 */
(function () {
  var navToggle = document.querySelector('.nav-toggle');
  var navLinks = document.querySelector('.site-nav__links');

  if (!navToggle || !navLinks) {
    return;
  }

  var closeMenu = function () {
    navToggle.setAttribute('aria-expanded', 'false');
    navLinks.classList.remove('is-open');
  };

  navToggle.addEventListener('click', function () {
    var isOpen = navLinks.classList.toggle('is-open');
    navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  });

  navLinks.addEventListener('click', function (event) {
    if (event.target.closest('a')) {
      closeMenu();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      closeMenu();
    }
  });

  window.addEventListener('resize', function () {
    if (window.innerWidth > 640) {
      closeMenu();
    }
  });
})();
