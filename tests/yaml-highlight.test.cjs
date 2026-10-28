const test=require('node:test'),assert=require('node:assert/strict');
const {colorLine}=require('../app/static/assets/js/yaml-highlight.js');
test('YAML keys, strings, numbers, booleans and comments receive distinct colors',()=>{
 assert.match(colorLine('enabled: true'),/yaml-key.*enabled.*yaml-literal.*true/);
 assert.match(colorLine('count: 42'),/yaml-number">42/);
 assert.match(colorLine('title: "A # inside a string" # outside'),/yaml-string.*# inside.*yaml-comment.*# outside/);
 assert.match(colorLine('copy: *original'),/yaml-anchor/);
});
test('arbitrary YAML text is escaped, never injected as HTML',()=>{
 const result=colorLine('title: "<img src=x onerror=alert(1)> & hello"');
 assert.doesNotMatch(result,/<img/);assert.match(result,/&lt;img/);assert.match(result,/&amp;/);
 assert.doesNotMatch(colorLine('  # <script>alert(1)</script>'),/<script>/);
});
