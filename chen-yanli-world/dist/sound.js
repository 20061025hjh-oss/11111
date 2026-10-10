import {EFFECTS,MUSIC_NAMES,SAMPLE_RATE,renderPCM,musicScore} from './audio-data.js?v=music3';
export {EFFECTS,MUSIC_NAMES};
export class SoundEngine {
 constructor(host=globalThis){
  this.host=host;this.enabled=true;this.musicEnabled=true;this.fxVolume=.72;this.musicVolume=.28;this.compat=false;
  this.ctx=null;this.ready=false;this.lastError='';this.onState=()=>{};this.resuming=null;this.pending=[];
  this.voices=new Set();this.buffers=new Map();this.pcm=new Map();this.pools=new Map();this.tracks=[];this.recent=new Map();this.serial=0;
  this.scene='menu';this.levelIndex=0;this.musicSource=null;this.musicKey='';this.musicOffset=0;this.musicStarted=0;this.mediaMusic=null;
  try{this.enabled=host.localStorage?.getItem('chen-yanli-sound')!=='off';this.musicEnabled=host.localStorage?.getItem('chen-yanli-music')!=='off';this.compat=host.localStorage?.getItem('chen-yanli-compat')==='on';}catch{}
  // 提前在内存生成 PCM；操作时不请求、不解码、不重新加载音频。
  for(const [name,notes] of Object.entries(EFFECTS))this.pcm.set(name,renderPCM(notes));
  for(let i=0;i<3;i++){const s=musicScore(i);this.pcm.set(`bg${i}`,renderPCM(s.notes,s.duration,true));}
 }
 clock(){return(this.host.performance?.now?.()??Date.now())/1000;}
 pref(k,v){try{this.host.localStorage?.setItem(k,v?'on':'off');}catch{}}
 session(){try{if(this.host.navigator?.audioSession)this.host.navigator.audioSession.type='playback';}catch{}}
 prepareContext(){
  if(this.ctx&&this.ctx.state!=='closed')return;
  const Ctx=this.host.AudioContext||this.host.webkitAudioContext;if(!Ctx)throw Error('No Web Audio');
  this.ctx=new Ctx({latencyHint:'interactive'});this.buffers.clear();
  this.master=this.ctx.createGain();this.master.gain.value=.85;this.master.connect(this.ctx.destination);
  this.fxGain=this.ctx.createGain();this.fxGain.gain.value=this.fxVolume;this.fxGain.connect(this.master);
  this.musicGain=this.ctx.createGain();this.musicGain.gain.value=this.musicVolume;this.musicGain.connect(this.master);
  for(const [name,pcm] of this.pcm){const buffer=this.ctx.createBuffer(1,pcm.length,SAMPLE_RATE);buffer.getChannelData(0).set(pcm);this.buffers.set(name,buffer);}
 }
 prepareMedia(){
  if(this.pools.size||!this.host.Audio)return;
  const make=name=>{const a=new this.host.Audio(new URL(`./audio/${name}.wav?v=music3`,import.meta.url).href);a.preload='auto';a.setAttribute('playsinline','');a.load?.();return a;};
  for(const name of Object.keys(EFFECTS))this.pools.set(name,[make(name),make(name),make(name)]);
  this.tracks=[0,1,2].map(i=>{const a=make(`bg${i}`);a.loop=true;return a;});
 }
 prewarm(){try{if(!this.compat)this.prepareContext();else this.prepareMedia();}catch{this.prepareMedia();}}
 unlock(){
  if(!this.enabled)return Promise.resolve(false);this.session();
  if(this.compat||(!this.host.AudioContext&&!this.host.webkitAudioContext)){
   this.prepareMedia();if(!this.host.Audio){this.lastError='当前浏览器不支持声音，请用 Safari / Chrome 打开';this.onState();return Promise.resolve(false);}
   this.ready=true;this.lastError='';this.updateMusic();this.flush();this.onState();return Promise.resolve(true);
  }
  try{
   this.prepareContext();if(this.ctx.state==='running'){this.ready=true;this.lastError='';this.updateMusic();this.flush();this.onState();return Promise.resolve(true);}
   if(!this.resuming)this.resuming=Promise.resolve(this.ctx.resume()).then(()=>{this.resuming=null;this.ready=this.ctx.state==='running';this.lastError=this.ready?'':'请点“试音”启用声音';if(this.enabled){this.updateMusic();this.flush();}this.onState();return this.ready;}).catch(()=>{this.resuming=null;this.ready=false;this.lastError='声音未启用，请点“试音”或打开“兼容播放”';this.onState();return false;});
   return this.resuming;
  }catch{this.ready=false;this.lastError='请在声音设置中开启“兼容播放”';this.onState();return Promise.resolve(false);}
 }
 flush(){const q=this.pending.splice(0);for(const [name,time] of q)if(this.clock()-time<.18)this.play(name);}
 setEnabled(value){this.enabled=!!value;this.pref('chen-yanli-sound',this.enabled);if(!this.enabled)this.silence();else if(this.ready)this.updateMusic();this.onState();return this.enabled;}
 setMusicEnabled(value){this.musicEnabled=!!value;this.pref('chen-yanli-music',this.musicEnabled);this.updateMusic();this.onState();}
 setVolume(kind,value){value=Math.max(0,Math.min(1,Number(value)));if(kind==='music')this.musicVolume=value;else this.fxVolume=value;const gain=kind==='music'?this.musicGain:this.fxGain;if(gain){gain.gain.cancelScheduledValues(this.ctx.currentTime);gain.gain.setTargetAtTime(value,this.ctx.currentTime,.015);}if(this.mediaMusic)this.mediaMusic.volume=this.musicVolume;}
 setCompat(value){this.silence();this.compat=!!value;this.ready=false;this.pref('chen-yanli-compat',this.compat);this.prewarm();return this.unlock();}
 test(){this.recent.delete('test');this.setEnabled(true);const result=this.unlock();this.play('test');return result;}
 setScene(state,index=0){if(state===this.scene&&index===this.levelIndex)return;const old=this.levelIndex;this.scene=state;this.levelIndex=index;if(old!==index){this.stopMusic();this.musicOffset=0;}this.updateMusic();}
 musicWanted(){return this.enabled&&this.musicEnabled&&this.ready&&['menu','play'].includes(this.scene);}
 stopMusic(){
  this.serial++;
  if(this.musicSource){this.musicOffset=(this.musicOffset+this.ctx.currentTime-this.musicStarted)%this.musicSource.buffer.duration;try{this.musicSource.stop();this.musicSource.disconnect();}catch{}this.musicSource=null;}
  this.mediaMusic?.pause();this.mediaMusic=null;this.musicKey='';
 }
 updateMusic(){
  if(!this.musicWanted()){this.stopMusic();return;}
  const index=this.scene==='menu'?0:this.levelIndex,key=`bg${index}`;if(this.musicKey===key)return;
  this.stopMusic();this.musicKey=key;
  if(this.compat||!this.ctx){
   this.prepareMedia();const a=this.tracks[index];if(!a)return;a.volume=this.musicVolume;this.mediaMusic=a;
   const token=++this.serial;try{Promise.resolve(a.play()).catch(()=>{if(token!==this.serial)return;this.lastError='音乐播放被阻止，请再次点“试音”';this.musicKey='';this.onState();});}catch{this.musicKey='';}return;
  }
  if(this.ctx.state!=='running'){this.musicKey='';return;}
  const s=this.ctx.createBufferSource();s.buffer=this.buffers.get(key);s.loop=true;s.connect(this.musicGain);this.musicSource=s;this.musicStarted=this.ctx.currentTime;s.start(this.ctx.currentTime,this.musicOffset%s.buffer.duration);
 }
 silence(){this.pending=[];this.serial++;this.stopMusic();for(const voice of [...this.voices]){try{voice.stop();voice.disconnect();}catch{}this.voices.delete(voice);}for(const pool of this.pools.values())for(const a of pool)a.pause();}
 play(name){
  if(!this.enabled||!EFFECTS[name])return;
  if(!this.ready||this.ctx&&!this.compat&&this.ctx.state!=='running'){this.pending.push([name,this.clock()]);this.pending=this.pending.slice(-12);return;}
  const now=this.clock(),previous=this.recent.get(name)??-100;if(now-previous<(name==='step'?.16:.025))return;this.recent.set(name,now);
  if(this.compat||!this.ctx){this.prepareMedia();const pool=this.pools.get(name);if(!pool)return;const a=pool.find(p=>p.paused||p.ended)??pool[0];try{a.currentTime=0;a.volume=this.fxVolume*(name==='step'?.28:name==='land'?.60:1);Promise.resolve(a.play()).catch(()=>{this.lastError='音效播放被阻止，请再次点“试音”';this.onState();});}catch{}return;}
  if(this.voices.size>=32){const oldest=this.voices.values().next().value;oldest.stop();this.voices.delete(oldest);}
  const source=this.ctx.createBufferSource();source.buffer=this.buffers.get(name);source.playbackRate.value=name==='step'?(this.voices.size%2?1.08:.97):1;
  const gain=this.ctx.createGain();gain.gain.value=name==='step'?.28:name==='land'?.60:name==='click'?.65:1;source.connect(gain);gain.connect(this.fxGain);this.voices.add(source);source.onended=()=>{this.voices.delete(source);source.disconnect();gain.disconnect();};
  // 调用与游戏事件在同一帧，直接从当前音频时刻启动。
  source.start(this.ctx.currentTime);
  if(['clear','win','gameover','boss','bossDefeat','checkpoint'].includes(name)&&this.musicSource){const t=this.ctx.currentTime,p=this.musicGain.gain;p.cancelScheduledValues(t);p.setTargetAtTime(this.musicVolume*.38,t,.012);p.setTargetAtTime(this.musicVolume,t+Math.min(.8,source.buffer.duration),.10);}
 }
}
