from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BOOKS_CSV = BASE_DIR / 'books_working.csv'
RAW_Q2_CSV = BASE_DIR / 'raw_q2_entries.csv'
Q1_CATALOG_CSV = BASE_DIR / 'q1_catalog.csv'
BOOK_FINAL_VIEW_CSV = BASE_DIR / 'book_final_view.csv'
Q1_UNASSIGNED_CSV = BASE_DIR / 'q1_unassigned_books.csv'

LEGACY_OUTPUTS = [
    BASE_DIR / 'q2_pool.csv',
    BASE_DIR / 'q1_clusters.csv',
    BASE_DIR / 'book_q1_links.csv',
    BASE_DIR / 'q1_index.csv',
    BASE_DIR / 'q1_books_flat.csv',
]

RAW_Q2_FIELDS = [
    'raw_q2_id',
    'book_id',
    'title',
    'author',
    'q2_text',
    'q2_status',
    'source_basis',
    'notes',
]

Q1_CATALOG_FIELDS = [
    'q1_id',
    'q1_question',
    'book_count',
    'book_ids',
    'book_titles',
    'status',
    'notes',
]

Q1_UNASSIGNED_FIELDS = [
    'book_id',
    'title',
    'author',
    'metadata_status',
    'metadata_reliable',
    'raw_q2_count',
    'reason',
]

BOOK_FINAL_VIEW_FIELDS = [
    'book_id',
    'title',
    'author',
    'metadata_status',
    'metadata_reliable',
    'q2_generation_basis',
    'q1_id',
    'q1_question',
    'q1_status',
    'q1_assignment_reason',
    'raw_q2_count',
    'raw_q2_1',
    'raw_q2_2',
    'raw_q2_3',
    'raw_q2_4',
    'raw_q2_5',
    'notes',
]

GENERIC_Q2_FALLBACK = [
    '这本书试图修正哪一种常见但有问题的看法？',
    '作者给出的关键证据链条是什么？',
    '如果把书中的框架应用到现实，会先做哪一步？',
    '这本书最有解释力的概念如何落到具体案例？',
]

MIN_STABLE_Q1_BOOKS = 3

# Keep Q1 questions concrete and narrow enough for retrieval.
Q1_THEME_QUESTION = {
    '政治与制度': '制度安排如何具体影响权力运行与群体行为？',
    '心理与决策': '哪些心理机制会系统性影响判断与选择质量？',
    '小说与叙事': '人物在欲望、责任与制度压力下做出了哪些代价性选择？',
    '复杂系统': '系统中的反馈与耦合如何导致长期反直觉结果？',
    'AI与技术实践': '模型、算法与工程实现之间的关键落差在哪里？',
    '商业与组织': '组织如何在不确定环境中保持策略有效性？',
    '游戏与机制设计': '规则与激励如何改变参与者的策略与体验？',
    '历史与社会': '哪些结构性因素推动了长期历史与社会变迁？',
    '哲学与思想': '该书如何界定行动、责任与自由的边界？',
    '方法与学习工具': '这本书把复杂问题拆解为可学习步骤的关键方法是什么？',
}

Q2_BY_THEME = {
    '政治与制度': [
        '这本书如何解释制度设计与执行之间的张力？',
        '书中的案例如何揭示权力运作的具体机制？',
        '该书指出了哪些会导致制度失灵的关键条件？',
    ],
    '心理与决策': [
        '这本书揭示了哪些稳定影响判断质量的心理机制？',
        '该书提出了哪些可执行的偏差修正方法？',
        '这本书如何解释理性与非理性在决策中的互动？',
    ],
    '小说与叙事': [
        '这本书通过人物关系揭示了哪些核心冲突？',
        '叙事结构如何影响读者对人物选择的理解？',
        '作品中的价值冲突如何映射现实处境？',
    ],
    '复杂系统': [
        '这本书如何说明局部优化会触发系统级副作用？',
        '该书给出了哪些识别反馈回路的具体方法？',
        '书中的系统视角如何改变长期策略设计？',
    ],
    'AI与技术实践': [
        '这本书如何连接数学抽象与工程实现？',
        '该书强调了哪些可复用的建模与评估原则？',
        '书中讨论的技术限制如何影响真实应用？',
    ],
    '商业与组织': [
        '这本书如何解释组织在增长与效率之间的权衡？',
        '该书提供了哪些应对不确定性的策略框架？',
        '书中对激励机制的分析能支持哪些管理决策？',
    ],
    '游戏与机制设计': [
        '这本书如何解释规则变化对行为策略的影响？',
        '该书提出了哪些可复用的机制设计原则？',
        '竞争与合作在何种条件下会发生转换？',
    ],
    '历史与社会': [
        '这本书如何识别推动历史变迁的结构性因素？',
        '书中如何解释制度与社会行为的共演关系？',
        '该书的历史论证对当下问题有什么可迁移价值？',
    ],
    '哲学与思想': [
        '这本书提出了哪些关键概念来重构对现实的理解？',
        '书中如何处理价值判断与行动选择之间的关系？',
        '该书与既有思想传统的分歧点在哪里？',
    ],
    '方法与学习工具': [
        '这本书提供了哪些可复用的问题拆解方法？',
        '这些方法在真实任务中的关键步骤是什么？',
        '该书如何帮助建立可验证的分析流程？',
    ],
    '待人工复核': [
        '这本书最核心的论题是什么？',
        '作者试图反驳或修正什么常见观点？',
        '该书最值得追踪的论证链条是什么？',
    ],
}

THEME_KEYWORDS = [
    ('游戏与机制设计', ['游戏', 'game', '博弈', '引擎', '游戏化', '蚱']),
    ('AI与技术实践', ['人工智能', 'ai', '深度学习', 'python', '矩阵', '推荐系统', '算法', '计算机']),
    ('政治与制度', ['国家', '权力', '统治', '规训', '契约', '共同体', '政治', '制度', '秩序', '农民']),
    ('心理与决策', ['心理', '认知', '思维', '决策', '噪声', '理性', '焦虑', '习惯', '拖延']),
    ('复杂系统', ['复杂', '系统', '同步', '因果', '控制论', '信号', '反馈', '流行病']),
    ('商业与组织', ['商业', '公司', '组织', '产品', '投资', '奈飞', 'mba', '谈判', 'business']),
    ('历史与社会', ['历史', '世界史', '全球史', '王朝', '社会学', '1493', '时间线']),
    ('方法与学习工具', ['方法', '工具', '微积分', '线性代数', '数学要素', 'problem', 'gtd', '清单']),
    ('小说与叙事', ['小说', '伊甸', '白夜', '雪国', '荒原狼', '尤利西斯', '玫瑰', '审判', '城堡', '罪与罚', '项塔兰', '哈扎尔辞典']),
    ('哲学与思想', ['哲学', '荣格', '叔本华', '阿伦特', '尼采', '意志', '表象', '德米安', '思想']),
]


def load_rows(path: Path):
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def title_head(title: str) -> str:
    for sep in ['：', ':', '｜', '|', ' - ']:
        if sep in title:
            return title.split(sep, 1)[0].strip()
    return title.strip()


def choose_variants(theme: str, book_id: str):
    variants = Q2_BY_THEME[theme]
    digest = hashlib.md5(f"{theme}:{book_id}".encode('utf-8')).hexdigest()
    start = int(digest[:2], 16) % len(variants)
    return variants[start:] + variants[:start]


def signal_strength(theme: str, title: str, author: str) -> int:
    text = f"{title} {author}".lower()
    for key, keywords in THEME_KEYWORDS:
        if key == theme:
            return sum(1 for kw in keywords if kw.lower() in text)
    return 0


def desired_q2_count(theme: str, metadata_status: str, title: str, author: str) -> int:
    # Decide count first, then generate only that many entries.
    if theme == '待人工复核':
        return 2

    status = (metadata_status or '').strip()
    strength = signal_strength(theme, title, author)

    target = 2
    if status == 'matched' and strength >= 2:
        target = 3
    if status == 'matched' and strength >= 4:
        target = 4
    if status == 'matched' and strength >= 6:
        target = 5
    if status == 'ambiguous-match' and strength >= 3:
        target = 3

    return min(5, max(2, target))


def build_q2_texts(theme: str, book_id: str, title: str, desired_count: int):
    anchor = f"《{title_head(title)}》这本书试图回答的核心问题是什么？"
    ordered = choose_variants(theme, book_id)
    q2_texts: list[str] = [anchor]

    candidates = []
    candidates.extend(ordered)
    candidates.extend(GENERIC_Q2_FALLBACK)

    for q in candidates:
        if len(q2_texts) >= desired_count:
            break
        if q not in q2_texts:
            q2_texts.append(q)

    return q2_texts[: min(desired_count, 5)]


def infer_theme(title: str, author: str):
    text = f"{title} {author}".lower()
    for theme, keywords in THEME_KEYWORDS:
        if any(k.lower() in text for k in keywords):
            return theme
    return '待人工复核'


def clean_legacy_outputs():
    removed = []
    for path in LEGACY_OUTPUTS:
        if path.exists():
            path.unlink()
            removed.append(path.name)
    return removed


def build_views(remove_legacy: bool = True):
    books = load_rows(BOOKS_CSV)

    raw_q2_rows = []
    q1_books = defaultdict(list)
    q1_titles = defaultdict(list)
    q1_status = {}
    q1_assignment_map = {}
    book_final_rows = []
    q1_unassigned_rows = []

    raw_idx = 1

    for row in books:
        book_id = row['book_id'].strip()
        title = row['title'].strip()
        author = row.get('author', '').strip()
        metadata_status = row.get('metadata_status', '').strip()
        has_reliable_metadata = metadata_status == 'matched'

        theme = infer_theme(title, author)
        is_unassigned_theme = theme == '待人工复核'
        q1_question = '' if is_unassigned_theme else Q1_THEME_QUESTION[theme]

        # Generate thematic Q2 only when metadata is reliably matched.
        if has_reliable_metadata:
            q2_target = desired_q2_count(theme, metadata_status, title, author)
            book_q2_texts = build_q2_texts(theme, book_id, title, q2_target)
            q2_source_basis = 'title-author-and-matched-metadata'
        else:
            book_q2_texts = []
            q2_source_basis = 'insufficient-reliable-metadata'

        q2_count = len(book_q2_texts)

        raw_ids_for_book = []
        for q2_text in book_q2_texts:
            raw_q2_id = f"RQ2-{raw_idx:04d}"
            raw_idx += 1
            raw_rows_status = 'needs-review' if is_unassigned_theme else 'draft'

            raw_q2_rows.append(
                {
                    'raw_q2_id': raw_q2_id,
                    'book_id': book_id,
                    'title': title,
                    'author': author,
                    'q2_text': q2_text,
                    'q2_status': raw_rows_status,
                    'source_basis': q2_source_basis,
                    'notes': 'auto-generated baseline; human refinement required',
                }
            )
            raw_ids_for_book.append(raw_q2_id)

        current_q1_status = 'draft'
        if metadata_status in {'no-match', 'ambiguous-match'}:
            current_q1_status = 'needs-review'

        if not has_reliable_metadata:
            current_q1_status = 'unassigned'
            assignment_reason = 'metadata_not_matched' if metadata_status == 'no-match' else 'metadata_ambiguous'
            q1_unassigned_rows.append(
                {
                    'book_id': book_id,
                    'title': title,
                    'author': author,
                    'metadata_status': metadata_status,
                    'metadata_reliable': 'false',
                    'raw_q2_count': str(q2_count),
                    'reason': 'metadata_not_matched' if metadata_status == 'no-match' else 'metadata_ambiguous',
                }
            )
        elif is_unassigned_theme:
            current_q1_status = 'unassigned'
            assignment_reason = 'theme_inference_low_confidence'
            q1_unassigned_rows.append(
                {
                    'book_id': book_id,
                    'title': title,
                    'author': author,
                    'metadata_status': metadata_status,
                    'metadata_reliable': 'true',
                    'raw_q2_count': str(q2_count),
                    'reason': 'theme_inference_low_confidence',
                }
            )
        else:
            assignment_reason = 'theme_cluster_candidate'
            q1_books[q1_question].append(book_id)
            q1_titles[q1_question].append(title)
            q1_status[q1_question] = (
                'needs-review'
                if current_q1_status == 'needs-review'
                else q1_status.get(q1_question, 'draft')
            )
            q1_assignment_map[book_id] = q1_question

        book_final_rows.append(
            {
                'book_id': book_id,
                'title': title,
                'author': author,
                'metadata_status': metadata_status,
                'metadata_reliable': 'true' if has_reliable_metadata else 'false',
                'q2_generation_basis': q2_source_basis,
                'q1_id': '',  # filled after q1 catalog is built when assigned
                'q1_question': '' if (is_unassigned_theme or not has_reliable_metadata) else q1_question,
                'q1_status': current_q1_status,
                'q1_assignment_reason': assignment_reason,
                'raw_q2_count': str(q2_count),
                'raw_q2_1': book_q2_texts[0] if len(book_q2_texts) > 0 else '',
                'raw_q2_2': book_q2_texts[1] if len(book_q2_texts) > 1 else '',
                'raw_q2_3': book_q2_texts[2] if len(book_q2_texts) > 2 else '',
                'raw_q2_4': book_q2_texts[3] if len(book_q2_texts) > 3 else '',
                'raw_q2_5': book_q2_texts[4] if len(book_q2_texts) > 4 else '',
                'notes': f'theme={theme}',
            }
        )

    q1_catalog_rows = []
    q1_id_map = {}

    sorted_q1 = sorted(
        q1_books.items(), key=lambda item: (-len(set(item[1])), item[0])
    )

    next_q1_index = 1
    unstable_q1_questions = set()
    for q1_question, book_ids in sorted_q1:
        unique_ids = sorted(set(book_ids), key=lambda x: int(x))
        if len(unique_ids) < MIN_STABLE_Q1_BOOKS:
            unstable_q1_questions.add(q1_question)
            continue

        q1_id = f"Q1-{next_q1_index:03d}"
        next_q1_index += 1
        q1_id_map[q1_question] = q1_id

        seen_titles = set()
        ordered_titles = []
        for title in q1_titles[q1_question]:
            if title not in seen_titles:
                seen_titles.add(title)
                ordered_titles.append(title)

        q1_catalog_rows.append(
            {
                'q1_id': q1_id,
                'q1_question': q1_question,
                'book_count': str(len(unique_ids)),
                'book_ids': ' '.join(unique_ids),
                'book_titles': ' | '.join(ordered_titles),
                'status': q1_status.get(q1_question, 'draft'),
                'notes': 'direct Q1->books lookup view',
            }
        )

    for row in book_final_rows:
        if row['q1_question'] in unstable_q1_questions:
            row['q1_id'] = ''
            row['q1_question'] = ''
            row['q1_status'] = 'unassigned'
            row['q1_assignment_reason'] = 'q1_cluster_not_stable'
            q1_unassigned_rows.append(
                {
                    'book_id': row['book_id'],
                    'title': row['title'],
                    'author': row['author'],
                    'metadata_status': row['metadata_status'],
                    'metadata_reliable': row['metadata_reliable'],
                    'raw_q2_count': row['raw_q2_count'],
                    'reason': 'q1_cluster_not_stable',
                }
            )
        elif row['q1_question']:
            row['q1_id'] = q1_id_map[row['q1_question']]

    book_final_rows.sort(
        key=lambda row: (
            0 if row['q1_status'] == 'unassigned' else 1,
            0 if row['metadata_reliable'] == 'false' else 1,
            int(row['book_id']),
        )
    )

    write_csv(RAW_Q2_CSV, raw_q2_rows, RAW_Q2_FIELDS)
    write_csv(Q1_CATALOG_CSV, q1_catalog_rows, Q1_CATALOG_FIELDS)
    write_csv(BOOK_FINAL_VIEW_CSV, book_final_rows, BOOK_FINAL_VIEW_FIELDS)
    write_csv(Q1_UNASSIGNED_CSV, q1_unassigned_rows, Q1_UNASSIGNED_FIELDS)

    removed_files = []
    if remove_legacy:
        removed_files = clean_legacy_outputs()

    print(
        {
            'books': len(books),
            'raw_q2_entries': len(raw_q2_rows),
            'q1_catalog_rows': len(q1_catalog_rows),
            'book_final_rows': len(book_final_rows),
            'q1_unassigned_rows': len(q1_unassigned_rows),
            'legacy_removed': removed_files,
        }
    )


if __name__ == '__main__':
    build_views(remove_legacy=True)
