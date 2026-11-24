// Original wing geometry and markings, inspired by violet morpho-like butterflies.
// Wing halves are cached once and articulated independently during flight.
export function createButterflyArt() {
  const fore=new Path2D('M 16 147 C 31 114 35 47 96 14 C 124 -2 153 7 166 32 C 187 76 149 111 107 135 C 72 151 40 156 16 147 Z')
  const hind=new Path2D('M 17 147 C 72 133 132 141 157 174 Q 171 192 152 207 Q 153 220 135 222 Q 131 236 115 232 Q 106 244 93 235 Q 77 244 68 231 Q 51 235 45 220 C 24 207 17 172 17 147 Z')
  const wings=Array.from({length:3},(_,variant)=>{
    const canvas=document.createElement('canvas');canvas.width=192;canvas.height=256
    const c=canvas.getContext('2d')
    for(const wing of [hind,fore]){
      c.save();c.clip(wing)
      const g=c.createLinearGradient(12,160,148,30)
      g.addColorStop(0,'#34216f');g.addColorStop(.24,['#c183f2','#a080ed','#d390ef'][variant]);g.addColorStop(.53,['#8932e3','#6546d7','#a343cf'][variant]);g.addColorStop(.72,'#4c1b88');g.addColorStop(.86,'#20112f');g.addColorStop(1,'#100c1c')
      c.fillStyle=g;c.fillRect(0,0,192,256)
      const sheen=c.createRadialGradient(66,139,0,79,131,105);sheen.addColorStop(0,'#cfaaff66');sheen.addColorStop(.5,'#5529d233');sheen.addColorStop(1,'#120c2900');c.fillStyle=sheen;c.fillRect(0,0,192,256)
      // Fine deterministic scales, rather than a flat solid-color silhouette.
      let seed=47+variant*31
      for(let i=0;i<1400;i++){seed=(seed*1664525+1013904223)>>>0;const x=seed%185;seed=(seed*1664525+1013904223)>>>0;const y=seed%250;c.fillStyle=i%3?'#f0d8ff13':'#1506221c';c.fillRect(x,y,.6,1.5)}
      const tips=[[98,17],[133,12],[163,35],[177,65],[151,101],[126,124],[156,185],[139,214],[111,231],[78,229],[49,214]]
      for(const [x,y]of tips){c.beginPath();c.moveTo(17,148);c.quadraticCurveTo((x+17)/2+10,(y+148)/2-9,x,y);c.strokeStyle='#1c123f88';c.lineWidth=1.3;c.stroke();c.strokeStyle='#d9bcf52c';c.lineWidth=.35;c.stroke()}
      c.restore();c.strokeStyle='#170d29';c.lineWidth=5;c.stroke(wing);c.strokeStyle='#c59cdb66';c.lineWidth=.7;c.stroke(wing)
    }
    // Irregular ivory patches and smaller edge pearls echo real wing patterning.
    for(const [x,y,rx,ry,a]of [[103,28,5,8,-.5],[127,25,4,6,-.4],[148,39,3,5,-.6],[159,57,2.6,4,-.5],[147,78,7,10,-.6],[130,91,4,6,-.5],[113,104,3,4,-.5],[151,186,3,4,.4],[138,207,2.5,3,.3],[118,222,2,3,.3],[95,229,2.5,2.5,0],[72,223,2,3,-.3],[53,211,2,3,-.4]]){
      c.save();c.translate(x,y);c.rotate(a);c.fillStyle='#f7e8ff';c.beginPath();c.ellipse(0,0,rx,ry,0,0,Math.PI*2);c.fill();c.restore()
    }
    return canvas
  })
  const petal=document.createElement('canvas');petal.width=96;petal.height=128
  const p=petal.getContext('2d');const g=p.createLinearGradient(15,110,70,15);g.addColorStop(0,'#71408000');g.addColorStop(.3,'#aa70c9');g.addColorStop(.68,'#e8b8ed');g.addColorStop(1,'#fff0fa')
  p.fillStyle=g;p.beginPath();p.moveTo(25,115);p.bezierCurveTo(-4,69,31,20,78,8);p.bezierCurveTo(97,61,53,108,25,115);p.fill();p.strokeStyle='#fff0ff80';p.lineWidth=.7;p.beginPath();p.moveTo(25,115);p.quadraticCurveTo(58,61,78,8);p.stroke()
  return {wings,petal}
}

export function paintButterfly(c,art,x,y,size,angle,beat,variant,alpha,blur=0){
  c.save();c.translate(x,y);c.rotate(angle);c.scale(size/340,size/340);c.globalAlpha=alpha
  if(blur)c.filter=`blur(${blur}px)`
  const fold=.16+Math.pow((Math.sin(beat)+1)/2,.75)*.84
  for(const side of [-1,1]){c.save();c.scale(side*fold,1);c.drawImage(art.wings[variant],-16,-147);c.restore()}
  c.fillStyle='#261632';c.beginPath();c.ellipse(0,1,3.6,24,0,0,Math.PI*2);c.fill();c.fillStyle='#e5b5f0';c.beginPath();c.ellipse(-.7,-14,1.2,6,-.2,0,Math.PI*2);c.fill()
  c.strokeStyle='#d7b3dfb0';c.lineWidth=.8
  for(const side of [-1,1]){c.beginPath();c.moveTo(side,-20);c.quadraticCurveTo(side*9,-41,side*17,-42);c.stroke()}
  c.restore()
}
