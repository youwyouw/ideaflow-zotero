# ideaflow-zotero

[English](README.md)

用 Codex 或 Claude Code 把一个研究 idea 整理成 Zotero 阅读分类。你可以发研究问题、论文链接或会议 PDF。Skill 会先核对库里已有的记录，再逐篇整理成可以打开原文的独立条目，每条配一张 Memory Card。

## 需要准备什么

| | 要求 | 怎么确认 |
| --- | --- | --- |
| Zotero | 同一台电脑上装有 **Zotero Desktop 10 或更新版本**。[下载 Zotero](https://www.zotero.org/download/) | 在 Zotero 里点 **帮助 → 关于 Zotero**。 |
| Python | **Python 3.10 或更新版本**。[下载 Python](https://www.python.org/downloads/) | 在终端运行 `python --version`。macOS 上运行 `python3 --version`。 |
| AI 助手 | **Codex**（桌面版或命令行）或 **Claude Code**（桌面版或命令行），在你自己的电脑上运行。 | 这个 Skill 要在本机运行脚本。网页版 ChatGPT 和网页版 Claude 访问不到你电脑上的 Zotero。 |

Windows 用户安装 Python 时，记得勾选 **Add python.exe to PATH**。如果运行 `python --version` 弹出了微软商店，说明还没装好，请从 python.org 安装，然后重新打开一个终端。

## 第一次使用前的设置（只需做一次）

### 1. 允许其他应用和 Zotero 通信

Zotero 默认不让其他程序读取或修改你的文献库，需要手动打开一次本地 API：

1. 打开 Zotero Desktop。
2. 打开设置：Windows 和 Linux 点 **编辑 → 设置**，macOS 点 **Zotero → 设置**。
3. 进入 **高级** 标签页，勾选 **允许本机上的其他应用与 Zotero 通信**。

这个开关只允许你本机上的程序连接，外部网络连不进来。使用 Skill 时请保持 Zotero 开着。

### 2. 下载项目

在 GitHub 页面点 **Code → Download ZIP**，然后**解压**。要用解压出来的文件夹，不要直接在压缩包预览窗口里打开。会用 Git 的话也可以直接克隆仓库。

### 3. 在 AI 助手里打开项目文件夹

- **Codex：** 把解压出的 `ideaflow-zotero` 文件夹作为工作区或项目打开。如果 Codex 问是否信任这个文件夹，选择信任，这样它才能运行自带的脚本。
- **Claude Code 桌面版：** 把解压出的 `ideaflow-zotero` 文件夹选为工作文件夹。
- **Claude Code 命令行：** 打开终端，进入项目文件夹后启动：

  ```sh
  cd 你的路径/ideaflow-zotero
  claude
  ```

项目里已经自带两份 Skill：Codex 用 `.agents/skills`，Claude Code 用 `.claude/skills`。如果助手里找不到 `ideaflow-zotero`，重启一下助手。

### 4. 检查连接

对助手说：

```text
用 ideaflow-zotero 检查一下能不能连上 Zotero，不要修改任何东西。
```

助手会运行状态检查命令。你也可以在项目文件夹里自己运行：

```sh
python .agents/skills/ideaflow-zotero/scripts/zotero.py status
```

看到 `"reachable": true` 和 `"write_api_supported": true` 就说明设置好了。如果不是，请看下面的[常见问题](#常见问题)。

## 第一次正式使用

在 Codex 输入 `$ideaflow-zotero`，在 Claude Code 输入 `/ideaflow-zotero`，再接上类似下面的请求：

```text
我想研究，AI 和用户一起制定方案后，遇到新证据时
会不会更难撤回原来的建议。先查我的 Zotero，再推荐最多五篇能帮助我
设计实验的论文。Memory Card 请用英文在前、简体中文在后的格式。
先给我看导入计划。
```

过程中会遇到三种确认：

1. **助手请求运行命令。** Skill 要运行 `python …/zotero.py` 来读写 Zotero。看一下命令内容，没问题就同意。
2. **助手给你看导入计划。** 计划里列出目标分类，以及每篇文献是新建、复用还是加卡片。这时还没写入任何东西，你可以要求修改，或者让它开始写入。
3. **Zotero 弹窗询问是否允许 `ideaflow-zotero` 写入。** 在 Zotero 窗口里点 **允许**。之后或导入较多文献时，可能会再问几次。

第一次建议只让它在一个新分类里放一两篇试试。Skill 只会新增条目、分类归属、标签和它自己的卡片，会保留你已有的笔记，不会删除任何条目。

## 在其他项目里使用

把整个 `ideaflow-zotero` 技能文件夹（包括 `scripts` 和 `references`）复制到用户目录：Codex 放到 `~/.agents/skills`，Claude Code 放到 `~/.claude/skills`。复制后重启助手。 [Codex Skill 文档](https://learn.chatgpt.com/docs/build-skills) · [Claude Code Skill 文档](https://code.claude.com/docs/en/skills)

## 文献放在哪里

| 输入 | Zotero 位置 | 得到什么 |
| --- | --- | --- |
| 一个科研问题或正在推进的课题 | **Research Ideas → <Idea>** | 一张 Idea Card，记录当前问题、已有证据、研究空白和下一步检验。把能推进该 idea 的文献归入对应分类。 |
| 会议 PDF、综述或参考文献表 | **Research Directions → <来源或主题>** | 把引用整理成独立文献条目，每篇可以打开原文，并有自己的 Memory Card。 |
| 想以后读的论文 | **To Read** | 每篇一条，按需加 Reading Guide。 |

分类和标签默认用英文，也可以在请求中指定名称（例如 `待读`）和笔记语言。双语卡片按篇排版，先放完整英文块，再放对应中文。 [卡片格式](.agents/skills/ideaflow-zotero/references/cards.md)

**Memory Card** 包含要点、背景、方法、结论和研究空白，区分论文发现与自己的判断，并标注阅读依据是全文、摘要还是二手资料。需要辅助阅读时，可以加 **Reading Guide**，标出优先看的图表、章节和原文入口。

同一篇文章可以属于多个 Zotero 分类。写入时会优先复用已有条目，保留已有笔记。同一份计划重复执行时，脚本会检查已导入的条目和卡片。

## 分享给合作者

让助手将选中的分类导出为 Markdown 阅读清单和 BibTeX 文件。默认导出题录和来源链接，也可以明确要求附带 IdeaFlow Memory Cards。发出前请检查导出文件。

## 常见问题

| 报错或现象 | 怎么办 |
| --- | --- |
| `Could not complete GET /. Keep Zotero open and check that its local API is enabled.` | 打开 Zotero Desktop，并确认已完成[第 1 步](#1-允许其他应用和-zotero-通信)的设置。如果 Zotero 开着、设置也打开了，可能是助手的沙箱拦截了本机网络访问。助手请求运行命令时点同意，或者允许它以可访问本机网络的方式运行。 |
| `HTTP 403` 或 `Zotero did not grant write authorization.` | 检查第 1 步的设置，然后重新发一次请求，在 Zotero 弹窗里点 **允许**。 |
| `"write_api_supported": false` | 在 **帮助 → 检查更新** 里把 Zotero 升级到 10 或更新版本。 |
| `HTTP 429` | Zotero 限制了连续的授权弹窗。等一分钟再试。 |
| `HTTP 409` 或 `HTTP 412` | Zotero 正忙，或者文献库刚被改过。让助手重新生成一次导入计划。 |
| 提示找不到 `python`，或者弹出微软商店 | 从 python.org 安装 Python，安装时勾选 **Add python.exe to PATH**，然后重新打开终端。macOS 上用 `python3`。 |
| 助手不认识 `ideaflow-zotero` | 确认打开的是项目文件夹本身，而不是它的上一级文件夹。然后重启助手。 |
| 助手找不到 `zotero.py` | 脚本在 `.agents/skills/ideaflow-zotero/scripts` 和 `.claude/skills/ideaflow-zotero/scripts`，可以把这个路径直接告诉助手。 |

## 命令行和费用

[英文 README 的命令行示例](README.md#command-line)展示如何检查连接、预览导入、写入和导出。

脚本通过 `127.0.0.1` 连接本机 Zotero。用已有的 Codex 或 Claude Code 权限即可运行。Skill 本身无需另开模型 API 密钥。助手可以使用客户端提供的工具读取你提供的资料和检索公开来源。如果已启用 Zotero 同步，本地变更可能同步到你的账户。 [Zotero 本地 API 文档](https://www.zotero.org/support/dev/web_api/v3/local_api)
