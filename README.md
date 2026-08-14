# 🐋 dsh-whale-font

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

把 DeepSeek Harness（DSH）对话里的主语人称「**我 / 你 / I / me**」显示成 **DeepSeek 官方蓝色鲸鱼图标**。

纯显示层替换：不改动任何消息数据、不影响模型读取/记忆、输入框不受影响。一眼就能分辨出每句话的主语（说话者）。

## 功能

| 位置 | 效果 |
|---|---|
| 助手消息里的「我」 | → 🐋 鲸鱼 |
| 你发送的「你」 | → 🐋 鲸鱼 |
| 助手消息里的英文 `I`、`me`（独立单词） | → 🐋 鲸鱼 |
| 引号内的「你 / 我」（助手复读你的话时） | 保持原样 |
| 代码块 `<code>` / `<pre>` 内 | 不替换 |
| 输入框（正在打字） | 不替换 |

复制消息时，「我/你/I/me」都会**还原成原字**（不会复制出空字符或图片）；鲸鱼身体蓝色、肚子/眼睛在深浅模式下都固定白色。

## 实现原理

两套机制配合，各管各的：

| 层 | 处理什么 | 机制 | 说明 |
|---|---|---|---|
| 字体层 | 中文「我」「你」 | 自定义彩色字体（COLR/CFF） | 字符出现即渲染成鲸鱼，**零 DOM 改动、零闪烁、实时**，复制出来仍是原字；身体蓝、肚子/眼睛固定白 |
| DOM 层 | 英文 `I`/`me`、引号内还原 | 监听页面 + 插入 SVG / 包裹基础字体 | 字体做不到「整词判断」和「上下文判断」，只能靠这层补 |

> 为什么英文 `I`/`me` 不走字体？因为字体是逐字符映射，会把 `It`/`Idea` 里的 `I`、`message`/`time` 里的 `me` 也误替换。DOM 层用单词边界精确匹配独立的 `I`/`me`。

## 安装

### 前置要求

- 已安装 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（`dsh` 命令可用）。

### 方式一：官方命令（推荐）

一条命令装好：

```bash
dsh plugin --profile web add github:kxSenlin/dsh-whale-font
```

装完**重启 DSH 服务**，再在浏览器里**强制刷新**（`Ctrl + Shift + R`）即可。

用 `dsh plugin --profile web list` 可以确认插件已在列表里。升级重跑同一条 `add` 命令即可。

### 方式二：手动安装（离线 / 不想走 git）

1. 把本仓库的 `lib/` 和 `package.json`、`cordis.patch.yml` 放到 `~/.dsh/profiles/node_modules/dsh-whale-font/` 下；
2. 编辑 `~/.dsh/profiles/web/cordis.patch.yml`，在末尾加上：

   ```yaml
   - insert:
       - id: whale-font
         name: 'dsh-whale-font'
   ```

   （若该文件原本只有 `[]`，就用上面三行替换 `[]`。）
3. 重启 DSH 服务，浏览器强制刷新（`Ctrl + Shift + R`）。

> 路径说明：`~` 是用户主目录 —— Windows 是 `C:\Users\<用户名>`，macOS/Linux 是 `/Users/<用户名>` 或 `/home/<用户名>`。

## 调整大小 / 位置（可选）

默认就是仓库作者调好的大小。想自己微调：

1. `pip install fonttools`
2. 编辑 `tune/whale-config.json`：

   | 参数 | 含义 |
   |---|---|
   | `scaleX` | 鲸鱼视觉宽度（越大越宽） |
   | `scaleY` | 鲸鱼视觉高度（越大越高） |
   | `yOffset` | 上下位置（越大越往下） |
   | `advanceWidth` | 鲸鱼在句子里占的宽度槽位（普通字 = 1000） |
   | `leftBearing` | 鲸鱼头前面的空白（越大鲸鱼越往右） |

3. 运行 `python tune/adjust_whale.py`（自动读取同目录的 `favicon.svg` 和 `whale-config.json`，重新生成字体并写回插件目录）。
4. 浏览器强制刷新即可，**不用重启 DSH**。

## 卸载

```bash
dsh plugin --profile web remove dsh-whale-font
```

手动安装的，删除 `~/.dsh/profiles/node_modules/dsh-whale-font/` 目录，并删掉 `~/.dsh/profiles/web/cordis.patch.yml` 里那三行，再重启 DSH。

## 常见问题

**Q：复制消息时英文 `I`/`me` 会丢字吗？**
A：不会。`I`/`me` 显示成鲸鱼，但复制出来仍是原字（图标里藏了一个透明的原字，正常看不见、拖蓝选中时会浮现）。中文「我/你」走字体，复制也仍是原字。

**Q：鲸鱼是黑色 / 颜色不对？**
A：鲸鱼身体是 DeepSeek 蓝 `#4d6bfe`，肚子/眼睛固定白色，深色模式也不会变黑。若显示异常，确认浏览器较新（COLR 彩色字体需 Chrome 71+ / Firefox / Safari 16.4+）。

**Q：升级 DSH 后鲸鱼不见了？**
A：本插件依赖界面内部 CSS 类名（`Sxvs8a_`、`gdEzaW_bubble` 等），DSH 升级后这些类名可能变化导致失效。届时需更新 `lib/client.js` 里的选择器。

## License

[MIT](LICENSE)

## 目录结构

```
dsh-whale-font/
├── package.json        声明 dsh.bundle.patch + dsh.client
├── cordis.patch.yml    配置层（把插件挂进 profile）
├── lib/
│   ├── index.js        节点端（空实现）
│   └── client.js       浏览器端（字体 + DOM 逻辑，含内嵌 base64 字体）
├── tune/               调参工具（可选）
│   ├── adjust_whale.py
│   ├── whale-config.json
│   └── favicon.svg
├── LICENSE
└── README.md
```
