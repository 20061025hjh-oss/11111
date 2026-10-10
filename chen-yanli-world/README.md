# 陈燕丽的异世界生活

GitHub Pages 发布文件已准备好，位于仓库根目录的 `docs/`。

在[Pages 设置](https://github.com/20061025hjh-oss/11111/settings/pages)选择 **Deploy from a branch → main → /docs → Save**，等待部署完成。

GitHub Pages 开通后的游戏地址：`https://20061025hjh-oss.github.io/11111/`。手机和电脑均可直接打开游玩。

原创方块像素横版冒险游戏，主角为陈燕丽。此文件夹保存最新手机网页版及早期 Python 桌面原版。

## 网页版

- 三个关卡：风铃草原、暮色矿谷、星光城堡。
- 金币、怪物、城堡守卫、存档点、二段跳、魔法与方块建造。
- 手机支持同时触控移动、跳跃、攻击；电脑支持键盘操作。
- 三首原创循环配乐、25 种分层音效、缓存音效同时播放。
- 独立音乐/音效音量，暂停或切出页面停止音乐，兼容播放和试音按钮。
- 最高分与关卡解锁保存在浏览器本地。

GitHub Pages 发布来源：`main` 分支的 `/docs` 文件夹。发布文件与本目录 `dist/` 的最新版一致。

## 本地运行网页版

安装 Python 3 后，在本文件夹打开终端运行：

```bash
python -m http.server 8000 --directory dist
```

电脑浏览器打开 `http://localhost:8000`。手机与电脑连接同一 Wi-Fi 时，手机打开 `http://电脑的局域网IP:8000`；电脑需允许此端口访问。网页使用 ES 模块，请通过 HTTP 服务运行。

点“开始冒险”或“试音”后开启声音。默认从提前生成的内存音频缓冲区直接触发音效，不在操作时下载音频；实际输出延迟仍受设备和浏览器影响。若试音无声，在“声音设置”中开启“兼容播放”。

电脑操作：A / D 或方向键移动，空格跳跃（可二段跳），Shift 加速，J 魔法，B 建造，P 暂停，R 重开，Esc 首页。

## Python 桌面原版

```bash
python "python/陈燕丽的异世界生活.py"
```

使用 Python 标准库 Tkinter，无需游戏引擎。若系统未安装 Tkinter，需先安装对应组件。Python 文件为早期桌面原版；本次增强背景音乐与低延迟音效在网页版中实现。

## 开发与检查

安装 Node.js 22 或更新版本，无需安装第三方依赖：

```bash
npm test
npm run audio
```

`npm test` 检查关卡通关、游戏事件、触控输入、音效缓存与叠加、音乐切换和兼容播放逻辑。自动检查使用模拟音频及页面环境，实际手机听感需设备试玩。

`npm run audio` 根据 `dist/audio-data.js` 重新生成全部 WAV 音效和配乐；`dist/audio/` 已包含生成文件，正常试玩无需重新生成。

## 文件

- `dist/index.html`、`style.css`：页面与响应式布局。
- `dist/game.js`：游戏逻辑、Canvas 绘制、键盘与触控操作。
- `dist/assets.js`：原创像素角色与关卡数据。
- `dist/sound.js`：音效缓冲、混音、音乐循环、播放模式与音量控制。
- `dist/audio-data.js`：音色合成与三首原创配乐的乐谱。
- `dist/audio/`：兼容模式使用的完整 WAV 音频资源。
- `generate-audio.mjs`：可重复运行的音频生成脚本。
- `python/`：Python 桌面原版。

本项目保留通用源码与资源，不包含托管平台配置或凭据。

## 更新 GitHub Pages 发布文件

修改 `dist/` 后，将其中的全部文件同步复制到仓库根目录的 `docs/`，保留 `docs/.nojekyll`，再提交到 `main`。开启 Pages 后，后续提交会触发重新发布。
