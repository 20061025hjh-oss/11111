import assert from 'node:assert/strict';
import {Game,canvasPoint} from './dist/game.js';
const step=1/120, tick=(g,n=1,keys=new Set())=>{for(let i=0;i<n;i++)g.update(step,keys);};
const fresh=(i=0)=>{const g=new Game();g.start(i);return g;};
let g=fresh();tick(g,120);assert(g.player.grounded);assert.equal(g.player.y,514);
g.level.enemies=[];g.player.jump_buffer=.15;tick(g,20);assert(g.player.y<450);assert.equal(g.player.jumps,1);g.player.jump_buffer=.15;tick(g);assert.equal(g.player.jumps,0);tick(g,200);assert(g.player.grounded);assert.equal(g.player.jumps,2);
g=fresh();g.level.enemies=[];g.player.x=240;tick(g,6);assert.equal(g.coins,1);assert.equal(g.score,50);
g=fresh();g.damage(false,120);g.damage(false,120);assert.equal(g.player.hp,4);g.player.invulnerable=0;g.player.star=8;g.damage(false,120);assert.equal(g.player.hp,4);g.damage(true);assert.equal(g.player.hp,3);assert.equal(g.player.x,80);
g=fresh();g.build_mode=true;assert(g.build(3,13));assert.equal(g.materials,19);assert(!g.build(2,13));assert(!g.build(30,13));assert(g.build(3,13,true));assert.equal(g.materials,20);assert(!g.build(2,14,true));
g=fresh();g.level.enemies=[];const q=[...g.level.tiles].find(([k,v])=>v==='Q')[0].split(',').map(Number);g.player.x=q[0]*40+6;g.player.jump_buffer=.15;tick(g,50);assert.equal(g.level.tiles.get(q.join(',')),'U');
g=fresh();g.level.pickups=[];g.player.x=720;g.level.enemies=[{x:840,y:530,w:32,h:30,vx:0,vy:0,kind:'crab',hp:2,dead:false,flash:0}];g.shoot();tick(g,30);assert.equal(g.level.enemies[0].hp,1);tick(g,12);g.shoot();tick(g,30);assert(g.level.enemies[0].dead);
g=fresh();g.level.enemies=[];g.player.x=g.level.checkpoint_x;tick(g);assert(g.checkpoint);g.player.y=900;tick(g);assert.equal(g.player.x,g.level.checkpoint_x);
g=fresh();g.score=999;g.coins=42;g.materials=0;g.restart();assert.equal(g.score,0);assert.equal(g.coins,0);assert.equal(g.materials,20);
// 手机上画面可能左右留边，点按必须映射到画面坐标而不是元素宽度。
const fake={getBoundingClientRect:()=>({left:10,top:20,width:844,height:390})};
const center=canvasPoint(fake,432,215);assert(Math.abs(center.x-500)<.001);assert(Math.abs(center.y-320)<.001);
const edge=canvasPoint(fake,10,215);assert(edge.x<0);
for(let index=0;index<3;index++){
 g=fresh(index);
 for(let frame=0;frame<24000&&g.state==='play';frame++){
  const p=g.player,gap=g.level.gaps.find(([a,b])=>a*40-100<p.x&&p.x<b*40+20),hazard=g.level.hazards.find(h=>h.x-110<p.x&&p.x<h.x+h.w);
  if(p.grounded&&((gap&&p.x+28>gap[0]*40-65)||hazard))p.jump_buffer=.15;
  if(gap&&p.jumps>0&&p.vy>30&&p.x<gap[1]*40)p.jump_buffer=.15;
  g.update(step,new Set(['right','shift','j']));
 }
 assert.equal(g.state,index<2?'stageclear':'win');
 console.log(`关卡 ${index+1} 连续通关通过，生命 ${g.player.hp}，分数 ${g.score}`);
}
console.log('PASS: gameplay, build/recover, checkpoint, rewards, projectile, mobile coordinate mapping and all three stages.');
