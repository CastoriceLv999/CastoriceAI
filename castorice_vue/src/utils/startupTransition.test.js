import test from 'node:test'
import assert from 'node:assert/strict'
import { startupFrame, TRANSITION_DURATION, sweepEdges } from './startupTransition.js'
test('left-to-right cover and reveal keep the background swap opaque',()=>{
  const width=1000
  assert.equal(sweepEdges(.2,width).front,width/2)
  assert.equal(sweepEdges(.4,width).front,width+sweepEdges(.4,width).feather)
  assert.equal(sweepEdges(.5,width).tail,-sweepEdges(.5,width).feather)
  assert.ok(Math.abs(sweepEdges(.79,width).tail-width/2)<.001)
  assert.equal(sweepEdges(1,width).tail,width+sweepEdges(1,width).feather)
})
test('startup handoff is fully covered before intro disappears',()=>{
  assert.equal(startupFrame(0).introOpacity,1)
  assert.equal(startupFrame(0).interfaceOpacity,0)
  assert.equal(startupFrame(TRANSITION_DURATION*.48).cover,1)
  assert.equal(startupFrame(TRANSITION_DURATION*.57).introOpacity,0)
  assert.equal(startupFrame(TRANSITION_DURATION*.57).cover,1)
  assert.equal(startupFrame(TRANSITION_DURATION).done,true)
  assert.equal(startupFrame(TRANSITION_DURATION).interfaceOpacity,1)
  assert.equal(startupFrame(TRANSITION_DURATION).cover,0)
})
test('reduced motion completes with a brief dissolve and bounded values',()=>{
  assert.equal(startupFrame(500,true).done,true)
  for(let t=-100;t<4000;t+=50)for(const value of Object.values(startupFrame(t)).filter(x=>typeof x==='number'))assert.ok(value>=0&&value<=1)
})
