// node --test: cloze rendering against what Anki's own renderer produced for the same notes
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { clozeNumbers, clozeTexts, renderCard } from './render.js'

const clozeType = { type: 1, name: 'Lückentext', css: '', flds: [{ name: 'Text' }], tmpls: [{ name: 'Lückentext', qfmt: '{{cloze:Text}}', afmt: '{{cloze:Text}}' }] }
const render = (text, ord) => renderCard({ ord, note: { flds: text, tags: '' }, nt: clozeType, deck: 'T' })

test('simple cloze with hint', () => {
  const r = render('{{c1::Berlin::Stadt}} ist in {{c2::DE}}', 1)
  assert.equal(r.question, '<span class="cloze-inactive" data-ordinal="1">Berlin</span> ist in <span class="cloze" data-cloze="DE" data-ordinal="2">[...]</span>')
  assert.ok(render('{{c1::Berlin::Stadt}} ist in {{c2::DE}}', 0).question.startsWith('<span class="cloze" data-cloze="Berlin" data-ordinal="1">[Stadt]</span> ist'))
})

test('nested clozes like Anki', () => {
  const text = '{{c1::Haupt {{c2::innen}} weiter}}'
  assert.deepEqual(clozeNumbers(text), [1, 2])
  assert.equal(render(text, 1).question, '<span class="cloze-inactive" data-ordinal="1">Haupt <span class="cloze" data-cloze="innen" data-ordinal="2">[...]</span> weiter</span>')
  assert.equal(render(text, 1).answer, '<span class="cloze-inactive" data-ordinal="1">Haupt <span class="cloze" data-ordinal="2">innen</span> weiter</span>')
  assert.equal(render(text, 0).answer, '<span class="cloze" data-ordinal="1">Haupt <span class="cloze-inactive" data-ordinal="2">innen</span> weiter</span>')
  assert.deepEqual(clozeTexts(text, 1), ['Haupt innen weiter'])
})

test('image occlusion masks like Anki', () => {
  const occ = '{{c1::image-occlusion:rect:left=.1:top=.2:width=.3:height=.15:oi=1}}<br>{{c2::image-occlusion:polygon:points=.1,.1 .2,.3 .05,.4}}'
  assert.equal(render(occ, 0).question,
    '<div class="cloze" data-ordinal="1" data-shape="rect" data-left=".1" data-top=".2" data-width=".3" data-height=".15" data-occludeInactive="1" ></div><br>' +
    '<div class="cloze-inactive" data-ordinal="2" data-shape="polygon" data-points=".1,.1 .2,.3 .05,.4" ></div>')
  assert.match(render(occ, 0).answer, /class="cloze-highlight" data-ordinal="1"/)
})
