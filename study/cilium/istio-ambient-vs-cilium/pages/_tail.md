<script>
(function () {
  var C = { cyan: '#00d4ff', green: '#00ff88', gold: '#ffd700', red: '#ff6b6b', orange: '#ff9e64', dim: '#5a6070' };
  var CYCLE = ['cyan', 'green', 'gold', 'orange'];

  function parts(el, name) {
    var v = el.getAttribute(name);
    return v ? v.split('|') : [];
  }
  function txt(s) {
    return s.split('\\n').join('<br>');
  }
  function done(el) {
    if (el.getAttribute('data-rendered') === '1') return true;
    el.setAttribute('data-rendered', '1');
    return false;
  }

  Array.prototype.forEach.call(document.querySelectorAll('.seq'), function (el) {
    if (done(el)) return;
    var nodes = parts(el, 'data-seq');
    var acc = parts(el, 'data-accent');
    var html = '';
    for (var i = 0; i < nodes.length; i++) {
      var key = acc[i] && C[acc[i]] ? acc[i] : 'cyan';
      if (i > 0) html += '<div class="seq-arrow"></div>';
      html += '<div class="seq-node" style="border-color:' + C[key] + '">' + txt(nodes[i]) + '</div>';
    }
    el.innerHTML = html;
  });

  Array.prototype.forEach.call(document.querySelectorAll('.stack'), function (el) {
    if (done(el)) return;
    var layers = parts(el, 'data-stack');
    var acc = parts(el, 'data-accent');
    var html = '';
    for (var i = 0; i < layers.length; i++) {
      var w = 100 - i * 8;
      var key = acc[i] && C[acc[i]] ? acc[i] : CYCLE[i % CYCLE.length];
      html += '<div class="stack-layer" style="width:' + w + '%;border-color:' + C[key] + '">' + txt(layers[i]) + '</div>';
    }
    el.innerHTML = html;
  });

  Array.prototype.forEach.call(document.querySelectorAll('.steps'), function (el) {
    if (done(el)) return;
    var items = parts(el, 'data-steps');
    var start = parseInt(el.getAttribute('data-start') || '1', 10);
    var html = '';
    for (var i = 0; i < items.length; i++) {
      html += '<div class="step"><div class="step-num">' + (start + i) + '</div>'
        + '<div class="step-txt">' + txt(items[i]) + '</div></div>';
    }
    el.innerHTML = html;
  });

  Array.prototype.forEach.call(document.querySelectorAll('.cmp'), function (el) {
    if (done(el)) return;
    var html = '';
    ['left', 'right'].forEach(function (side) {
      var title = el.getAttribute('data-' + side + '-title') || '';
      var items = parts(el, 'data-' + side);
      var body = '';
      for (var i = 0; i < items.length; i++) body += '<div class="cmp-item">' + txt(items[i]) + '</div>';
      html += '<div class="cmp-col ' + side + '"><div class="cmp-title">' + title + '</div>' + body + '</div>';
    });
    el.innerHTML = html;
  });
})();
</script>
