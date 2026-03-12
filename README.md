# AI Thematic Reading List Builder for Existing Book Collections

> Turn an existing book backlog into thematic reading lists with metadata-aware AI clustering.

- 中文名：面向现有书单的 AI 主题阅读清单生成器
- English Name: AI Thematic Reading List Builder for Existing Book Collections
- Repository: `ai-thematic-reading-list-builder`

[中文](#中文) | [English](#english)

---

## 中文

### 适合谁

这个项目更适合下面这些人，而不是“我今天想搜某个主题下该看什么书”的纯找书场景：

1. 手里已经有一大批待读书目，但不知道该先读哪一组的人。
2. 豆瓣、微信读书、浏览器收藏夹、Excel 书单里已经堆了很多条目，但传统分类法越分越乱的人。
3. 想把“历史、哲学、心理学、科普、小说”这些跨领域材料自动整理成若干主题阅读包的人。
4. 导师或团队一次性给了一批论文、报告、材料，希望先看出它们大致可以聚成哪些阅读方向的人。

### 概述

很多书单项目都会停在“这本书属于什么领域”这一层，比如心理学、哲学、历史、小说、技术。这种整理方式看起来整齐，但真正开始读的时候常常并不好用，因为用户真正面对的痛点通常不是“我想知道它属于哪一类”，而是“我手头已经有这么多东西了，怎样把它们自然整理成几条值得推进的阅读线”。

这个项目解决的就是这个问题。它不是一个“帮你去全网找书”的推荐引擎，而是一个“把已有材料自动聚合成主题书单”的整理工作流。它更像是在一堆已经收集好的书里，帮你看出哪些内容其实应该放在一起读，哪些条目暂时信息不足，不该硬分。

对很多读者来说，这个场景很常见：豆瓣想读里堆了几十本书，过一段时间再回头看，只剩下一串标题；你知道这些书大概都重要，但不知道先从哪几本一起读最顺。这个工作流的价值就在这里。它不是替你决定“世界上最好的书”，而是帮你把已经拥有的材料盘活，自动整理出更可执行的阅读清单。

同样的思路也能迁移到论文场景。比如导师一次给了学生二三十篇论文，学生未必一开始就知道创新点应该落在哪，也未必知道这些论文天然分成哪几组。这个时候，先为单条材料提炼局部主题，再把多条材料聚成更高层的主题簇，本质上就是同一套范式。这里用在书单上，后续也完全可以改造成论文、报告、课程资料或其他文本集合的整理流程。

当前仓库默认从豆瓣相关 metadata 出发做匹配与抓取，但豆瓣不是这个项目的本体，只是当前实现选用的一种内容来源。只要你能从别的来源拿到足够稳定的标题、作者、简介或摘要，这套流程就可以迁移过去。因此，这个项目既是一个可直接运行的书单整理工具，也是一个可以复用到别的材料集合上的主题聚合范式。

为了解决这些问题，项目使用两个层级的提问结构：

1. Q2：单本书或单条材料的局部主题。可以把它理解成“这本书主要在展开什么具体方向”。
2. Q1：跨多本书的上位主题。可以把它理解成“这些材料为什么值得被放进同一个阅读包”。

整个流程的目标，不是先拍脑袋定义一些宽泛主题，再把书塞进去；而是先确认书目信息是否可靠，再为单本书生成可追溯的 Q2，最后只从稳定的 Q2 聚合中提炼 Q1。

这个 README 是项目唯一的流程说明。README、脚本行为、CSV 结果必须一致；如果三者冲突，应先修代码并全量重建结果，而不是继续沿用旧产物。

### CSV 合同

项目目录固定保留 5 张运营 CSV：

1. `books_working.csv`
2. `raw_q2_entries.csv`
3. `q1_catalog.csv`
4. `book_final_view.csv`
5. `q1_unassigned_books.csv`

含义如下：

1. `books_working.csv` 是唯一输入，负责书目主索引和 metadata 可信度。
2. `raw_q2_entries.csv` 是允许生成的原始 Q2 层。
3. `q1_catalog.csv` 是 Q1 到书单的总览。
4. `book_final_view.csv` 是按书查看最终状态的主入口。
5. `q1_unassigned_books.csv` 是正式的未分配队列，不是漏项表。

### 核心规则

1. 没有可靠 metadata，就不能自动生成 thematic Q2，也不能进入 Q1。
2. Q2 采用“先决定要写几条，再只生成这些条”的流程，不走“先写很多再清洗”。
3. Q1 只能从通过 metadata 门槛且形成稳定簇的书里派生。
4. 不能稳定归类的书必须显式展示，而不是隐藏在空白字段中。

### Metadata 门槛

`books_working.csv` 中的 `metadata_status` 决定是否允许进入主题生成：

1. `matched`：允许生成 Q2，并可参与 Q1 聚类。
2. `ambiguous-match`：不允许生成 Q2；进入 `q1_unassigned_books.csv`。
3. `no-match`：不允许生成 Q2；进入 `q1_unassigned_books.csv`。

这是硬门槛，不允许例外。原因是：没有可靠书目信息，就不能假装知道这本书在回答什么问题。

### 两个脚本，各管一段

阶段 1：

1. 脚本：`workflow_processor.py`
2. 作用：只做 metadata 匹配、状态更新、断点续跑。
3. 明确不做：Q2 生成、Q1 聚类。

阶段 2-4：

1. 脚本：`workflow_build_final_views.py`
2. 作用：根据 `books_working.csv` 生成 `raw_q2_entries.csv`、`q1_catalog.csv`、`book_final_view.csv`、`q1_unassigned_books.csv`。
3. 行为约束：未通过 metadata 门槛的书只能进入未分配队列。

### Q2 生成规则

1. Q2 必须是问题句。
2. Q2 必须可以从书名、作者、已匹配 metadata 所给出的信息稳定支撑。
3. 先判断这本书需要几条，再只生成该数量。
4. 默认 2 条；只有在额外信号足够强时，才增加到 3-5 条。
5. 不允许车轱辘话式改写，只换措辞但不增加信息的候选问题应被舍弃。

### Q1 生成规则

1. Q1 必须是可理解、可检索、具有解释力的问题句。
2. 不允许“什么都能装进去”的空泛大类。
3. 过小、过弱、不稳定的簇不保留为正式 Q1，而是退回未分配队列。
4. 当前实现要求一个 Q1 至少要有稳定的多本书支持，不能用单书占位符充数。

### 如何查看结果

1. 看某个 Q1 对应哪些书：打开 `q1_catalog.csv`。
2. 看某本书有没有被分到 Q1、Q2 是什么、依据是什么：打开 `book_final_view.csv`。
3. 看哪些书没有产生 Q1，以及为什么没有：打开 `q1_unassigned_books.csv`。

不需要再走 “Q1 -> Q2 -> 书” 的三跳链路。

### `book_final_view.csv` 关键字段

1. `metadata_reliable`：当前 metadata 是否可靠。
2. `q2_generation_basis`：为什么允许或不允许生成 Q2。
3. `q1_status`：当前是已分配还是未分配。
4. `q1_assignment_reason`：为什么被分配，或为什么没有被分配。
5. `raw_q2_count` 和 `raw_q2_1` 到 `raw_q2_5`：当前真正生成出来的 Q2 数量与内容。

### `q1_unassigned_books.csv` 的原因口径

至少使用以下原因之一：

1. `metadata_not_matched`
2. `metadata_ambiguous`
3. `theme_inference_low_confidence`
4. `q1_cluster_not_stable`

### 每次重建后的检查清单

1. 确认目录内仍然只有 5 张运营 CSV。
2. 确认 `metadata_status != matched` 的书没有出现在 `raw_q2_entries.csv`。
3. 确认所有没有 Q1 的书都能在 `q1_unassigned_books.csv` 中直接看到原因。
4. 确认 `book_final_view.csv` 中没有“空着但不解释”的状态。
5. 确认 `q1_catalog.csv` 中不再出现明显过宽或单书占位的 Q1。

### 执行顺序（由 AI Agent 驱动）

这是一个 **AI 智能体工作流项目**。你不需要（也不应该）手动去终端里敲命令运行 Python 文件。这里的脚本更多是写给 AI 看的“标准操作规程”。

1. **准备数据**：清除或替换默认的 `books_working.csv`，填入你自己的书单。至少需要提供以下基础表头（其余元数据脚本会自动抓取补充）：
   | title | author | isbn | douban_url | douban_id |
   | :--- | :--- | :--- | :--- | :--- |
   | 示例书名 | 示例作者 | ... | ... | ... |
2. **唤醒 AI**：在你的编辑器里打开 AI 对话框（如 Cursor、GitHub Copilot），直接对 AI 说：“请阅读 README 的规则，先帮我运行 `workflow_processor.py` 更新 metadata，然后再运行 `workflow_build_final_views.py` 完成主题聚类。”
3. **AI 自动执行**：AI 会自动阅读这里的脚本逻辑、为你调通环境、处理报错并执行完毕。
4. **全量重建**：只要流程规则变了，就让 AI 全量重建，不允许继续沿用旧 CSV。

### 开源与可移植性说明

1. 当前脚本都使用相对路径定位项目目录，因此整个 `book-question-workflow` 文件夹可以移动到其他位置再使用。
2. 终端里出现的 `.venv` 或 Python 绝对路径不是项目内部依赖，它们只是本机执行环境，不属于项目必须内容。
3. 当前目录中未发现 API key、token、cookie、密码、私钥、用户绝对路径等明显敏感信息。
4. `douban_workflow_helper.js` 使用公开网页抓取逻辑，没有内置账号凭据。

---

## English

### Who This Is For

This project is better suited to people who already have a large pile of reading material and need help organizing it, rather than people who simply want a search engine for “books about topic X.” Typical use cases include:

1. Readers who already have a long backlog but do not know which books should be read together first.
2. People whose Douban shelves, reading apps, browser bookmarks, or spreadsheets are full of saved titles, but whose category labels are no longer useful.
3. Users who want to turn a mixed collection of history, philosophy, psychology, science, and fiction into several coherent thematic reading lists.
4. Students or researchers who receive a batch of papers, reports, or references and need to see the major thematic groupings before they can identify directions worth pursuing.

### Overview

Many book-list projects stop at broad categories such as psychology, philosophy, history, fiction, or technology. That may look tidy, but it often breaks down when someone actually starts reading, because the practical problem is usually not “which category does this belong to?” but “I already have a large pile of material, so how do I turn it into a few reading paths that are actually worth following?”

That is the problem this project is designed to solve. It is not mainly a discovery engine for finding new books on the open web. It is a workflow for automatically clustering existing material into thematic reading lists. In other words, it helps a user look at a pile of already collected books and see which ones naturally belong together, and which items still lack enough evidence to be grouped confidently.

This is a common real-world situation. A reader may have saved dozens of books in Douban and later come back to a flat list of titles with no clear sense of what to read first. The value of this workflow is not that it tells the user “the best books in the world.” Its value is that it activates the material the user already owns, and reorganizes it into reading lists that are easier to act on.

The same pattern also transfers well to papers and research materials. For example, a supervisor may give a student a batch of papers before the student has a clear sense of the possible innovation directions. In that setting, extracting local themes from individual items and then clustering them into higher-level thematic groups is essentially the same pattern. This repository applies that pattern to books first, but the workflow can also be adapted to papers, reports, course materials, or other text collections.

The current implementation starts from Douban-related metadata matching and scraping, but Douban is not the core idea of the project. It is only the current data source. If another source can provide stable titles, authors, descriptions, or abstracts, the same workflow can be transferred there. So this repository is both a practical book-list organizer and a reusable pattern for thematic clustering over other material collections.

To support that goal, the workflow uses two layers of prompts:

1. Q2: the local theme of a single book or item. In plain terms, this means “what direction is this item mainly developing?”
2. Q1: the higher-level theme shared across multiple books. In plain terms, this means “why do these items belong in the same reading pack?”

The goal is not to invent broad themes first and force books into them. The goal is to confirm reliable metadata first, generate traceable Q2 questions for individual books, and derive Q1 only from stable Q2 groupings.

This README is the single source of truth for the workflow. The README, the scripts, and the generated CSV outputs must agree. If they diverge, fix the code and regenerate the outputs instead of trusting stale files.

### CSV Contract

The project directory keeps exactly 5 operational CSV files:

1. `books_working.csv`
2. `raw_q2_entries.csv`
3. `q1_catalog.csv`
4. `book_final_view.csv`
5. `q1_unassigned_books.csv`

They mean:

1. `books_working.csv` is the only input and stores the master book index plus metadata reliability.
2. `raw_q2_entries.csv` is the raw Q2 layer for books that are allowed to receive generated Q2.
3. `q1_catalog.csv` is the direct Q1-to-books overview.
4. `book_final_view.csv` is the main per-book final view.
5. `q1_unassigned_books.csv` is the formal unassigned queue, not a missing-items table.

### Core Rules

1. Without reliable metadata, a book must not receive generated thematic Q2 or enter Q1 clustering.
2. Q2 follows a count-first process: decide how many are needed, then generate only that many.
3. Q1 can only be derived from books that passed the metadata gate and formed stable clusters.
4. Books that cannot be assigned stably must be shown explicitly, not hidden behind blank fields.

### Metadata Gate

The `metadata_status` field in `books_working.csv` controls eligibility:

1. `matched`: allowed to receive Q2 and enter Q1 clustering.
2. `ambiguous-match`: not allowed to receive generated Q2; must go to `q1_unassigned_books.csv`.
3. `no-match`: not allowed to receive generated Q2; must go to `q1_unassigned_books.csv`.

This is a hard gate. If the metadata is not reliable, the workflow must not pretend to know what the book is about.

### Two Scripts, Two Responsibilities

Stage 1:

1. Script: `workflow_processor.py`
2. Responsibility: metadata matching, status updates, resumable processing.
3. Explicitly does not handle Q2 or Q1 generation.

Stage 2-4:

1. Script: `workflow_build_final_views.py`
2. Responsibility: generate `raw_q2_entries.csv`, `q1_catalog.csv`, `book_final_view.csv`, and `q1_unassigned_books.csv` from `books_working.csv`.
3. Constraint: books that fail the metadata gate may only appear in the unassigned queue.

### Q2 Generation Rules

1. Every Q2 must be a question.
2. Every Q2 must be stably supported by the title, author, and matched metadata.
3. Decide the number first, then generate only that number.
4. Default to 2 Q2 questions; increase to 3-5 only when there is clearly stronger evidence.
5. Avoid wheel-spinning paraphrases. A candidate that only rewords an existing question without adding information should be rejected.

### Q1 Generation Rules

1. Every Q1 must be understandable, searchable, and explanatory.
2. Broad buckets that could absorb almost anything are not allowed.
3. Small, weak, or unstable clusters should not survive as formal Q1; they must be pushed back into the unassigned queue.
4. The current implementation requires each formal Q1 to have stable support from multiple books rather than acting as a one-book placeholder.

### How To Read The Outputs

1. To see which books belong to a Q1, open `q1_catalog.csv`.
2. To inspect one book's Q1, Q2, and status basis, open `book_final_view.csv`.
3. To see which books have no Q1 and why, open `q1_unassigned_books.csv`.

You do not need to follow a three-step chain like “Q1 -> Q2 -> book”.

### Important Fields In `book_final_view.csv`

1. `metadata_reliable`: whether the metadata is reliable.
2. `q2_generation_basis`: why Q2 generation was allowed or blocked.
3. `q1_status`: whether the book is assigned or unassigned.
4. `q1_assignment_reason`: why the book was assigned, or why it was not.
5. `raw_q2_count` and `raw_q2_1` to `raw_q2_5`: the actual generated Q2 count and contents.

### Allowed Reason Codes In `q1_unassigned_books.csv`

At minimum, use one of these:

1. `metadata_not_matched`
2. `metadata_ambiguous`
3. `theme_inference_low_confidence`
4. `q1_cluster_not_stable`

### Post-Rebuild Checklist

1. Confirm the directory still contains exactly 5 operational CSV files.
2. Confirm that books with `metadata_status != matched` do not appear in `raw_q2_entries.csv`.
3. Confirm that every book without Q1 is visible in `q1_unassigned_books.csv` with a reason.
4. Confirm that `book_final_view.csv` contains no unexplained blank-state rows.
5. Confirm that `q1_catalog.csv` contains no obviously overbroad or one-book placeholder Q1 questions.

### Execution Order (AI Agent Driven)

This is an **AI Agent workflow project**. You do not need to manually open a terminal and run the Python files. These scripts are essentially "Standard Operating Procedures" written for the AI to read and execute.

1. **Prepare data**: Replace `books_working.csv` with your own book list. A minimal working example of the CSV headers:
   | title | author | isbn | douban_url | douban_id |
   | :--- | :--- | :--- | :--- | :--- |
   | Book Title | Author | ... | ... | ... |
2. **Instruct the AI**: Open your AI chat panel (e.g., Cursor, GitHub Copilot) and tell the AI: "Please read the README rules, run `workflow_processor.py` first to update metadata, and then run `workflow_build_final_views.py` to finish the thematic clustering."
3. **AI Automation**: The AI will automatically read the logic, fix any environment issues, construct LLM prompts, and finish the job for you.
4. **Rebuild Rule**: Any rule change requires instructing the AI to do a full rebuild. Do not keep using old CSV outputs after logic changes.

### Open Source And Portability Notes

1. The scripts use paths relative to the project directory, so the entire `book-question-workflow` folder can be moved safely.
2. The `.venv` path or absolute Python path seen in local terminals is not part of the project contract; it is only a local execution environment.
3. No obvious API keys, tokens, cookies, passwords, private keys, or user absolute paths were found inside the project directory during review.
4. `douban_workflow_helper.js` uses public web requests and does not embed account credentials.
