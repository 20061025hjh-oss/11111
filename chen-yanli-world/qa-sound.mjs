import assert from 'node:assert/strict';
import {SoundEngine,EFFECTS} from './dist/sound.js';
import {Game} from './dist/game.js';
class Param{constructor(){this.value=0;this.events=[]}cancelScheduledValues(t){this.events.push(['cancel',t]);}setTargetAtTime(v,t,s){assert(Number.isFinite(v)&&s>0);this.events.push([v,t,s]);}}
class Gain{constructor(){this.gain=new Param()}connect(){}disconnect(){}}
class Source{constructor(ctx){this.ctx=ctx;this.playbackRate={value:1};this.loop=false;}connect(){}disconnect(){}start(t,offset=0){this.startTime=t;this.offset=offset;this.ctx.sources.push(this)}stop(){this.stopped=true;this.onended?.();}}
class Context{
 constructor(options){this.options=options;this.state='suspended';this.currentTime=5;this.destination={};this.sources=[];this.bufferCount=0;}
 createGain(){return new Gain()}
 createBuffer(n,size,rate){this.bufferCount++;const data=new Float32Array(size);return{duration:size/rate,getChannelData:()=>data};}
 createBufferSource(){return new Source(this)}
 resume(){return Promise.resolve().then(()=>{this.state='running'})}
}
const host={AudioContext:Context,navigator:{audioSession:{type:'ambient'}},performance:{now:()=>1000}};
const a=new SoundEngine(host);a.prewarm();assert.equal(a.ctx.options.latencyHint,'interactive');assert.equal(a.buffers.size,28);assert(!a.ready);
const unlock=a.unlock();a.play('start');assert.equal(a.pending.length,1);await unlock;assert(a.ready);assert.equal(host.navigator.audioSession.type,'playback');assert.equal(a.pending.length,0);
const music=a.musicSource;assert(music.loop);assert.equal(music.startTime,a.ctx.currentTime);
// 动作触发直接启动缓存声音，不等待 Promise、网络加载或定时器。
const count=a.ctx.sources.length;a.play('jump');a.play('coin');a.play('magic');assert.equal(a.ctx.sources.length,count+3);assert([...a.voices].every(s=>s.startTime===a.ctx.currentTime));assert(![...a.voices].some(s=>s.stopped));
const buffers=a.ctx.bufferCount;for(const name of Object.keys(EFFECTS)){a.recent.delete(name);a.play(name);}assert.equal(a.ctx.bufferCount,buffers);assert(a.voices.size<=32);
a.setScene('paused',0);assert(music.stopped);assert.equal(a.musicSource,null);a.setScene('play',0);assert(a.musicSource.loop);
const first=a.musicSource;a.setScene('play',1);assert(first.stopped);assert.equal(a.musicSource.buffer,a.buffers.get('bg1'));a.setScene('play',1);const same=a.musicSource;a.setScene('play',1);assert.equal(a.musicSource,same);
a.setMusicEnabled(false);assert.equal(a.musicSource,null);a.setMusicEnabled(true);assert(a.musicSource);
a.setVolume('music',.16);a.setVolume('fx',.61);assert.equal(a.musicVolume,.16);assert.equal(a.fxVolume,.61);
a.setScene('gameover',1);assert.equal(a.musicSource,null);a.setScene('menu',1);assert.equal(a.musicSource.buffer,a.buffers.get('bg0'));
a.setEnabled(false);assert.equal(a.voices.size,0);assert.equal(a.musicSource,null);const n=a.ctx.sources.length;a.play('coin');assert.equal(a.ctx.sources.length,n);
await a.test();assert(a.enabled);assert(a.musicSource);assert([...a.voices].some(s=>s.buffer===a.buffers.get('test')));
// 切回页面后恢复被冻结的 AudioContext；过期动作不能积压后响。
a.ctx.state='suspended';a.play('jump');a.pending.push(['coin',-100]);await a.unlock();assert.equal(a.pending.length,0);
const noAudio=new SoundEngine({});noAudio.prewarm();assert.equal(await noAudio.unlock(),false);noAudio.setEnabled(false);
const g=new Game(),events=[];g.onSound=n=>events.push(n);g.start();assert(events.includes('start'));g.level.enemies=[];g.player.jump_buffer=.15;g.update(1/120,new Set());assert(events.includes('jump'));g.player.jump_buffer=.15;g.update(1/120,new Set());assert(events.includes('doubleJump'));g.shoot();const shots=events.filter(x=>x==='magic').length;g.shoot();assert.equal(events.filter(x=>x==='magic').length,shots);
g.player.x=240;g.player.y=514;g.player.vy=0;g.update(1/120,new Set());assert(events.includes('coin'));g.damage(false,300);const hurts=events.filter(x=>x==='hurt').length;g.damage(false,300);assert.equal(events.filter(x=>x==='hurt').length,hurts);
const h=new Game(),e=[];h.onSound=n=>e.push(n);h.start(2);const guardian=h.level.enemies.find(m=>m.kind==='guardian');h.player.x=guardian.x-300;h.update(1/120,new Set());assert(e.includes('boss'));h.hitEnemy(guardian,99);assert(e.includes('bossDefeat'));
const walking=new Game(),steps=[];walking.onSound=n=>steps.push(n);walking.start();walking.level.enemies=[];walking.player.x=80;for(let i=0;i<50;i++)walking.update(1/120,new Set(['right']));assert(steps.includes('step'));walking.player.grounded=false;walking.player.y=480;walking.player.vy=400;for(let i=0;i<20;i++)walking.update(1/120,new Set());assert(steps.includes('land'));
console.log('PASS: 25 cached sounds, immediate same-tick starts, overlap, interactive context, music transitions, independent volumes, pause/mute/recovery and game events.');
