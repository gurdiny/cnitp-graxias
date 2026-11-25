/* CNITP · Inicio — JS sin dependencias (sustituye React + support.js). */
(function () {
  'use strict';

  var reducedMQ = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  var reduced = function () { return !!(reducedMQ && reducedMQ.matches); };

  /* ---------- Selector de área (Tanatología / Psicología) ---------- */
  var AREAS = ['tanatologia', 'psicologia'];

  function setArea(area, opts) {
    if (AREAS.indexOf(area) === -1) { return; }
    var i;
    var doors = document.querySelectorAll('[data-area]');
    for (i = 0; i < doors.length; i += 1) {
      doors[i].setAttribute('aria-pressed', String(doors[i].getAttribute('data-area') === area));
    }
    var blocks = document.querySelectorAll('[data-area-show]');
    for (i = 0; i < blocks.length; i += 1) {
      blocks[i].hidden = blocks[i].getAttribute('data-area-show') !== area;
    }
    var status = document.getElementById('cn-area-status');
    if (status && opts && opts.announce) {
      status.textContent = 'Mostrando el Área de ' + (area === 'tanatologia' ? 'Tanatología' : 'Psicología') + '.';
    }
    if (opts && opts.scroll) {
      var target = document.getElementById(area);
      if (target) {
        target.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });
        var heading = target.querySelector('h3');
        if (heading) {
          heading.setAttribute('tabindex', '-1');
          heading.focus({ preventScroll: true });
        }
      }
    }
  }

  function areaFromHash() {
    var h = (location.hash || '').replace('#', '');
    return AREAS.indexOf(h) !== -1 ? h : null;
  }

  document.addEventListener('click', function (ev) {
    var el = ev.target.closest ? ev.target.closest('[data-area], a[href="#tanatologia"], a[href="#psicologia"]') : null;
    if (!el) { return; }
    if (el.hasAttribute('data-area')) {
      setArea(el.getAttribute('data-area'), { announce: true });
      return;
    }
    // Enlaces de navegación: mostrar el área antes de que el navegador haga scroll.
    ev.preventDefault();
    var area = el.getAttribute('href').slice(1);
    if (history.pushState) { history.pushState(null, '', '#' + area); }
    setArea(area, { scroll: true });
  });

  window.addEventListener('hashchange', function () {
    var a = areaFromHash();
    if (a) { setArea(a, { scroll: true }); }
  });

  // Enlace directo (#psicologia): mostrar el área ya, y hacer scroll cuando
  // fuentes e imágenes terminaron de cargar para no quedar desfasados.
  var initial = areaFromHash();
  if (initial) {
    setArea(initial);
    var jump = function () {
      var el = document.getElementById(initial);
      if (el) { el.scrollIntoView({ block: 'start' }); }
    };
    if (document.readyState === 'complete') { jump(); } else { window.addEventListener('load', jump, { once: true }); }
  }

  /* ---------- Contadores de cifras ---------- */
  (function counters() {
    var nodes = document.querySelectorAll('[data-cn-count]');
    if (!nodes.length || reduced() || typeof IntersectionObserver !== 'function') { return; }
    var fmt = function (v) { return Math.round(v).toLocaleString('en-US'); };
    var run = function (el) {
      var target = parseInt(el.getAttribute('data-cn-count'), 10);
      if (!(target > 0)) { return; }
      var finalText = el.textContent;
      var start = 0;
      var tick = function (now) {
        if (!start) { start = now; }
        var p = (now - start) / 1500;
        if (p >= 1) { el.textContent = finalText; return; }
        el.textContent = fmt(target * (1 - Math.pow(1 - p, 3)));
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    var io = new IntersectionObserver(function (entries) {
      for (var j = 0; j < entries.length; j += 1) {
        if (entries[j].isIntersecting) {
          io.unobserve(entries[j].target);
          run(entries[j].target);
        }
      }
    }, { threshold: 0.5 });
    for (var n = 0; n < nodes.length; n += 1) { io.observe(nodes[n]); }
  })();

  /* ---------- Mariposa del hero (curva de Fay) ---------- */
  (function mariposa() {
    var cv = document.querySelector('canvas[data-cn-mariposa]');
    if (!cv || !cv.getContext) { return; }
    var ctx = cv.getContext('2d');
    if (!ctx) { return; }

    var K = 2400;
    var DRAW = 4.6;
    var px = new Float32Array(K + 1);
    var py = new Float32Array(K + 1);
    var minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
    for (var i = 0; i <= K; i += 1) {
      var t = 12 * Math.PI * i / K;
      var r = Math.exp(Math.cos(t)) - 2 * Math.cos(4 * t) - Math.pow(Math.sin(t / 12), 5);
      var x = Math.sin(t) * r;
      var y = Math.cos(t) * r;
      px[i] = x; py[i] = y;
      if (x < minX) { minX = x; } if (x > maxX) { maxX = x; }
      if (y < minY) { minY = y; } if (y > maxY) { maxY = y; }
    }
    var spanX = maxX - minX;
    var spanY = maxY - minY;
    var midY = (minY + maxY) / 2;

    var dust = [];
    for (var d0 = 0; d0 < 18; d0 += 1) {
      dust.push({ x: Math.random(), y: Math.random(), v: 0.012 + Math.random() * 0.02, r: 0.6 + Math.random() * 1.1, ph: Math.random() * 6.28 });
    }

    var W = 0, H = 0, s = 1, cx = 0, cy = 0, grad = null, step = 1, halo = 9;
    var dirty = true;      // hay que recalcular tamaño
    var t0 = 0;            // inicio de la animación
    var paused = 0;        // ms acumulados en pausa (para no saltar al volver)
    var pausedAt = 0;
    var raf = 0;
    var inView = true;

    function fit() {
      var w = cv.clientWidth, h = cv.clientHeight;
      if (!(w > 1) || !(h > 1)) { return false; }
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      var bw = Math.round(w * dpr), bh = Math.round(h * dpr);
      if (cv.width !== bw || cv.height !== bh) { cv.width = bw; cv.height = bh; }
      W = w; H = h;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      s = Math.min(W * 0.8 / spanX, H * 0.78 / spanY);
      cx = W / 2;
      cy = H / 2 + midY * s;
      grad = ctx.createLinearGradient(0, cy - maxY * s, 0, cy - minY * s);
      grad.addColorStop(0, '#F6E3A6');
      grad.addColorStop(0.5, '#D9B25F');
      grad.addColorStop(1, '#8F6E2A');
      step = W < 430 ? 2 : 1;
      halo = W < 430 ? 6 : 9;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      dirty = false;
      return true;
    }

    function trace(from, to, sx, k, oy) {
      var q = s * k;
      ctx.beginPath();
      ctx.moveTo(cx + px[from] * q * sx, cy + oy - py[from] * q);
      for (var j = from + step; j < to; j += step) {
        ctx.lineTo(cx + px[j] * q * sx, cy + oy - py[j] * q);
      }
      ctx.lineTo(cx + px[to] * q * sx, cy + oy - py[to] * q);
    }

    function strokeMain(n, sx, oy) {
      trace(0, n, sx, 1, oy);
      ctx.strokeStyle = grad;
      ctx.globalAlpha = 0.05; ctx.lineWidth = halo; ctx.stroke();
      ctx.globalAlpha = 0.13; ctx.lineWidth = 3.4; ctx.stroke();
      ctx.globalAlpha = 0.92; ctx.lineWidth = 1.15; ctx.stroke();
    }

    function strokeGhost(sxg, oy, alpha) {
      trace(0, K, sxg, 1.13, oy);
      ctx.strokeStyle = '#B8923F';
      ctx.globalAlpha = alpha; ctx.lineWidth = 1; ctx.stroke();
    }

    function paintStatic() {
      if (!fit()) { return; }
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter';
      strokeGhost(0.9, 0, 0.1);
      strokeMain(K, 1, 0);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    }

    function paint(now) {
      if (dirty && !fit()) { return; }
      if (!t0) { t0 = now; }
      var e = (now - t0 - paused) / 1000;
      var p = Math.min(e / DRAW, 1);
      var eased = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
      var n = Math.max(2, Math.floor(eased * K));
      var after = e - DRAW;
      var amp = after > 0 ? Math.min(after / 1.6, 1) : 0;
      var sx = 1 - 0.13 * amp * (0.5 - 0.5 * Math.cos(after * 1.16));
      var sxg = 1 - 0.24 * amp * (0.5 - 0.5 * Math.cos(after * 1.16 - 0.9));
      var oy = amp * 3 * Math.sin(e * 0.9);

      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter';

      var fadeIn = Math.min(e / 2, 1);
      ctx.fillStyle = '#E9CB7B';
      for (var d = 0; d < dust.length; d += 1) {
        var du = dust[d];
        var yy = (du.y - e * du.v) % 1;
        if (yy < 0) { yy += 1; }
        ctx.globalAlpha = 0.5 * Math.sin(yy * 3.1416) * fadeIn;
        ctx.beginPath();
        ctx.arc(du.x * W + Math.sin(e * 0.5 + du.ph) * 9, yy * H, du.r, 0, 6.2832);
        ctx.fill();
      }

      if (amp > 0.01) { strokeGhost(sxg, oy, 0.1 * amp); }
      strokeMain(n, sx, oy);

      var heads = [];
      if (p < 1) {
        heads.push(n);
      } else {
        var f = after * 0.03;
        heads.push(Math.floor((f % 1) * K));
        heads.push(Math.floor(((f * 0.73 + 0.41) % 1) * K));
      }
      for (var hi = 0; hi < heads.length; hi += 1) {
        var hd = heads[hi];
        var tail = Math.max(0, hd - 90);
        if (hd - tail > 3) {
          trace(tail, hd, sx, 1, oy);
          ctx.strokeStyle = '#FFF6D8';
          ctx.globalAlpha = 0.5; ctx.lineWidth = 1.9; ctx.stroke();
        }
        var hx = cx + px[hd] * s * sx;
        var hy = cy + oy - py[hd] * s;
        ctx.fillStyle = '#F6E3A6';
        ctx.globalAlpha = 0.2;
        ctx.beginPath(); ctx.arc(hx, hy, 8, 0, 6.2832); ctx.fill();
        ctx.fillStyle = '#FFFFFF';
        ctx.globalAlpha = 0.95;
        ctx.beginPath(); ctx.arc(hx, hy, 2, 0, 6.2832); ctx.fill();
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    }

    function loop(now) {
      raf = requestAnimationFrame(loop);
      paint(now);
    }

    function start() {
      if (raf || reduced()) { return; }
      if (pausedAt) { paused += performance.now() - pausedAt; pausedAt = 0; }
      raf = requestAnimationFrame(loop);
    }
    function stop() {
      if (!raf) { return; }
      cancelAnimationFrame(raf);
      raf = 0;
      pausedAt = performance.now();
    }
    function sync() {
      if (reduced()) { stop(); paintStatic(); return; }
      if (inView && !document.hidden) { start(); } else { stop(); }
    }

    if (typeof ResizeObserver === 'function') {
      new ResizeObserver(function () {
        dirty = true;
        if (reduced()) { paintStatic(); }
      }).observe(cv);
    } else {
      window.addEventListener('resize', function () { dirty = true; });
    }

    if (typeof IntersectionObserver === 'function') {
      new IntersectionObserver(function (entries) {
        inView = entries[entries.length - 1].isIntersecting;
        sync();
      }, { threshold: 0.02 }).observe(cv);
    }
    document.addEventListener('visibilitychange', sync);
    if (reducedMQ && reducedMQ.addEventListener) { reducedMQ.addEventListener('change', sync); }
    sync();
  })();
})();
