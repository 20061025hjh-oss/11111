import assert from 'node:assert/strict';
import {boot} from './dist/game.js';
const ids=new Map(),frames=[];
class Classes{constructor(){this.s=new Set()}add(x){this.s.add(x)}remove(x){this.s.delete(x)}contains(x){return this.s.has(x)}}
const context=new Proxy({}, {get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>{o[k]=v;return true;}});
class El{
 constructor(id=''){this.id=id;this.listeners={};this.classList=new Classes();this.dataset={};this.textContent='';this.children=[];this.hidden=false;if(id)ids.set(id,this);}
 addEventListener(k,f){(this.listeners[k]||=[]).push(f)}
 setAttribute(k,v){this[k]=v}
 setPointerCapture(){}
 getContext(){return context}
 getBoundingClientRect(){return{left:0,top:0,width:393,height:393*640/1000}}
 append(e){this.children.push(e)}
 set innerHTML(s){this.html=s;for(const x of s.matchAll(/id="([^"]+)"/g))new El(x[1]);}
}
for(const id of['game','sound','soundTest','soundStatus','music','fxVolume','musicVolume','compatAudio','build','recover','pause','fullscreen','home','playArea','overlay','dialog','hpLabel','coinLabel','toast'])new El(id);
ids.get('playArea').parentElement=new El('parent');
const buttons=['left','right','shift','j','jump'].map(key=>{const b=new El();b.dataset.key=key;return b;});
globalThis.document={getElementById:id=>ids.get(id),createElement:()=>new El(),querySelectorAll:()=>buttons,addEventListener:()=>{},body:new El(),hidden:false};
globalThis.window={addEventListener:()=>{}};
globalThis.localStorage={getItem:()=>null,setItem:()=>{}};
globalThis.requestAnimationFrame=f=>frames.push(f);
const app=boot();frames.shift()(performance.now()+17);assert(ids.get('dialog').html.includes('陈燕丽的异世界生活'));
app.act('start');frames.shift()(performance.now()+34);assert.equal(ids.get('overlay').hidden,true);
const event=id=>({pointerId:id,preventDefault(){}});
buttons[0].listeners.pointerdown[0](event(1));buttons[4].listeners.pointerdown[0](event(2));
assert(app.keys.has('left')&&app.keys.has('jump'));assert.equal(app.game.player.jump_buffer,.15);
app.game.update(1/120,app.keys);assert(app.game.player.vx<0);assert(app.game.player.vy<0);
buttons[4].listeners.pointerup[0](event(2));assert(app.keys.has('left')&&!app.keys.has('jump'));
buttons[0].listeners.pointerup[0](event(1));assert.equal(app.keys.size,0);
ids.get('pause').onclick();assert.equal(app.game.state,'paused');ids.get('pause').onclick();assert.equal(app.game.state,'play');
ids.get('build').onclick();assert(app.game.build_mode);
ids.get('game').listeners.pointerdown[0]({clientX:130*.393,clientY:535*.393,button:0,preventDefault(){}});assert.equal(app.game.level.tiles.get('3,13'),'X');
ids.get('recover').onclick();ids.get('game').listeners.pointerdown[0]({clientX:130*.393,clientY:535*.393,button:0,preventDefault(){}});assert(!app.game.level.tiles.has('3,13'));
ids.get('fullscreen').onclick();assert(document.body.classList.contains('immersive'));ids.get('fullscreen').onclick();assert(!document.body.classList.contains('immersive'));
ids.get('music').onclick();assert.equal(app.audio.musicEnabled,false);ids.get('music').onclick();assert.equal(app.audio.musicEnabled,true);ids.get('fxVolume').oninput({target:{value:'.52'}});ids.get('musicVolume').oninput({target:{value:'.18'}});assert.equal(app.audio.fxVolume,.52);assert.equal(app.audio.musicVolume,.18);
console.log('PASS: start overlay, simultaneous touch input, key release, pause/resume, touch build/recover and fullscreen fallback.');
